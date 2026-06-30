"""
Draft a bug report from a call transcript using GPT-4o.

Runs automatically after each call (see app/server.py) and feeds
generate_bug_report.py, which rebuilds BUG_REPORT.md from every draft —
there is no manual review step in this pipeline by design.

Usage:
    python analyze.py <call_sid>          # analyze one transcript
    python analyze.py --all               # analyze every transcript on disk
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from scenarios.scenarios import SCENARIOS

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

TRANSCRIPTS_DIR = Path(__file__).resolve().parent / "transcripts"
BUG_REPORTS_DIR = Path(__file__).resolve().parent / "bug_reports"
BUG_REPORTS_DIR.mkdir(exist_ok=True)
KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parent / "knowledge_base" / "clinic_facts.md"

RUBRIC = """
You are reviewing a phone-call transcript between a "patient" (PATIENT BOT)
and a clinic's AI phone agent (CLINIC AGENT). Find concrete quality issues
in the CLINIC AGENT's behavior only. Look for things like:

- Self-contradiction: the agent makes two incompatible claims about the
  same fact within the call (e.g. first says an appointment exists, then
  later says there are no appointments/open cases on file; states two
  different times/dates/confirmation numbers for what should be the same
  booking). This is one of the strongest, most concrete signals of a real
  bug — always flag it. If it also prevents the patient from completing
  their request, mark it High severity.
- The call ending (or being cut off at a time limit) WITHOUT the
  patient's stated goal being achieved, and without the agent clearly and
  coherently explaining why not. A patient being told to wait for a
  callback or being transferred is fine IF the agent's reasoning was
  clear and consistent — but if the agent went back and forth, stalled
  repeatedly ("let me check," "one moment," "I'm processing this now")
  without ever producing a result, or contradicted itself about why it
  couldn't proceed, flag this as a High severity functional failure, not
  just a minor process note.
- Stating something that should be impossible given an explicit business
  rule (e.g. confirms a Sunday appointment at an office stated to be
  closed weekends) or that contradicts the GROUND TRUTH FACTS below (e.g.
  wrong hours, wrong address, wrong insurance acceptance).
- Silently substituting a different option than what the patient
  explicitly asked for — a different day, time, provider, or detail —
  without ever telling the patient WHY their original request couldn't
  be honored. For example, a patient asks for a Sunday appointment and
  the agent just starts offering weekday times with no mention of why
  Sunday isn't an option (closed weekends, fully booked, etc.). The
  patient ending up with a workable appointment does NOT make this okay
  — silently redirecting without explanation is itself the bug, separate
  from whether the call eventually resolved. Default this to Medium
  severity.
- Disclosing or acting on protected health information (appointment
  details, medication, visit history) for someone who has not been
  identity-verified — this is a privacy/compliance issue, flag as High.
- The agent addresses the patient by a name that doesn't match the name
  the patient actually gave earlier in the call (e.g. patient said
  "Patricia Nguyen" and the agent later calls them something else
  entirely, like a different first name). This is a real identity/
  attentiveness error, distinct from calibration note 4's out-of-context
  hallucination — here the surrounding sentence is otherwise coherent and
  relevant, just with the wrong name substituted in. Default Medium
  severity.
- The agent re-asks for the same specific piece of information 3+ times
  after the patient has already given the same, consistent answer each
  time, without ever acknowledging receipt, confirming it, or explaining
  why it's asking again. Flag this even if the call eventually moves on
  or resolves — looping on something the patient already answered
  correctly and consistently is itself a real functional/parsing
  reliability bug, not just an inefficiency. Default Medium severity (High
  if it contributes to the call never resolving).
- Mishearing medical terminology, drug names, or spelled-out
  clarifications and proceeding on the wrong information instead of
  confirming it back to the patient.
- Processing an ongoing/chronic prescription refill without ever asking
  when the patient last saw a doctor or had a checkup for that
  condition. A real clinic should check this before refilling something
  long-term — silently approving and forwarding the refill with no
  recency check at all is a real safety-relevant gap, not a nitpick.
  Default Medium severity (High if the patient volunteers that it's been
  a long time — e.g. over a year — and the agent still doesn't react to
  that).
- Confidently stating a clinical or scheduling fact it has no way of
  actually knowing or verifying, as opposed to correctly saying it
  doesn't know or needs to check.
