"""
Compiles every per-call draft in bug_reports/*.md into one final
BUG_REPORT.md — fully automatically, no manual editing step. This is
called automatically right after each call's bug-analysis draft is
written (see app/server.py), and can also be run by hand:

    python generate_bug_report.py

This file is regenerated from scratch every time it runs, so any manual
edits to BUG_REPORT.md will be overwritten the next time a call completes
or this script is run. The source of truth is bug_reports/*.md.
"""

import re
from pathlib import Path

BUG_REPORTS_DIR = Path(__file__).resolve().parent / "bug_reports"
OUT_PATH = Path(__file__).resolve().parent / "BUG_REPORT.md"

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}

BUG_BLOCK_RE = re.compile(
    r"Bug:\s*(?P<title>.+?)\s*\n"
    r"Severity:\s*(?P<severity>High|Medium|Low)\s*\n"
    r"Quote:\s*(?P<quote>.+?)\s*\n"
    r"Why it matters:\s*(?P<why>.+?)(?=\n\s*Bug:|\Z)",
    re.DOTALL,
)


def parse_draft(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    what_match = re.search(r"What this call was testing:\s*(.+)", text)
    recording_match = re.search(r"Recording:\s*(\[.+?\]\(.+?\))", text)
    transcript_match = re.search(r"Transcript:\s*(\[.+?\]\(.+?\))", text)

    bugs = []
    for m in BUG_BLOCK_RE.finditer(text):
        bugs.append({
            "title": m.group("title").strip(),
            "severity": m.group("severity").strip(),
            "quote": m.group("quote").strip(),
            "why": m.group("why").strip(),
        })
    bugs.sort(key=lambda b: SEVERITY_ORDER.get(b["severity"], 99))

    return {
        "call_name": path.stem,
        "what": what_match.group(1).strip() if what_match else None,
        "recording_link": recording_match.group(1) if recording_match else None,
        "transcript_link": transcript_match.group(1) if transcript_match else None,
        "bugs": bugs,
    }


def render_call_section(call: dict) -> str:
    lines = [f"## Call: {call['call_name']}"]
    if call["what"]:
        lines.append(f"**What this call was testing:** {call['what']}")
    # Drafts store paths relative to bug_reports/ (../recordings/..., etc)
    # — rewrite to be relative to the repo root, since BUG_REPORT.md lives there.
    if call["recording_link"]:
        lines.append(f"- Recording: {call['recording_link'].replace('../', '')}")
    if call["transcript_link"]:
        lines.append(f"- Transcript: {call['transcript_link'].replace('../', '')}")
    lines.append("")

    if not call["bugs"]:
        lines.append("No significant issues found in this call.")
    else:
        for i, bug in enumerate(call["bugs"], start=1):
            lines.append(f"**Bug {i} — {bug['title']}**")
            lines.append(f"- Severity: **{bug['severity']}**")
            lines.append(f"- Caught: {bug['quote']}")
            lines.append(f"- Why it matters / what should have happened: {bug['why']}")
            lines.append("")

    return "\n".join(lines)


def generate():
    draft_paths = sorted(BUG_REPORTS_DIR.glob("*.md"))
    calls = [parse_draft(p) for p in draft_paths]

    calls_with_bugs = [c for c in calls if c["bugs"]]
    calls_without_bugs = [c for c in calls if not c["bugs"]]

    sections = [
        "# Bug Report\n",
        "Auto-generated from every draft in `bug_reports/*.md` by "
        "`generate_bug_report.py` — this file is regenerated from scratch "
        "after every call (see `app/server.py`) and by running that script "
        "directly. Each draft is itself produced by `analyze.py` sampling "
        "GPT-4o multiple times against a fixed rubric and merging the "
        "results, specifically to reduce both false positives (e.g. "
        "calendar-arithmetic hallucinations) and false negatives (a bug "
        "missed on a single pass) — see `analyze.py`'s docstring and "
        "rubric for the calibration history behind those choices.\n",
        "Findings are ranked by severity within each call.\n",
        "**Note on duplicate scenarios:** `simple_scheduling`, `reschedule`, "
        "and `cancel` each appear twice — once tagged `[EARLIER VERSION]` "
        "(an early call in this project's development, kept intentionally "
        "for comparison rather than discarded) and once tagged "
        "`[LATEST VERSION]` (re-run after all fixes in this session: "
        "interruption/patience tuning, more natural speech, transcript "
        "accuracy flagging, role-confusion fixes, etc.). All other "
        "scenarios were de-duplicated down to a single latest-version call "
        "each. See each call's \"What this call was testing\" line for "
        "which version it is.\n",
        "---\n",
    ]

    for call in calls_with_bugs:
        sections.append(render_call_section(call))
        sections.append("---\n")

    if calls_without_bugs:
        sections.append("## Calls with no findings\n")
        for call in calls_without_bugs:
            recording = call["recording_link"].replace("../", "") if call["recording_link"] else ""
            transcript = call["transcript_link"].replace("../", "") if call["transcript_link"] else ""
            sections.append(f"- **{call['call_name']}** — {recording}, {transcript}")

    OUT_PATH.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(calls_with_bugs)} calls with findings, "
          f"{len(calls_without_bugs)} clean)")


if __name__ == "__main__":
    generate()
