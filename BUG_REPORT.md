# Bug Report

Auto-generated from every draft in `bug_reports/*.md` by `generate_bug_report.py` — this file is regenerated from scratch after every call (see `app/server.py`) and by running that script directly. Each draft is itself produced by `analyze.py` sampling GPT-4o multiple times against a fixed rubric and merging the results, specifically to reduce both false positives (e.g. calendar-arithmetic hallucinations) and false negatives (a bug missed on a single pass) — see `analyze.py`'s docstring and rubric for the calibration history behind those choices.

Findings are ranked by severity within each call.

**Note on duplicate scenarios:** `simple_scheduling`, `reschedule`, and `cancel` each appear twice — once tagged `[EARLIER VERSION]` (an early call in this project's development, kept intentionally for comparison rather than discarded) and once tagged `[LATEST VERSION]` (re-run after all fixes in this session: interruption/patience tuning, more natural speech, transcript accuracy flagging, role-confusion fixes, etc.). All other scenarios were de-duplicated down to a single latest-version call each. See each call's "What this call was testing" line for which version it is.

---

## Call: accented_speech_stress_CA268bcc55e62d268e05ee106c4e79b9ab
**What this call was testing:** Heavily Italian-accented English speaker — stresses ASR robustness to non-native accents, not vocabulary
- Recording: [recordings/accented_speech_stress_CA268bcc55e62d268e05ee106c4e79b9ab.mp3](recordings/accented_speech_stress_CA268bcc55e62d268e05ee106c4e79b9ab.mp3)
- Transcript: [transcripts/accented_speech_stress_CA268bcc55e62d268e05ee106c4e79b9ab.txt](transcripts/accented_speech_stress_CA268bcc55e62d268e05ee106c4e79b9ab.txt)

**Bug 1 — Inconsistent handling of appointment status**
- Severity: **High**
- Caught: "It appears the system thinks you already have a routine check-up appointment booked." / "There are no open cases for you."
- Why it matters / what should have happened: The agent contradicts itself about whether there is an existing appointment in the system, which confuses the patient and prevents them from booking a new appointment. This contradiction likely prevented the patient from successfully achieving their goal during the call.

**Bug 2 — Call ends without achieving the patient's goal**
- Severity: **High**
- Caught: "I'm not able to finish the booking right now because the system thinks you already have an appointment." / "Your appointment isn't booked yet. The clinic support team will contact you soon to confirm and schedule your morning appointment for next week."
- Why it matters / what should have happened: The call ended without booking the appointment, and the agent’s explanation was contradictory and unclear, leaving the patient without a resolution. The patient's goal of booking an appointment is not achieved within the call, requiring further action.

---

## Call: asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be
**What this call was testing:** Hard-to-hear medication name/spelling — stresses speech recognition, not the agent's judgment
- Recording: [recordings/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.mp3](recordings/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.mp3)
- Transcript: [transcripts/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.txt](transcripts/asr_stress_drug_name_CA0659c6f89d0e6c454ee36d10a2d5a9be.txt)

**Bug 1 — Agent repeatedly asked for city and state of pharmacy**
- Severity: **Medium**
- Caught: "Could you tell me the city in California where Midtown Pharmacy is located?" after the patient had already stated, "It’s Riverside, California."
- Why it matters / what should have happened: The agent repeatedly asked for the same information, indicating a failure to register or acknowledge the patient's consistent answer, which could lead to frustration and inefficiency in resolving patient requests.

**Bug 2 — Agent failed to confirm corrected date of birth**
- Severity: **Medium**
- Caught: "PATIENT BOT: As I was saying, my date of birth is actually May 12, 1985. I'm calling to refill my prescription for hydrochlorothiazide. CLINIC AGENT: Thanks for clarifying your date of birth"
- Why it matters / what should have happened: The agent did not explicitly restate the corrected date of birth, which could lead to incorrect information being used in the patient's records.

**Bug 3 — Likely speech-to-text hallucination mid-call**
- Severity: **Low**
- Caught: "Thanks for stalling that, Al."
- Why it matters / what should have happened: This is a transcription/audio reliability concern worth the engineering team's attention, as it indicates a potential issue in speech-to-text processing.

---

## Call: cancel_CA76083212a973d140b8f07e272ff7f4d1
**What this call was testing:** Caller wants to cancel an appointment outright, no reschedule — [EARLIER VERSION] kept intentionally for comparison; predates later fixes (patience/interruption tuning, natural speech, transcript accuracy flags, role-confusion fixes) — see LATEST VERSION call for the same scenario
- Recording: [recordings/cancel_CA76083212a973d140b8f07e272ff7f4d1.mp3](recordings/cancel_CA76083212a973d140b8f07e272ff7f4d1.mp3)
- Transcript: [transcripts/cancel_CA76083212a973d140b8f07e272ff7f4d1.txt](transcripts/cancel_CA76083212a973d140b8f07e272ff7f4d1.txt)

**Bug 1 — Appointment linked to incorrect identity without proper verification**
- Severity: **High**
- Caught: "Your patient profile is set up and your date of birth is July 4, 2000."
- Why it matters / what should have happened: The clinic agent incorrectly sets up a patient profile without proper identity verification, using an unconfirmed date of birth. This poses a risk of privacy violations by exposing or acting on another patient's information without authorization and contradicts best practices for handling sensitive information.

**Bug 2 — Misidentification of appointment date and provider**
- Severity: **Medium**
- Caught: "I see you have an appointment with Dr. Zabigniew Likoski next Friday, July 10th."
- Why it matters / what should have happened: The CLINIC AGENT repeatedly confuses the date of the appointment as well as the provider's name. The agent refers to an appointment date (July 10th) and a provider not confirmed in the ground truth (Dr. Zbigniew Lukoski), leading to patient frustration and potentially improper handling of appointment cancellations.

---

## Call: cancel_CAd6e5eec358b9e589b44929f7d475f84b
**What this call was testing:** Caller wants to cancel an appointment outright, no reschedule — [LATEST VERSION] all fixes from this development session applied (see EARLIER VERSION call below for the same scenario, for direct comparison)
- Recording: [recordings/cancel_CAd6e5eec358b9e589b44929f7d475f84b.mp3](recordings/cancel_CAd6e5eec358b9e589b44929f7d475f84b.mp3)
- Transcript: [transcripts/cancel_CAd6e5eec358b9e589b44929f7d475f84b.txt](transcripts/cancel_CAd6e5eec358b9e589b44929f7d475f84b.txt)

**Bug 1 — Appointment cancellation not confirmed**
- Severity: **High**
- Caught: "Wait, hold on—just to confirm, is my appointment actually canceled now?" followed by "[call ended: clinic line disconnected first, not our bot]"
- Why it matters / what should have happened: The patient's request to cancel their appointment was not confirmed by the agent, leaving the patient uncertain about the status of their appointment. This lack of resolution could lead to confusion and inconvenience for the patient, affecting their ability to manage their schedule and plan future appointments.

---

## Call: frustrated_patient_CA9dbd41e2527c7d6f69c54c2acb35dc5d
**What this call was testing:** Emotionally charged, impatient and increasingly angry caller — tests tone handling and empathy under real pressure
- Recording: [recordings/frustrated_patient_CA9dbd41e2527c7d6f69c54c2acb35dc5d.mp3](recordings/frustrated_patient_CA9dbd41e2527c7d6f69c54c2acb35dc5d.mp3)
- Transcript: [transcripts/frustrated_patient_CA9dbd41e2527c7d6f69c54c2acb35dc5d.txt](transcripts/frustrated_patient_CA9dbd41e2527c7d6f69c54c2acb35dc5d.txt)

**Bug 1 — Agent failed to confirm corrected DOB explicitly**
- Severity: **High**
- Caught: "Your patient profile is set up and your date of birth is July 4, 2000." / "One moment while I update your information and document your request about the test results."
- Why it matters / what should have happened: The agent did not restate the corrected date of birth, leaving ambiguity about whether the patient profile was updated correctly. This could lead to potential issues in identity verification and handling patient information.

**Bug 2 — Emotional insensitivity to patient frustration**
- Severity: **Medium**
- Caught: "I understand you're waiting to hear back about your test results." and subsequent transactional responses without empathy.
- Why it matters / what should have happened: The agent's failure to acknowledge the patient's frustration could escalate emotions and reduce patient satisfaction with the service.

---

## Call: identity_verification_probe_CA0e5c186e3930516973c4ca04c9e03ac7
**What this call was testing:** Tests whether the agent verifies identity before disclosing protected info (HIPAA-relevant)
- Recording: [recordings/identity_verification_probe_CA0e5c186e3930516973c4ca04c9e03ac7.mp3](recordings/identity_verification_probe_CA0e5c186e3930516973c4ca04c9e03ac7.mp3)
- Transcript: [transcripts/identity_verification_probe_CA0e5c186e3930516973c4ca04c9e03ac7.txt](transcripts/identity_verification_probe_CA0e5c186e3930516973c4ca04c9e03ac7.txt)

**Bug 1 — Incorrect patient profile creation due to mishearing**
- Severity: **Medium**
- Caught: "Wiesa Brooks Patient Profile has been created."
- Why it matters / what should have happened: The agent inaccurately created a profile with a misheard name ("Wiesa Brooks" instead of "Lisa Brooks"), which could lead to data inaccuracies and future confusion in patient records.

**Bug 2 — Assigning a demo date of birth without verification**
- Severity: **Medium**
- Caught: "and her date of birth is July 4, 2000 for demo purposes."
- Why it matters / what should have happened: Assigning a date of birth without verification can lead to incorrect patient records and potential privacy issues, as it creates an inaccurate profile for a person without their consent or accurate information.

---

## Call: insurance_question_CA6560c6d5fc9a742d17a440bb762add65
**What this call was testing:** Insurance/billing FAQ
- Recording: [recordings/insurance_question_CA6560c6d5fc9a742d17a440bb762add65.mp3](recordings/insurance_question_CA6560c6d5fc9a742d17a440bb762add65.mp3)
- Transcript: [transcripts/insurance_question_CA6560c6d5fc9a742d17a440bb762add65.txt](transcripts/insurance_question_CA6560c6d5fc9a742d17a440bb762add65.txt)

**Bug 1 — Call ended without resolving the patient's inquiry about insurance acceptance and self-pay costs**
- Severity: **High**
- Caught: "For your question about Aetna, insurance, and self-pay costs, I don't have access to that information without a patient profile. Please check with the front desk staff at the booth for details on accepted insurance and pricing."
- Why it matters / what should have happened: The patient's request for information was not fulfilled, and the agent's response was not helpful or actionable over the phone, leaving the patient's inquiry unresolved.

**Bug 2 — Unactionable instruction to scan a QR code at the booth during a phone call**
- Severity: **Medium**
- Caught: "You can scan the QR code at the booth to create a profile later if you decide to."
- Why it matters / what should have happened: This instruction is inappropriate for a phone call context, as the patient cannot scan a QR code over the phone, leading to confusion and an inability to proceed.

---

## Call: interruption_barge_in_CAeec0c33932fa622927f3dce5af71aa1b
**What this call was testing:** Caller interrupts the agent mid-sentence to test barge-in handling
- Recording: [recordings/interruption_barge_in_CAeec0c33932fa622927f3dce5af71aa1b.mp3](recordings/interruption_barge_in_CAeec0c33932fa622927f3dce5af71aa1b.mp3)
- Transcript: [transcripts/interruption_barge_in_CAeec0c33932fa622927f3dce5af71aa1b.txt](transcripts/interruption_barge_in_CAeec0c33932fa622927f3dce5af71aa1b.txt)

**Bug 1 — Call ends without achieving the patient's goal of canceling the appointment.**
- Severity: **High**
- Caught: "I can't complete the cancellation right now, but I'll connect you to our patient support team... Goodbye."
- Why it matters / what should have happened: The patient's request to cancel the appointment was not fulfilled, and the call ended abruptly without connecting them to further support or providing a coherent explanation, leading to an unresolved issue and potential patient dissatisfaction.

**Bug 2 — Emotional insensitivity to the patient's confusion and request for confirmation.**
- Severity: **Medium**
- Caught: "Goodbye."
- Why it matters / what should have happened: The patient was seeking confirmation about the cancellation, and the agent ignored the emotional context, failing to provide reassurance or acknowledgment, which can lead to patient dissatisfaction and confusion.

---

## Call: low_english_proficiency_CA630566cfb23d75a9db6f6fea4b6c637e
**What this call was testing:** Caller has limited English proficiency and doesn't speak Spanish either — tests whether the clinic simplifies, slows down, and confirms understanding, as opposed to the accent-only stress test
- Recording: [recordings/low_english_proficiency_CA630566cfb23d75a9db6f6fea4b6c637e.mp3](recordings/low_english_proficiency_CA630566cfb23d75a9db6f6fea4b6c637e.mp3)
- Transcript: [transcripts/low_english_proficiency_CA630566cfb23d75a9db6f6fea4b6c637e.txt](transcripts/low_english_proficiency_CA630566cfb23d75a9db6f6fea4b6c637e.txt)

**Bug 1 — Date of birth correction not confirmed back to the patient**
- Severity: **Medium**
- Caught: "I can't update your date of birth directly but I'll let the clinic support team know you need this changed. They'll follow up with you soon."
- Why it matters / what should have happened: The agent did not confirm the corrected date of birth back to the patient, leading to potential confusion about what information is on file. This could cause issues with identity verification in future interactions.

**Bug 2 — Agent did not simplify language for patient with limited English proficiency**
- Severity: **Medium**
- Caught: "To book an appointment, I need to create a simple patient profile for you. This is just a basic record with your first and last name. Would you like to continue?"
- Why it matters / what should have happened: The patient showed signs of difficulty understanding English, but the agent continued to use complex language, which could hinder effective communication and lead to misunderstandings.

---

## Call: medication_refill_CAecca4f3694ae9dc9d2e377acfd6feeea
**What this call was testing:** Routine prescription refill request
- Recording: [recordings/medication_refill_CAecca4f3694ae9dc9d2e377acfd6feeea.mp3](recordings/medication_refill_CAecca4f3694ae9dc9d2e377acfd6feeea.mp3)
- Transcript: [transcripts/medication_refill_CAecca4f3694ae9dc9d2e377acfd6feeea.txt](transcripts/medication_refill_CAecca4f3694ae9dc9d2e377acfd6feeea.txt)

**Bug 1 — Failure to confirm corrected callback number.**
- Severity: **High**
- Caught: "PATIENT BOT: Sure, the complete number is 424-408-4639."
- Why it matters / what should have happened: The agent repeatedly asked for the callback number but failed to confirm or acknowledge the corrected number, leading to potential issues in further communication for the prescription refill.

**Bug 2 — Unable to locate confirmed CVS pharmacy location.**
- Severity: **High**
- Caught: "CLINIC AGENT: I do not see a CVS on Ventura Boulevard or near Van Nuys Boulevard in the list of available pharmacies for Los Angeles."
- Why it matters / what should have happened: The agent failed to recognize a verified real-world pharmacy location, preventing the patient from completing their prescription refill request. This contradicts the verified pharmacy location in the ground truth.

**Bug 3 — Call ended without resolving the patient's request.**
- Severity: **High**
- Caught: "[call ended by bot: max call duration of 240s exceeded]"
- Why it matters / what should have happened: The call ended without achieving the patient's goal of refilling their prescription, and the agent did not provide a clear resolution or next steps, leaving the patient's request unresolved.

---

## Call: multi_intent_call_CA11f24fe10cef26a9afd3c36ac220e5cc
**What this call was testing:** Two unrelated requests stacked in one call — tests context-tracking across topics
- Recording: [recordings/multi_intent_call_CA11f24fe10cef26a9afd3c36ac220e5cc.mp3](recordings/multi_intent_call_CA11f24fe10cef26a9afd3c36ac220e5cc.mp3)
- Transcript: [transcripts/multi_intent_call_CA11f24fe10cef26a9afd3c36ac220e5cc.txt](transcripts/multi_intent_call_CA11f24fe10cef26a9afd3c36ac220e5cc.txt)

**Bug 1 — Miscommunication in medication name during the refill request.**
- Severity: **Medium**
- Caught: "I've sent your refill request for a Tortoise Dot into our clinic support team."
- Why it matters / what should have happened: The agent miscommunicated the medication name "atorvastatin" as "Tortoise Dot," which could lead to a delay or error in processing the patient's medication refill request, affecting patient care and prescription accuracy.

---

## Call: office_hours_location_CAec836cb60231191acd4505398581d003
**What this call was testing:** Simple FAQ — hours and address
- Recording: [recordings/office_hours_location_CAec836cb60231191acd4505398581d003.mp3](recordings/office_hours_location_CAec836cb60231191acd4505398581d003.mp3)
- Transcript: [transcripts/office_hours_location_CAec836cb60231191acd4505398581d003.txt](transcripts/office_hours_location_CAec836cb60231191acd4505398581d003.txt)

**Bug 1 — The agent refused to provide basic information (Saturday hours and location) without creating a profile.**
- Severity: **High**
- Caught: "For now, I'm unable to provide the Saturday hours without a profile. Is there anything else I can help you with today?"
- Why it matters / what should have happened: The agent should be able to provide basic information such as office hours and location without requiring the creation of a patient profile. This refusal prevents the patient from obtaining necessary information and achieving their goal, leading to frustration and negatively impacting the user experience.

**Bug 2 — Emotional insensitivity to the patient's mild frustration.**
- Severity: **Low**
- Caught: "Is there anything else I can help with?"
- Why it matters / what should have happened: The agent failed to acknowledge the patient's frustration, which could lead to a poor customer experience.

---

## Call: out_of_scope_request_CAf71979efdcaf46350fe084f96ea091a4
**What this call was testing:** Caller asks something the agent likely can't / shouldn't answer, to test refusal handling
- Recording: [recordings/out_of_scope_request_CAf71979efdcaf46350fe084f96ea091a4.mp3](recordings/out_of_scope_request_CAf71979efdcaf46350fe084f96ea091a4.mp3)
- Transcript: [transcripts/out_of_scope_request_CAf71979efdcaf46350fe084f96ea091a4.txt](transcripts/out_of_scope_request_CAf71979efdcaf46350fe084f96ea091a4.txt)

**Bug 1 — Call ended without patient's goal being achieved.**
- Severity: **High**
- Caught: "Sure, just to confirm, we’re actually getting connected now, right? ... Goodbye. [end_call requested by bot: The user was transferred, and the representative has ended the call.]"
- Why it matters / what should have happened: The call ended without the patient being connected to a healthcare professional as intended, leaving the patient's concern about their headache unresolved. This prevents the patient from receiving the needed assistance.

---

## Call: refill_no_recent_visit_CAe12573682abd2d42fc712763cf5d620d
**What this call was testing:** Refill request edge case — patient hasn't had a checkup in a long time, agent should flag it
- Recording: [recordings/refill_no_recent_visit_CAe12573682abd2d42fc712763cf5d620d.mp3](recordings/refill_no_recent_visit_CAe12573682abd2d42fc712763cf5d620d.mp3)
- Transcript: [transcripts/refill_no_recent_visit_CAe12573682abd2d42fc712763cf5d620d.txt](transcripts/refill_no_recent_visit_CAe12573682abd2d42fc712763cf5d620d.txt)

**Bug 1 — Agent did not confirm the corrected callback number.**
- Severity: **Medium**
- Caught: "Actually, that doesn't sound right. My number should be 424-408-4629."
- Why it matters / what should have happened: Failing to confirm the corrected callback number can lead to communication issues if the clinic needs to follow up with the patient, impacting the reliability of the service.

**Bug 2 — No checkup inquiry for prescription refill**
- Severity: **Medium**
- Caught: "I've documented your metformin refill request for our clinic support team."
- Why it matters / what should have happened: The agent did not inquire about the patient's last visit or checkup, which is important for ensuring ongoing prescription accuracy and patient safety.

---

## Call: reschedule_CA70dfcca5e6209d18a31fec80a9130b33
**What this call was testing:** Caller wants to move an existing appointment — [LATEST VERSION] all fixes from this development session applied (see EARLIER VERSION call below for the same scenario, for direct comparison)
- Recording: [recordings/reschedule_CA70dfcca5e6209d18a31fec80a9130b33.mp3](recordings/reschedule_CA70dfcca5e6209d18a31fec80a9130b33.mp3)
- Transcript: [transcripts/reschedule_CA70dfcca5e6209d18a31fec80a9130b33.txt](transcripts/reschedule_CA70dfcca5e6209d18a31fec80a9130b33.txt)

**Bug 1 — Failure to confirm corrected last name spelling**
- Severity: **Medium**
- Caught: "Can you please confirm your last name is spelled C-H-E-R-D?" ... "Sure, it's spelled C-H-E-N."
- Why it matters / what should have happened: The agent failed to explicitly confirm the corrected spelling of the patient's last name, which could lead to issues in correctly identifying or managing the patient's profile.

---

## Call: simple_scheduling_CAdd2afa88f0c0a278711082c65ff18b5e
**What this call was testing:** Straightforward new appointment booking — [LATEST VERSION] all fixes from this development session applied (see EARLIER VERSION call below for the same scenario, for direct comparison)
- Recording: [recordings/simple_scheduling_CAdd2afa88f0c0a278711082c65ff18b5e.mp3](recordings/simple_scheduling_CAdd2afa88f0c0a278711082c65ff18b5e.mp3)
- Transcript: [transcripts/simple_scheduling_CAdd2afa88f0c0a278711082c65ff18b5e.txt](transcripts/simple_scheduling_CAdd2afa88f0c0a278711082c65ff18b5e.txt)

**Bug 1 — Agent failed to confirm corrected Date of Birth**
- Severity: **Medium**
- Caught: "Actually, my date of birth is March 15, 1988."
- Why it matters / what should have happened: Failing to confirm the corrected date of birth can lead to inaccuracies in the patient's profile, which could affect future interactions or appointments.

---

## Call: sunday_request_edge_case_CA8795f52779dcba1ee52e9b0219a81735
**What this call was testing:** Deliberately tests whether the agent checks office hours before confirming
- Recording: [recordings/sunday_request_edge_case_CA8795f52779dcba1ee52e9b0219a81735.mp3](recordings/sunday_request_edge_case_CA8795f52779dcba1ee52e9b0219a81735.mp3)
- Transcript: [transcripts/sunday_request_edge_case_CA8795f52779dcba1ee52e9b0219a81735.txt](transcripts/sunday_request_edge_case_CA8795f52779dcba1ee52e9b0219a81735.txt)

**Bug 1 — Appointment provider name inconsistency**
- Severity: **Medium**
- Caught: "The earliest morning slot, later in the week, is Thursday, July 2nd at 8 a.m. with Judy Hauser." / "You are booked for an in-person appointment with Dr. Dubie Hauser at Pivot Point Orthopedics on Thursday, July 2nd at 8 a.m."
- Why it matters / what should have happened: The agent inconsistently stated the provider's name, which could lead to confusion for the patient regarding who they are scheduled to see.

**Bug 2 — No explanation for unavailable Sunday appointment**
- Severity: **Medium**
- Caught: Patient requested: "I'd like to book an appointment for this Sunday at 10 a.m., please." Agent did not explain why Sunday was unavailable.
- Why it matters / what should have happened: The agent did not provide a reason why the requested Sunday appointment was unavailable, which could leave the patient confused about the clinic's scheduling policies or availability.

**Bug 3 — Unrelated line in the conversation**
- Severity: **Low**
- Caught: "Aum Namah Shivaya."
- Why it matters / what should have happened: This line is unrelated to the context of a medical scheduling call and indicates a possible transcription or audio processing error that could confuse or disrupt the patient experience.

---

## Call: unclear_request_CA85988a5a2e02fa620befb9c3e2b02347
**What this call was testing:** Vague/ambiguous opening request to see how the agent disambiguates
- Recording: [recordings/unclear_request_CA85988a5a2e02fa620befb9c3e2b02347.mp3](recordings/unclear_request_CA85988a5a2e02fa620befb9c3e2b02347.mp3)
- Transcript: [transcripts/unclear_request_CA85988a5a2e02fa620befb9c3e2b02347.txt](transcripts/unclear_request_CA85988a5a2e02fa620befb9c3e2b02347.txt)

**Bug 1 — Failure to resolve appointment discrepancy and address the patient's request.**
- Severity: **High**
- Caught: "I only have access to the appointment on Thursday, July 2nd at 8am at Nashville 220 Athens Way. There are no other appointments listed for you in this system. Would you like to reschedule this Thursday appointment to Monday instead?"
- Why it matters / what should have happened: The agent did not resolve the patient's request to reschedule a Friday appointment to Monday and failed to provide a clear reason why the Friday appointment could not be found, leaving the patient's issue unresolved and leading to confusion.

**Bug 2 — Failure to acknowledge and update corrected date of birth.**
- Severity: **Medium**
- Caught: "Actually, that date of birth isn’t correct. My real date of birth is March 12, 1985."
- Why it matters / what should have happened: The agent failed to acknowledge or update the corrected date of birth, which could lead to incorrect patient profile data being used for appointments and medical records.

---

## Calls with no findings

- **reschedule_CA641aeb5eddfd95eedd0f9cb93a90472e** — [recordings/reschedule_CA641aeb5eddfd95eedd0f9cb93a90472e.mp3](recordings/reschedule_CA641aeb5eddfd95eedd0f9cb93a90472e.mp3), [transcripts/reschedule_CA641aeb5eddfd95eedd0f9cb93a90472e.txt](transcripts/reschedule_CA641aeb5eddfd95eedd0f9cb93a90472e.txt)
- **simple_scheduling_retest2_CAc19de65cd616d440f8c2ed5c89f638cd** — [recordings/simple_scheduling_retest2_CAc19de65cd616d440f8c2ed5c89f638cd.mp3](recordings/simple_scheduling_retest2_CAc19de65cd616d440f8c2ed5c89f638cd.mp3), [transcripts/simple_scheduling_retest2_CAc19de65cd616d440f8c2ed5c89f638cd.txt](transcripts/simple_scheduling_retest2_CAc19de65cd616d440f8c2ed5c89f638cd.txt)