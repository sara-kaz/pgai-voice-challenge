"""
Bridges a live Twilio phone call to the OpenAI Realtime API.

How a call flows through this file:
1. Twilio dials the target number and, once connected, requests `/twiml`.
   We return TwiML telling Twilio to open a bidirectional Media Stream
   websocket back to us, at `/media-stream/{call_sid}`.
2. Twilio connects to `/media-stream/{call_sid}`. We open a second
   websocket to OpenAI's Realtime API and configure it with the persona
   for this call (looked up by call_sid).
3. From then on we just relay audio both directions:
     Twilio caller audio  -> OpenAI (input_audio_buffer.append)
     OpenAI generated speech -> Twilio (media event)
   Twilio's Media Streams and OpenAI's Realtime API both speak G.711
   u-law at 8kHz for telephony, so no transcoding is needed — we pass the
   base64 payload straight through.
4. We also collect the transcript OpenAI emits (both sides) and write it
   to transcripts/{call_sid}.txt when the call ends.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional

import requests
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from twilio.rest import Client as TwilioClient

import analyze as bug_analyzer
import generate_bug_report as report_generator
from place_call import place_call as trigger_call
from scenarios.scenarios import SCENARIOS

load_dotenv()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_REALTIME_MODEL = os.environ.get("OPENAI_REALTIME_MODEL", "gpt-realtime")
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")
REALTIME_WS_URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_REALTIME_MODEL}"

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Pure cost-safety backstop, not the primary way calls end — the persona
# decides when to hang up via the end_call tool, including recognizing an
# unproductive loop and ending the call itself. This cap only protects
# against that judgment failing entirely and a call running away; it
# should be high enough to never be the thing that actually ends a call.
MAX_CALL_SECONDS = 600

# Whisper has a documented tendency to hallucinate fixed phrases (often
# foreign-language broadcast lines) during silence or unclear audio. The
# call is entirely in English, so non-Latin-script text is a strong signal
# of a hallucination rather than real dialogue — flagged, not dropped, so
# the bug-analysis pass treats it as transcription noise.
NON_LATIN_SCRIPT_RE = re.compile(
    r"[぀-ヿ㐀-䶿一-鿿가-힯Ѐ-ӿ؀-ۿ]"
)


def is_likely_transcription_artifact(text: str) -> bool:
    return bool(NON_LATIN_SCRIPT_RE.search(text))

END_CALL_TOOL = {
    "type": "function",
    "name": "end_call",
    "description": (
        "Hang up the phone call. Call this once your goal for the call is "
        "resolved and you've said goodbye, OR if the conversation is stuck "
        "and going nowhere after a reasonable number of attempts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Why you're ending the call."},
        },
        "required": ["reason"],
    },
}

TRANSCRIPTS_DIR = Path(__file__).resolve().parent.parent / "transcripts"
TRANSCRIPTS_DIR.mkdir(exist_ok=True)
RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)
BUG_REPORTS_DIR = Path(__file__).resolve().parent.parent / "bug_reports"
BUG_REPORTS_DIR.mkdir(exist_ok=True)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Twilio CallSids are "CA" + 32 hex chars. Filenames are always
# "{scenario_key}_{CallSid}.<ext>" — used by the optional web UI below to
# group existing call artifacts back by scenario.
CALL_SID_SUFFIX_RE = re.compile(r"^(?P<scenario>.+)_(?P<call_sid>CA[0-9a-f]{32})$")


def parse_call_filename_stem(stem: str) -> Optional[tuple]:
    """Returns (scenario_key, call_sid) for a "{scenario}_{CallSid}" stem.

    Some kept-for-comparison filenames have an extra suffix before the
    CallSid (e.g. "simple_scheduling_retest2_CA...") — match against the
    longest known SCENARIOS key so these still group under their real
    scenario instead of becoming their own bogus entry.
    """
    match = CALL_SID_SUFFIX_RE.match(stem)
    if not match:
        return None
    raw_prefix, call_sid = match.group("scenario"), match.group("call_sid")
    if raw_prefix in SCENARIOS:
        return raw_prefix, call_sid
    for key in SCENARIOS:
        if raw_prefix == key or raw_prefix.startswith(key + "_"):
            return key, call_sid
    return raw_prefix, call_sid  # unknown scenario — fall back to the raw prefix


def latest_call_for_scenario(scenario_key: str) -> Optional[tuple]:
    """(file_stem, call_sid) of the most recently modified transcript for
    this scenario, if any. Returns the real file stem (which may carry an
    extra suffix like "_retest2") rather than reconstructing one, so the
    caller can build correct paths for files with that suffix."""
    candidates = []
    for path in TRANSCRIPTS_DIR.glob("*_CA*.txt"):
        parsed = parse_call_filename_stem(path.stem)
        if parsed and parsed[0] == scenario_key:
            candidates.append((path, parsed[1]))
    if not candidates:
        return None
    latest_path, latest_call_sid = max(candidates, key=lambda pc: pc[0].stat().st_mtime)
    return latest_path.stem, latest_call_sid


# call_sid -> scenario_key, populated by /twiml, read by the media-stream handler
CALL_SCENARIOS: dict[str, str] = {}

app = FastAPI()

# Optional web UI (static/index.html) — a thin convenience layer over the
# same CLI tools (place_call.py, analyze.py, generate_bug_report.py). The
# CLI keeps working exactly as before; this is purely additive.
app.mount("/recordings", StaticFiles(directory=RECORDINGS_DIR), name="recordings")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/scenarios")
async def api_scenarios():
    return [
        {"key": key, "description": info["description"]}
        for key, info in SCENARIOS.items()
    ]


@app.post("/api/calls")
async def api_place_call(request: Request):
    body = await request.json()
    scenario_key = body.get("scenario")
    if scenario_key not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario '{scenario_key}'")
    try:
        call_sid = await asyncio.to_thread(trigger_call, scenario_key)
    except Exception as exc:
        raise HTTPException(500, f"Failed to place call: {exc}")
    return {"call_sid": call_sid, "scenario": scenario_key}


@app.get("/api/results")
async def api_results():
    seen = set()
    for path in TRANSCRIPTS_DIR.glob("*_CA*.txt"):
        parsed = parse_call_filename_stem(path.stem)
        if parsed:
            seen.add(parsed[0])
    return [
        {"scenario": key, "description": SCENARIOS.get(key, {}).get("description", "")}
        for key in sorted(seen)
    ]


@app.get("/api/results/{scenario_key}")
async def api_result_detail(scenario_key: str):
    found = latest_call_for_scenario(scenario_key)
    if found is None:
        raise HTTPException(404, f"No completed calls found for '{scenario_key}'")
    base_name, call_sid = found

    transcript_path = TRANSCRIPTS_DIR / f"{base_name}.txt"
    bug_report_path = BUG_REPORTS_DIR / f"{base_name}.md"
    recording_path = RECORDINGS_DIR / f"{base_name}.mp3"

    return {
        "scenario": scenario_key,
        "call_sid": call_sid,
        "transcript": transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else "(transcript not found)",
        "bug_report": bug_report_path.read_text(encoding="utf-8") if bug_report_path.exists() else "",
        "recording_url": f"/recordings/{base_name}.mp3" if recording_path.exists() else None,
    }


async def run_bug_analysis(transcript_call_sid: str):
    # bug_analyzer.analyze() makes several blocking OpenAI API calls — run
    # it off the event loop thread so it doesn't stall anything else.
    try:
        await asyncio.to_thread(bug_analyzer.analyze, transcript_call_sid)
    except Exception as exc:
        print(f"Background bug analysis failed for {transcript_call_sid}: {exc}")
        return

    # Rebuild the final BUG_REPORT.md from every draft on disk, so the
    # deliverable is always current with no manual step required.
    try:
        await asyncio.to_thread(report_generator.generate)
    except Exception as exc:
        print(f"BUG_REPORT.md regeneration failed: {exc}")


@app.api_route("/twiml", methods=["GET", "POST"])
async def twiml(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid") or request.query_params.get("CallSid")
    scenario_key = request.query_params.get("scenario", "simple_scheduling")
    CALL_SCENARIOS[call_sid] = scenario_key

    stream_url = f"{PUBLIC_BASE_URL.replace('https://', 'wss://')}/media-stream/{call_sid}"
    twiml_body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect><Stream url=\"" + stream_url + "\" /></Connect></Response>"
    )
    return Response(content=twiml_body, media_type="text/xml")


@app.websocket("/media-stream/{call_sid}")
async def media_stream(websocket: WebSocket, call_sid: str):
    await websocket.accept()
    scenario_key = CALL_SCENARIOS.get(call_sid, "simple_scheduling")
    persona_prompt = SCENARIOS[scenario_key]["persona"]

    # Ordered by when each turn STARTS (conversation.item.added, which
    # fires synchronously) rather than when its transcription finishes —
    # Whisper transcription of the clinic agent's audio can resolve
    # seconds after a later turn's transcript already arrived, which
    # otherwise scrambles the transcript's order.
    conversation_log: list[dict] = []
    item_index_by_id: dict[str, int] = {}
    # Maps each PATIENT BOT turn to the OpenAI response that produced it,
    # and tracks which responses were ever marked "cancelled" — see
    # wait_for_pending_transcripts below for why this matters.
    item_response_id: dict[str, str] = {}
    cancelled_response_ids: set[str] = set()
    transcript_lines: list[str] = []  # meta notes (errors, hangup, etc.), appended at the end
    stream_sid_holder = {"sid": None}
    call_ended = {"flag": False}

    async def hang_up_call(reason: str):
        if call_ended["flag"]:
            return
        call_ended["flag"] = True
        transcript_lines.append(f"[call ended by bot: {reason}]")
        try:
            await asyncio.to_thread(
                lambda: twilio_client.calls(call_sid).update(status="completed")
            )
        except Exception as exc:
            transcript_lines.append(f"[hangup request failed: {exc}]")

    async def wait_for_pending_transcripts(max_wait: float = 8.0, poll: float = 0.5):
        # Transcription can resolve several seconds after a turn happens,
        # arriving on the OpenAI websocket independently of when the call
        # ends. Closing the connection right after end_call fires can lose
        # the last turn or two, so poll instead of a blind sleep.
        waited = 0.0
        while waited < max_wait:
            if all(entry["text"] is not None for entry in conversation_log):
                return
            await asyncio.sleep(poll)
            waited += poll

    async def delayed_hang_up(reason: str):
        # Twilio needs real wall-clock time to play out the model's final
        # audio after end_call fires — hanging up immediately cuts the
        # last sentence off mid-word.
        await asyncio.sleep(5.0)
        # Give any still-in-flight transcriptions a chance to land before
        # tearing down the OpenAI connection.
        await wait_for_pending_transcripts()
        await hang_up_call(reason)

    async with websockets.connect(
        REALTIME_WS_URL,
        extra_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
    ) as openai_ws:
        await openai_ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": persona_prompt,
                "tools": [END_CALL_TOOL],
                "tool_choice": "auto",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        # silence_duration_ms default (~500ms) was making
                        # the bot jump in during the clinic agent's normal
                        # mid-sentence pauses, reading as interrupting. A
                        # modest bump (not a long wait) gives the agent a
                        # bit more room to finish a thought before VAD
                        # decides it's the bot's turn to speak.
                        "turn_detection": {
                            "type": "server_vad",
                            "silence_duration_ms": 700,
                        },
                        "transcription": {"model": "whisper-1"},
                    },
                    "output": {
                        "format": {"type": "audio/pcmu"},
                        "voice": "marin",
                    },
                },
            },
        }))

        # Deliberately not forcing the model to speak first: a
        # response.create with its own "instructions" field REPLACES the
        # session instructions for that one response, which would wipe out
        # the persona for the opening line. server_vad's turn_detection
        # (create_response=true by default) fires a response automatically
        # once it hears the clinic agent speak, using the full session
        # instructions intact.

        async def twilio_to_openai():
            try:
                async for raw in websocket.iter_text():
                    msg = json.loads(raw)
                    event = msg.get("event")
                    if event == "start":
                        stream_sid_holder["sid"] = msg["start"]["streamSid"]
                    elif event == "media":
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": msg["media"]["payload"],
                        }))
                    elif event == "stop":
                        if not call_ended["flag"]:
                            # We never initiated a hangup (no end_call, no
                            # timeout) — the other side (the clinic line)
                            # disconnected first. Worth a note: otherwise
                            # the transcript just stops with no explanation
                            # of who actually ended the call.
                            call_ended["flag"] = True
                            transcript_lines.append(
                                "[call ended: clinic line disconnected first, "
                                "not our bot]"
                            )
                        break
            finally:
                # The call ended (or Twilio's socket dropped) — close the
                # OpenAI side too, otherwise the Realtime session (and its
                # billing) stays open until OpenAI's own idle timeout.
                await openai_ws.close()

        async def openai_to_twilio():
            async for raw in openai_ws:
                msg = json.loads(raw)
                msg_type = msg.get("type")
                if msg_type not in ("response.output_audio.delta",):
                    print(f"DEBUG event: {msg_type} | {json.dumps(msg)[:300]}")

                if msg_type == "response.output_audio.delta" and stream_sid_holder["sid"]:
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid_holder["sid"],
                        "media": {"payload": msg["delta"]},
                    }))
                elif msg_type == "conversation.item.added":
                    item = msg.get("item", {})
                    item_id = item.get("id")
                    role = item.get("role")
                    if item_id and item.get("type") == "message" and role in ("user", "assistant"):
                        conversation_log.append({
                            "role": "CLINIC AGENT" if role == "user" else "PATIENT BOT",
                            "text": None,
                            "item_id": item_id,
                        })
                        item_index_by_id[item_id] = len(conversation_log) - 1
                elif msg_type == "response.output_item.added":
                    item = msg.get("item", {})
                    item_id = item.get("id")
                    response_id = msg.get("response_id")
                    if item_id and response_id:
                        item_response_id[item_id] = response_id
                elif msg_type == "response.done":
                    response = msg.get("response", {})
                    if response.get("status") == "cancelled" and response.get("id"):
                        cancelled_response_ids.add(response["id"])
                elif msg_type == "conversation.item.input_audio_transcription.completed":
                    idx = item_index_by_id.get(msg.get("item_id"))
                    if idx is not None:
                        conversation_log[idx]["text"] = msg["transcript"]
                elif msg_type == "response.output_audio_transcript.done":
                    idx = item_index_by_id.get(msg.get("item_id"))
                    if idx is not None:
                        conversation_log[idx]["text"] = msg["transcript"]
                elif msg_type == "conversation.item.done":
                    # status "incomplete" means the model started a
                    # response but it was cancelled before producing any
                    # speech (typically a barge-in). No transcript event
                    # will ever arrive for this item, so it needs an
                    # explicit value rather than sitting as None forever.
                    item = msg.get("item", {})
                    if item.get("status") == "incomplete":
                        idx = item_index_by_id.get(item.get("id"))
                        if idx is not None and conversation_log[idx]["text"] is None:
                            conversation_log[idx]["text"] = (
                                "[no speech produced — this turn was cancelled "
                                "before completing, likely a barge-in]"
                            )
                elif msg_type == "response.function_call_arguments.done" and msg.get("name") == "end_call":
                    try:
                        reason = json.loads(msg.get("arguments", "{}")).get("reason", "unspecified")
                    except json.JSONDecodeError:
                        reason = "unspecified"
                    transcript_lines.append(f"[end_call requested by bot: {reason}]")
                    # Don't hang up yet and don't break — keep relaying any
                    # trailing audio while the delayed hangup timer runs.
                    asyncio.create_task(delayed_hang_up(reason))
                elif msg_type == "error":
                    transcript_lines.append(f"[error] {msg}")

        try:
            await asyncio.wait_for(
                asyncio.gather(twilio_to_openai(), openai_to_twilio()),
                timeout=MAX_CALL_SECONDS,
            )
        except asyncio.TimeoutError:
            await hang_up_call(f"max call duration of {MAX_CALL_SECONDS}s exceeded")
        except Exception as exc:
            transcript_lines.append(f"[connection ended: {exc}]")
        finally:
            # Short inline tags instead of a full explanatory paragraph
            # repeated on every flagged line — keeps the dialogue readable.
            # The one-time legend below explains what each tag means.
            tags_used = set()
            dialogue_lines = []
            for entry in conversation_log:
                response_id = item_response_id.get(entry.get("item_id"))
                was_cancelled = response_id is not None and response_id in cancelled_response_ids
                if entry["text"] is None:
                    dialogue_lines.append(f"{entry['role']}: [UNAVAILABLE]")
                    tags_used.add("UNAVAILABLE")
                elif is_likely_transcription_artifact(entry["text"]):
                    dialogue_lines.append(
                        f"{entry['role']}: [HALLUCINATION — raw: {entry['text']!r}]"
                    )
                    tags_used.add("HALLUCINATION")
                elif entry["text"].startswith("[no speech produced"):
                    dialogue_lines.append(f"{entry['role']}: [NO SPEECH]")
                    tags_used.add("NO SPEECH")
                elif was_cancelled:
                    # A turn can deliver a complete transcript and then,
                    # moments later, a second response.done event reports
                    # the same response as "cancelled" (reason
                    # "turn_detected") — the other party started talking
                    # near the end of this turn. The API gives no way to
                    # tell how much of the text actually finished streaming
                    # to Twilio, so this is flagged as a caution rather
                    # than presented as a verified match to the audio.
                    dialogue_lines.append(f"{entry['role']}: {entry['text']} [CUT SHORT?]")
                    tags_used.add("CUT SHORT?")
                else:
                    dialogue_lines.append(f"{entry['role']}: {entry['text']}")

            legend = {
                "UNAVAILABLE": "no transcription ever arrived for this turn.",
                "HALLUCINATION": "speech-to-text hallucination (e.g. a foreign-"
                    "language or out-of-place phrase from silence/noise) — "
                    "not something actually said.",
                "NO SPEECH": "this turn was cancelled before any speech was "
                    "generated, typically a barge-in (the other side started "
                    "talking right as this turn began).",
                "CUT SHORT?": "OpenAI marked this response as interrupted "
                    "partway through or right after it finished. The audio "
                    "actually heard MAY end earlier than the text shown — "
                    "though spot checks suggest the text is often accurate, "
                    "this is a caution, not a confirmed truncation.",
            }
            header_lines = []
            if tags_used:
                header_lines.append("--- TAGS USED IN THIS TRANSCRIPT ---")
                for tag in ("UNAVAILABLE", "HALLUCINATION", "NO SPEECH", "CUT SHORT?"):
                    if tag in tags_used:
                        header_lines.append(f"[{tag}] = {legend[tag]}")
                header_lines.append("---")
                header_lines.append("")

            out_path = TRANSCRIPTS_DIR / f"{scenario_key}_{call_sid}.txt"
            out_path.write_text(
                "\n".join(header_lines + dialogue_lines + transcript_lines),
                encoding="utf-8",
            )
            print(f"Saved transcript for {call_sid} -> {out_path}")

            # Auto-draft the bug-analysis pass right away, instead of
            # requiring a manual `python analyze.py <call_sid>` run later.
            asyncio.create_task(run_bug_analysis(f"{scenario_key}_{call_sid}"))


@app.post("/recording-callback")
async def recording_callback(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid")
    recording_url = form.get("RecordingUrl")  # base URI, no extension
    if not recording_url:
        return {"status": "ignored"}

    mp3_url = recording_url + ".mp3"
    resp = requests.get(mp3_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    resp.raise_for_status()
    scenario_key = CALL_SCENARIOS.get(call_sid, "unknown_scenario")
    out_path = RECORDINGS_DIR / f"{scenario_key}_{call_sid}.mp3"
    out_path.write_bytes(resp.content)
    print(f"Saved recording for {call_sid} -> {out_path}")
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}