- Giving instructions or referencing things that only make sense in a
  different channel/context than the one the patient is actually using —
  e.g. telling someone ON A PHONE CALL to "scan the QR code at the booth"
  or "ask the front desk in person." This is a real, actionable bug
  (likely a prompt/context bleed from a different deployment surface,
  like an in-person kiosk), not a minor phrasing issue — the instruction
  is literally not actionable for this caller. Default Medium severity.
- The patient clearly signals difficulty understanding English (e.g.
  broken grammar throughout, saying "I no understand," asking what a
  word means, asking the agent to repeat or slow down), and the agent
  continues using long or complex sentences, multiple questions stacked
  in one turn, or unexplained jargon afterward instead of simplifying its
  own language. The agent does not need to be perfect about this, but a
  pattern of NOT adapting at all after clear, repeated signals is a real
  accessibility/usability gap worth flagging. Default Medium severity.
- Losing track of context when the call shifts to a second, unrelated
  request, or failing to confirm a correction the patient explicitly
  made. This specifically means: after the patient corrects a piece of
  their own data (date of birth, name, etc.), the agent's response must
  explicitly restate the corrected VALUE back (e.g. "I've updated your
  date of birth to April 12, 1990") for it to count as confirmed. A
  generic acknowledgment phrase alone — "thanks for the update," "got
  it," "noted" — without repeating the actual corrected value back does
  NOT count as confirmation and should still be flagged. The test is:
  could the patient (or someone reading only the transcript) tell which
  value is now on file? If not, flag it.
- Failing to ask for or check information it should have before taking
  an action; misunderstanding or ignoring what the patient actually said;
  giving medical advice/diagnosis it shouldn't; talking over the patient
  or cutting off an unfinished sentence (especially one correcting
  identity/record data); failing to recover gracefully from an unclear
  request.
- Emotional insensitivity: the patient is visibly upset, frustrated,
  angry, or distressed (raised tone, sighing, complaining about having
  to repeat themselves, demanding a real answer, expressing anger about
  being made to wait), and the agent responds in a flat, robotic, purely
  transactional way — ignoring the emotion entirely, repeating a generic
  script line, asking for more redundant information without
  acknowledging the frustration, or otherwise failing to adjust its tone
  at all in response to a clearly emotional caller. This is a real,
  reportable bug even when the agent eventually gets the task done
  correctly — getting the facts right while ignoring how upset the
  patient sounds is still a bug. Default this to Low or Medium severity
  (it's a quality/empathy gap, not a functional or safety failure) unless
  the caller is in real distress over something urgent (e.g. concerning
  test results) and is given no acknowledgment at all, in which case
  Medium is more appropriate. Do not flag this for a caller who is calm
  or only mildly impatient — this is specifically for clearly emotional
  callers being met with a flat, unresponsive tone.

Two important calibration notes, both based on real mistakes this exact
process has made before:

1. Do NOT attempt to independently verify whether a stated calendar date
   falls on a particular day of the week (e.g. "is July 7th really a
   Tuesday?"). Language models are unreliable at this arithmetic, and
   doing it yourself has previously produced false-positive "bugs" for
   dates that were actually correct. Only flag a date/day problem if the
   agent's OWN statements within the call are internally inconsistent
   (e.g. it calls the same appointment "Tuesday" in one line and
   "Thursday" in another) — never compute the weekday yourself.

2. Transcripts may contain short bracketed tags — a legend at the top of
   the transcript (if any tags are used) explains each one. In short:
   "[UNAVAILABLE]" means no transcription ever arrived for that turn.
   "[HALLUCINATION — raw: ...]" means a known speech-to-text artifact
   (e.g. a foreign-language or out-of-place phrase from silence/noise),
   not something actually said — never use it as evidence for a bug
   about the clinic agent, beyond optionally noting the hallucination
   itself as a separate transcription-reliability finding per
   calibration note 4 below.
   "[NO SPEECH]" means that turn was cancelled before any speech was
   generated (a barge-in) — there is nothing to analyze there.
   A PATIENT BOT line ending in "[CUT SHORT?]" means the system isn't
   certain the audio matched the full text shown (the response was
   interrupted partway through or right after finishing). Since this is
   the PATIENT's line, never use it as a basis for a bug about the
   clinic agent anyway — but specifically do not assume the agent heard
   or responded to the full text shown; if the agent's next line seems
   to respond to something not fully said, that is more likely explained
   by this uncertainty than by the agent ignoring or hallucinating
   context.

3. Do NOT flag it as a bug if the same proper name (especially an
   unusual or foreign-sounding one, like a doctor's name) is spelled or
   transcribed slightly differently in different places in the
   transcript (e.g. "Dr. Zbigniew Lukoski" vs "Dr. Zedniew Likoski" vs
   "Dr. Z. Bignew-Lukosky"). This is overwhelmingly likely to be Whisper
   mishearing the same spoken name differently each time it's said, not
   the agent actually assigning different providers. Only flag a
   provider/identity mismatch if the transcript shows the agent referring
   to clearly different, unrelated names (not phonetic variants of the
   same name) or other substantive contradictory facts (different dates,
   times, or appointment details) alongside the name discrepancy.

4. Watch for a single CLINIC AGENT line that is completely unrelated to
   the surrounding conversation — e.g. a religious phrase or mantra, an
   advertisement-like phrase, song lyrics, or any other sentence that has
   no plausible connection to a medical scheduling call. This is a known
   speech-to-text hallucination pattern (the same family of issue as a
   foreign-language broadcast phrase, just in English/Latin script this
   time, so it isn't always caught automatically before reaching you).
   Do NOT build a bug around its literal content (e.g. don't treat it as
   the agent actually saying something inappropriate) — instead report
   it as its own separate, distinct finding: "Bug: Likely speech-to-text
   hallucination mid-call", Severity Low, quoting the exact out-of-place
   line, with "Why it matters" noting it's a transcription/audio
   reliability concern worth the engineering team's attention, not a
   real statement by the agent.

Do NOT report minor phrasing/punctuation nitpicks.

Before giving your final answer, work through this checklist explicitly
under a "Checklist:" heading — this step is mandatory, do not skip it:
1. List every distinct personal/scheduling detail the patient stated
   (name, DOB, appointment day/time, insurance, reason for visit) and
   every time the patient corrected one of these after first stating it.
2. For each correction found in step 1, locate the agent's next response
   and check: does it explicitly restate the corrected VALUE? Write
   yes/no for each one.
3. List every distinct factual claim the agent made about scheduling,
   the patient's records, or clinic policy. Check whether any two of
   these claims contradict each other anywhere else in the call. (Do
   not count differently-spelled variants of the same proper name as a
   contradiction — see calibration note 3 above.)
4. Check whether the call ends with the patient's original stated goal
   actually achieved. If not, check whether the agent gave a clear,
   non-contradictory reason why.
5. Check whether the patient expresses clear emotion anywhere in the
   call (frustration, anger, distress, impatience, sighing, complaining
   about repeating themselves, etc.). If so, look at the agent's very
   next response: does it acknowledge the emotion in any way (e.g. "I
   understand this is frustrating," "I'm sorry for the wait"), or does
   it respond with a flat, purely transactional line as if nothing
   emotional was said? Note yes/no.
6. Check whether the patient explicitly asked for a specific day, time,
   provider, or other option, and whether the agent ended up offering or
   booking something different. If so, did the agent ever explain WHY
   the original request couldn't be honored? Note yes/no.
7. Scan every CLINIC AGENT line for one that is semantically unrelated
   to a medical scheduling call (see calibration note 4 above) — note
   any such line found, even if you're not fully sure.
8. Note the patient's name as first given. Scan every later CLINIC AGENT
   line that directly addresses the patient by name — does any of them
   use a different name? Note yes/no.
9. Pick out any single piece of information (a date, an address, a
   detail like "city and state") that the agent asked for more than
   once. For each one, check whether the patient's answer was the same
   each time, and whether the agent ever acknowledged or moved on after
   receiving it, or just kept re-asking. Note yes/no for each.
10. If this call involves a prescription/medication refill, check
    whether the agent asked about the patient's last visit/checkup for
    that condition at any point. Note yes/no.
11. If the patient's speech shows signs of limited English proficiency
    (broken grammar, "I no understand," asking what words mean, asking
    for repetition), check whether the agent's later turns ever got
    SIMPLER/shorter in response, or stayed just as complex throughout.
    Note yes/no.
12. Scan every CLINIC AGENT line for an instruction or reference that
    only makes sense in person or on a different channel (a QR code, a
    booth, a kiosk, "the front desk," visiting in person) given this is a
    PHONE call. Note any such line found.

After the checklist, under a "Findings:" heading, output one entry for
each real issue your checklist surfaced, in this exact format:

Bug: <one-line summary>
Severity: <High|Medium|Low>
Quote: "<the exact line(s) from the transcript that show the problem>"
Why it matters: <1-2 sentences, citing the contradicted ground-truth fact if applicable>

If your checklist surfaced no real issues, write exactly:
"No significant issues found." under the Findings heading.
"""

# A single GPT-4o pass over a transcript is not reliable enough to run
# unattended (no human review step exists downstream), so multiple
# independent passes are sampled and merged — a standard way to raise
# recall on LLM-based detection tasks, since a bug missed in one sample is
# often caught in another.
N_SAMPLES = 3

CONSOLIDATION_PROMPT = """
You will be given several independent draft bug-finding passes over the
same call transcript. Merge them into one clean, deduplicated list of
genuinely distinct issues:

- If multiple drafts describe the same underlying bug (even if worded
  differently or with different quoted snippets), merge them into ONE
  entry. Use the clearest description and the quote that best illustrates
  it. If severities differ across drafts for the same bug, use the
  highest one mentioned.
- Do not include an issue that appears clearly hallucinated or
  unsupported on a second look (e.g. claims about calendar weekday
  arithmetic, or anything attributed to a line marked as a transcription
  artifact).
- Keep the same output format as the drafts:

Bug: <one-line summary>
Severity: <High|Medium|Low>
Quote: "<the exact line(s) from the transcript that show the problem>"
Why it matters: <1-2 sentences>

If, after merging, there are no genuine issues left, say exactly:
"No significant issues found."
"""


def load_ground_truth() -> str:
    if not KNOWLEDGE_BASE_PATH.exists():
        return "(no ground-truth facts file found)"
    return KNOWLEDGE_BASE_PATH.read_text(encoding="utf-8")


def extract_findings(text: str) -> str:
    """Each sample includes a mandatory 'Checklist:' scratch-work section
    before 'Findings:' — only the Findings section is a real verdict."""
    marker_idx = text.lower().rfind("findings:")
    if marker_idx == -1:
        return text.strip()
    return text[marker_idx + len("findings:"):].strip()


def _is_no_issues(findings_text: str) -> bool:
    return findings_text.strip().rstrip(".").lower() == "no significant issues found"


def analyze(call_sid: str) -> str:
    transcript_path = TRANSCRIPTS_DIR / f"{call_sid}.txt"
    transcript = transcript_path.read_text(encoding="utf-8")
    ground_truth = load_ground_truth()

    user_content = (
        f"GROUND TRUTH FACTS about the clinic (use these to catch factual "
        f"errors, not just internal contradictions):\n{ground_truth}\n\n"
        f"--- TRANSCRIPT ---\n{transcript}"
    )

    sample_findings = []
    for _ in range(N_SAMPLES):
        completion = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.7,
            messages=[
                {"role": "system", "content": RUBRIC},
                {"role": "user", "content": user_content},
            ],
        )
        sample_findings.append(extract_findings(completion.choices[0].message.content))

    real_findings = [f for f in sample_findings if not _is_no_issues(f)]

    if not real_findings:
        result = "No significant issues found."
    else:
        consolidation_input = "\n\n---\n\n".join(
            f"DRAFT {i + 1}:\n{s}" for i, s in enumerate(real_findings)
        )
        consolidation = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            messages=[
                {"role": "system", "content": CONSOLIDATION_PROMPT},
                {"role": "user", "content": consolidation_input},
            ],
        )
        result = consolidation.choices[0].message.content

    # Filenames are "{scenario_key}_{CallSid}" — recover the scenario's
    # description for context at the top of the report.
    scenario_description = next(
        (info["description"] for key, info in SCENARIOS.items() if call_sid.startswith(key)),
        None,
    )

    # Relative paths (from bug_reports/) so links resolve both locally and
    # on GitHub once this repo is pushed.
    recording_link = f"[../recordings/{call_sid}.mp3](../recordings/{call_sid}.mp3)"
    transcript_link = f"[../transcripts/{call_sid}.txt](../transcripts/{call_sid}.txt)"
    header = (
        (f"What this call was testing: {scenario_description}\n" if scenario_description else "")
        + f"Recording: {recording_link}\nTranscript: {transcript_link}\n\n"
    )

    out_path = BUG_REPORTS_DIR / f"{call_sid}.md"
    out_path.write_text(header + result, encoding="utf-8")
    print(f"Wrote {out_path}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("call_sid", nargs="?")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        for path in TRANSCRIPTS_DIR.glob("*.txt"):
            analyze(path.stem)
    elif args.call_sid:
        analyze(args.call_sid)
    else:
        parser.error("Provide a call_sid or use --all")
