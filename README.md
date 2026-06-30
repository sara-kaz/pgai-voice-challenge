# Pretty Good AI — Voice Bot Challenge

An automated **patient caller** that phones Pretty Good AI's test clinic line, holds a natural spoken conversation with their voice agent, records and transcribes the call, and drafts bug reports — fully unattended.

**Target number:** `+1-805-439-8008`

---

## Deliverables

| Deliverable | Where |
|-------------|-------|
| Working code | This repo (`app/`, `analyze.py`, `generate_bug_report.py`, `place_call.py`, `scenarios/`) |
| README | This file |
| Architecture doc | [ARCHITECTURE.md](ARCHITECTURE.md) — see the **Summary** section at the top for the 1–2 paragraph version |
| Call transcripts & recordings | [`transcripts/`](transcripts/) and [`recordings/`](recordings/) — 20 calls across 17 scenarios, all `.mp3` |
| Bug report | [BUG_REPORT.md](BUG_REPORT.md) |
| Loom walkthrough (max 5 min) |[Full Recording](https://www.loom.com/share/5750342a89ab4cafb318a54be992937b)|
| Debugging screen recording | [Part 1](https://www.loom.com/share/a7c262546f1d4c67b4f1a82f4bcfafb6), [Part 2](https://www.loom.com/share/10f719e74f124b84a8fd0cc8e4d1c2aa) |

---

## Table of contents

- [Deliverables](#deliverables)
- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Running a call](#running-a-call)
- [Outputs](#outputs)
- [Bug reports](#bug-reports)
- [Test scenarios](#test-scenarios)
- [Architecture](#architecture)
- [Manual regeneration](#manual-regeneration)

---

## What it does

1. **Dials** the clinic using your Twilio number (`place_call.py`)
2. **Simulates** a human patient via OpenAI's Realtime speech-to-speech API
3. **Records** the full call audio and writes a transcript
4. **Analyzes** the transcript against a fixed rubric and clinic ground-truth facts
5. **Aggregates** findings into a ranked `BUG_REPORT.md`

Each scenario tests one focused behavior so bugs are easy to attribute. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design write-up.

---

## Quick start

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.9+ | Virtual environment recommended |
| [Twilio](https://twilio.com) account | Voice-capable phone number (outbound caller ID) |
| [OpenAI](https://platform.openai.com) API key | Realtime API access |
| [ngrok](https://ngrok.com) (or similar) | Exposes local server to Twilio webhooks |

### 1. Install dependencies

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in:

- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `OPENAI_API_KEY`
- `PUBLIC_BASE_URL` (set in step 4)

### 3. Expose the local server

Twilio needs a public URL to reach your webhooks:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL into `PUBLIC_BASE_URL` in `.env` (no trailing slash).

### 4. Start the bridge server

```bash
uvicorn app.server:app --port 8000
```

Keep this running. Twilio calls back into it as soon as a line connects.

---

## Running a call

The server **must** be running before you place a call. After the one-time setup above, running a call is two commands — start the server in the background, then place the call:

```bash
uvicorn app.server:app --port 8000 &   # leave running

python place_call.py --list            # see available scenarios
python place_call.py simple_scheduling # place one outbound test call
```

Everything past this point — recording, transcription, bug analysis, and rebuilding `BUG_REPORT.md` — happens automatically with no further commands.

### Optional: web UI

Once the server is running, you can also use a small browser UI instead of the CLI — open **`http://localhost:8000/`** (must be the server's actual URL, not the `static/index.html` file opened directly — it needs to call the server's API).

It has two parts:
- **Place a new call** — one button per scenario; click to dial the clinic live, same as `python place_call.py <scenario>`.
- **View results from a previous call** — buttons (highlighted green) for any scenario that already has a completed call on disk; click one to see its audio player, full transcript, and bug report draft.

This is purely a convenience layer over the same underlying code — the CLI commands above still work exactly as documented and don't require this page at all.

---

## Outputs

Each call produces three artifacts automatically — no manual step:

| Artifact | Path | Source |
|----------|------|--------|
| Recording | `recordings/<scenario>_<CallSid>.mp3` | Twilio recording webhook |
| Transcript | `transcripts/<scenario>_<CallSid>.txt` | Bridge server on hangup |
| Draft bug report | `bug_reports/<scenario>_<CallSid>.md` | `analyze.py` (triggered on transcript save) |

`BUG_REPORT.md` is rebuilt from all drafts in `bug_reports/` whenever a new analysis completes.

---

## Bug reports

### Automatic pipeline

When a transcript is saved, the server kicks off analysis in the background:

1. **`analyze.py`** — Drafts a per-call report using GPT-4o. Samples **3 independent passes** against a fixed rubric and merges results (a single pass missed real bugs ~2/3 of the time in development and also produced confident false positives, e.g. wrong day-of-week claims).
2. **`generate_bug_report.py`** — Rebuilds `BUG_REPORT.md` from every draft in `bug_reports/`, ranked by severity.

`BUG_REPORT.md` is fully derived output. Re-running analysis or the generator script will regenerate it from the current drafts.

### Ground-truth fact checking

`knowledge_base/clinic_facts.md` holds real clinic facts (hours, address, insurance, policies) sourced from the `pgai.us/athena` patient portal. `analyze.py` includes this file so it can catch the agent stating something **factually wrong but internally consistent** — e.g. confidently quoting incorrect hours — which a transcript-only check would miss.

> **Note:** Fill in any TODOs in `clinic_facts.md` before running analysis. Without complete ground truth, fact-checking degrades to internal-consistency checking only.

### Rubric coverage

The analyzer also looks for:

- Hallucinated or invented clinical claims
- Inconsistent details across a single call (symptom of backend/EHR issues)
- Transcription artifacts (non-Latin-script lines flagged in `app/server.py` before analysis)

---

## Test scenarios

17 scenarios in `scenarios/scenarios.py`. Each targets **one** primary behavior.

### Core workflows

| Scenario | What it tests |
|----------|---------------|
| `simple_scheduling` | Straightforward new appointment booking |
| `reschedule` | Moving an existing appointment |
| `cancel` | Cancelling an appointment (no reschedule) |
| `medication_refill` | Routine prescription refill |
| `refill_no_recent_visit` | Refill when patient hasn't had a recent checkup |
| `office_hours_location` | Hours and address FAQ |
| `insurance_question` | Insurance / billing FAQ |

### Edge cases & stress tests

| Scenario | What it tests |
|----------|---------------|
| `sunday_request_edge_case` | Agent checks office hours before confirming |
| `unclear_request` | Disambiguation of a vague opening request |
| `interruption_barge_in` | Barge-in / interruption handling |
| `frustrated_patient` | Tone and empathy under pressure |
| `out_of_scope_request` | Refusal of inappropriate requests (e.g. diagnosis) |

### Speech, privacy & context

| Scenario | What it tests |
|----------|---------------|
| `asr_stress_drug_name` | ASR on hard-to-hear medication names |
| `identity_verification_probe` | PHI disclosure without identity verification (HIPAA-relevant) |
| `multi_intent_call` | Context tracking across two unrelated requests |
| `accented_speech_stress` | ASR robustness to non-native accents |
| `low_english_proficiency` | Simplification and pacing for struggling speakers |

The last three were added to cover known clinical voice-bot failure modes beyond conversational quality: ASR errors on medical terminology, improper PHI disclosure, and context loss across topic switches.

---

## Architecture

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for:

- System diagram and data flow
- Live call bridge (Twilio ↔ OpenAI Realtime)
- Post-call pipeline (recording → transcript → analysis)
- Key design decisions and project layout

---

## Manual regeneration

The pipeline runs automatically after each call. To regenerate by hand (e.g. after editing the rubric or ground-truth facts):

```bash
# Re-analyze one call
python analyze.py <scenario>_<CallSid>

# Re-analyze every transcript
python analyze.py --all

# Rebuild BUG_REPORT.md from all drafts
python generate_bug_report.py
```
