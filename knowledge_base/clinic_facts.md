<!--
Ground-truth facts about the clinic, collected from the pgai.us/athena
patient portal (the "context on how our product works" the challenge
setup pointed us to). analyze.py loads this whole file into the
bug-checking prompt so GPT-4o can catch the clinic AGENT stating
something that's wrong but internally consistent (e.g. confidently
quoting the wrong hours), not just self-contradictions within one call.

The corpus here is small on purpose — a handful of facts — so we load
the entire file as context rather than running embedding-based retrieval.
If this grows into many pages of policy docs, switch to chunk + embed +
top-k retrieval instead of stuffing everything in.

UNKNOWN fields below should be confirmed by what the agent itself says
during the office_hours_location / insurance_question test calls — if the
agent's answer in those calls becomes our best available ground truth,
note that explicitly in BUG_REPORT.md rather than treating it as
independently verified.
-->

## Clinic identity
- Name: Pivot Point Orthopedics (Pretty Good AI demo clinic)
- Confirmed test patient: Sara Aly, DOB 10/22/2001

## Location(s)
- 220 Athens Way, Nashville, TN

## Office hours
- UNKNOWN — not provided by the demo confirmation. Confirm via the
  office_hours_location test call; treat the agent's stated hours as
  provisional ground truth only, flagged as such if used to judge other
  calls.

## Insurance accepted
- UNKNOWN — not provided by the demo confirmation. Confirm via the
  insurance_question test call.

## Confirmed appointment example (from demo confirmation text)
- Date: 07/09/2026, Time: 4:30 PM
- Provider: Doogie Howser
- Patient must bring: government-issued photo ID (no copies), insurance
  card, list of current medications, imaging discs if available

## Verified real-world pharmacy facts
- A real CVS Pharmacy exists at 14735 Ventura Blvd, Sherman Oaks, CA
  91403 (near the Ventura Blvd / Van Nuys Blvd intersection), and another
  at 5601 Van Nuys Blvd — both in the Los Angeles area described by the
  `medication_refill` persona ("CVS on Ventura Blvd," "near Van Nuys
  Blvd," "Los Angeles, California"). Verified via web search, not just
  internal consistency. If the agent claims it cannot find a CVS at or
  near this location, that is a real pharmacy-lookup/integration bug, not
  a case of the patient giving a nonexistent address — flag it as such.

## Important operational note
- The phone number on the original confirmation screen, (615) 645-1400,
  is NOT the number to call for this challenge — the challenge
  instructions explicitly say not to call it. All test calls go to
  +1-805-439-8008 only.
