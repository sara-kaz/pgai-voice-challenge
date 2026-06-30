What this call was testing: Hard-to-hear medication name/spelling — stresses speech recognition, not the agent's judgment
Recording: [../recordings/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.mp3](../recordings/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.mp3)
Transcript: [../transcripts/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.txt](../transcripts/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.txt)

Bug: Agent repeatedly asked for city and state of pharmacy
Severity: Medium
Quote: "Could you tell me the city in California where Midtown Pharmacy is located?" after the patient had already stated, "It’s Riverside, California."
Why it matters: The agent repeatedly asked for the same information, indicating a failure to register or acknowledge the patient's consistent answer, which could lead to frustration and inefficiency in resolving patient requests.

Bug: Agent failed to confirm corrected date of birth
Severity: Medium
Quote: "PATIENT BOT: As I was saying, my date of birth is actually May 12, 1985. I'm calling to refill my prescription for hydrochlorothiazide. CLINIC AGENT: Thanks for clarifying your date of birth"
Why it matters: The agent did not explicitly restate the corrected date of birth, which could lead to incorrect information being used in the patient's records.

Bug: Likely speech-to-text hallucination mid-call
Severity: Low
Quote: "Thanks for stalling that, Al."
Why it matters: This is a transcription/audio reliability concern worth the engineering team's attention, as it indicates a potential issue in speech-to-text processing.