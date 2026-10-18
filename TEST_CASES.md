# Test Cases and Results

Record of every case tried during the October 2026 review and fix pass, with the result **before** and **after** the changes. Everything in the "After" columns was produced by running the code. None of it was copied from expectations.

- Review and fixes: 2026-10-18
- Backend: Python 3.14, FastAPI 0.115, transformers 4.x, Windows 11
- Browser checks: Microsoft Edge 155 (headless), driven by Playwright

Contents:

1. [Safety probes (triage results)](#1-safety-probes-triage-results)
2. [Text extraction probes](#2-text-extraction-probes)
3. [Automated test suite](#3-automated-test-suite)
4. [API and security checks](#4-api-and-security-checks)
5. [Speech and avatar checks](#5-speech-and-avatar-checks)
6. [End-to-end browser checks](#6-end-to-end-browser-checks)
7. [How to rerun](#7-how-to-rerun)

---

## 1. Safety probes (triage results)

Each probe sends one intake straight to the triage engine. Rule IDs in brackets show why the level was chosen (see `rules-and-data/rules.json`; `S*` = critical-language override, `RF*` = risk-factor escalation).

| # | Input | Before | After | Status |
|---|---|---|---|---|
| 1 | Complaint `I'm going to die` (straight apostrophe) | GREEN (no rules) | RED (S1) | Fixed |
| 2 | Complaint `I’m gonna die` (curly apostrophe, phone keyboards) | GREEN (no rules) | RED (S1) | Fixed |
| 3 | Complaint `i think i'm dying` | GREEN (no rules) | RED (S1) | Fixed |
| 4 | Complaint `I can't breathe` | GREEN, nothing extracted | RED (R1, S3) | Fixed |
| 5 | Complaint `I want to kill myself` | GREEN (no rules) | RED (S2) + self-harm advice | Fixed |
| 6 | Complaint `i want to die` | GREEN (no rules) | RED (S2) | Fixed |
| 7 | Complaint `she is unconscious` | not tested before | RED (S4) | New |
| 8 | Complaint `no seizures, mild cough` + cough mild | not tested before | GREEN (negated, no false RED) | New |
| 9 | Rating `back_pain: 5` (old UI allowed 0–5) | GREEN (no rules) | Rejected: 422, scale is 0–3 | Fixed |
| 10 | Rating `back_pain: 3` (severe) | GREEN (no rules) | ORANGE (O1) | Fixed |
| 11 | Rating `dizziness: 3` / `5` | GREEN (no rules) | ORANGE (O7) | Fixed |
| 12 | Rating `nausea: 3` / `5` | GREEN (no rules) | ORANGE (O7) | Fixed |
| 13 | Pregnant + `bleeding: 1` | GREEN (no rules) | RED (RF1) | Fixed |
| 14 | Pregnant + `abdominal_pain: 2` | ORANGE (O1) | RED (O1, RF8) | Fixed |
| 15 | Rating `chest_pain: 99` | RED (R1), invalid input accepted | Rejected: 422 | Fixed |
| 16 | Rating `chest_pain: -4` | GREEN, invalid input accepted | Rejected: 422 | Fixed |
| 17 | Unknown symptom `made_up: 3` | GREEN, silently ignored | Rejected: 422 `Unknown symptom keys: made_up` | Fixed |
| 18 | Rating `chest_pain: 1` (mild) | GREEN (no rules) | ORANGE (O8) | Fixed* |
| 19 | Complaint `I have severe chest pain`, no ratings | GREEN (extracted as mild only) | RED (R1) | Fixed |
| 20 | Complaint `no fever, chest pain since morning`, no ratings | GREEN, chest pain dropped | ORANGE (O8) | Fixed |

\* Rule O8 ("any chest pain or breathing difficulty is at least ORANGE") is a conservative clinical choice made in this pass. It should be reviewed by a clinician.

**Existing safety scenarios** (`test_triage_safety.py`) still pass unchanged:

| Scenario | Expected | After |
|---|---|---|
| `im gonna die` | RED (S1) | PASS |
| `im ganna die` (typo) | RED (S1) | PASS |
| Diabetes + severe dehydration (3) | RED (RF4) | PASS |
| Pregnancy + `pregnancy_bleeding` | RED (RF1) | PASS |
| Elderly + chest pain mild (1) | ORANGE (RF3) | PASS |
| Cardiac history + chest pain mild (1) | ORANGE (RF7) | PASS |
| Vague complaint, no ratings | follow-up questions shown | PASS |
| Clarification completed | no follow-up questions | PASS |

**Rating-scale sweeps** (automated in `test_safety_regressions.py`):

| Check | Before | After |
|---|---|---|
| Every one of the 25 symptoms rated severe (3) alone is at least ORANGE | 9 symptoms came out GREEN (cough, sore throat, chills, fatigue, body aches, rash, nausea, dizziness, back pain) | All 25 are ORANGE or RED |
| Raising any single symptom from 0→1→2→3 never lowers the level | `back_pain` went ORANGE at 2, then GREEN at 3 | Monotonic for all 25 |

---

## 2. Text extraction probes

Output of `extract_symptoms_from_text` (symptom → rating on the 0–3 scale).

| # | Text | Before | After | Status |
|---|---|---|---|---|
| 1 | `no fever, chest pain since morning` | `{}`: "no" also hid chest pain | `{chest_pain: 1}` | Fixed |
| 2 | `not eating, headache` | `{}`: "not" hid headache | `{headache: 1}` | Fixed |
| 3 | `no fever but headache` | `{}`: the "no" three words back also hid headache | `{headache: 1}` | Fixed |
| 4 | `no fever or cough` | `{}` | `{}`: both negated, as intended | Unchanged |
| 5 | `no headache yesterday, headache today` | `{}`: only the first mention was checked | `{headache: 1}` | Fixed |
| 6 | `I don't have a fever` | `{fever: 1}`: "don't" was not a negation | `{}` | Fixed |
| 7 | `severe chest pain and mild cough` | `{chest_pain: 1, cough: 1}` | `{chest_pain: 3, cough: 1}` | Fixed |
| 8 | `I can't breathe properly` | `{}` | `{shortness_of_breath: 3}` | Fixed |

---

## 3. Automated test suite

Run from `app/backend`: `python -m unittest discover tests`

| Suite | Tests | Before | After |
|---|---|---|---|
| `test_triage_safety.py` | 8 | 8 pass | 8 pass |
| `test_triage_logging.py` | 3 | 3 pass | 3 pass |
| `test_advice_engine.py` | 2 | 2 pass | 2 pass |
| `test_nlp_extractor.py` | 5 | 5 pass | 5 pass |
| `test_hf_extractor.py` | 2 | 2 pass | 2 pass |
| `test_safety_regressions.py` (new) | 24 | — | 24 pass |
| `test_api.py` (new) | 15 | — | 15 pass |
| `test_speech.py` (new) | 9 | — | 9 pass |
| **Total** | **68** | **20 pass** | **68 pass** |

Other test-health results:

| Check | Before | After |
|---|---|---|
| `ResourceWarning: unclosed database` | One per request (connections never closed) | None (suite also passes with `-W error::ResourceWarning`) |
| Leftover `test_*.db` files in `app/backend/outputs/` | 51 files left behind | 0, tests use temp dirs that are deleted |

---

## 4. API and security checks

Automated in `test_api.py`; also checked by hand with `curl` against a running server.

| Check | Before | After |
|---|---|---|
| `GET /triage` (queue) without login | 200, patient list returned | 401 |
| `GET /triage/{id}` without login | 200, full patient record | 401 |
| PDF without login | 200 | 401 |
| Login `nurse` / `nurse2026` and `doctor` / `doctor2026` | no login existed | 200 + token |
| Wrong password / unknown user | — | 401 |
| Tampered or expired token | — | rejected |
| `POST /triage` (kiosk intake) without login | 200 | 200 (patients don't log in) |
| PDF `session_id` `../../evil`, `not-a-session`, uppercase hex | written to a path built from client input | 404/422, never touches disk |
| PDF contents | taken from client-supplied JSON | rebuilt from the stored session |
| PDF stored on server disk | yes, one file per download | no, rendered in memory |
| Triage while the NER model can't download (offline) | 500 error, triage fails (found by code reading) | 200, local extractor used, entities empty |
| `/speech` when TTS model can't load | 500, load error outside try (found by code reading) | 503 with a clean message |

---

## 5. Speech and avatar checks

| Check | How | Result |
|---|---|---|
| Server TTS with the old default `Vedika35/Vedika_text_to_speech` | `POST /speech` | **503**: the model's architecture (`vibevoice_streaming`) isn't supported by transformers 4.x, so the AI voice never worked before this pass |
| Server TTS with the new default `facebook/mms-tts-eng` | `POST /speech` with an 80-character sentence | 200, WAV returned. First call ~29 s (one-time model download), then ~1.2 s on CPU |
| Speech-to-text on real speech | Windows voice reads "I have had a bad headache and a fever since yesterday, and I feel dizzy." → `POST /speech/transcribe` | Exact transcript returned. First call 2.6 s, then 1.3 s on CPU (Whisper-tiny) |
| TTS → STT round trip | MMS voice says "Your result is orange. Please stay in the clinic. A clinician will see you today." → Whisper | "Your result is orange, please stay and the clinic a clinician will see you today." |
| STT on non-speech (beep from the fake microphone) | Browser records, sends to server | Before the guard: Whisper returned ~400 dots. After: empty text, the kiosk shows "We did not catch any words. Please try again." |
| STT on silence / clips under 0.25 s | unit tests | Empty text, model never loaded |
| STT bad input | unit tests | non-WAV 400, empty 400, over 2 MB 413, model unavailable 503 |
| Lip-sync, device voice | Browser: 8 mouth samples during narration | 6 distinct mouth shapes |
| Lip-sync, AI voice (audio loudness) | Browser: 40 samples during narration | 28 distinct mouth shapes; captions highlighted word by word |
| Mic opens while the nurse is talking | Browser | Nurse stops talking and status shows "Listening to you..." |

**Follow-up: name field gave no text (reported 2026-10-18).** A WAV of "My name is Amina Ben Salah" plus 3 s of silence was fed in as Edge's microphone:

| Mode | Before fix | After fix |
|---|---|---|
| Automatic, user waits (no Stop press) | Edge recognizer returned an empty final result; field stayed empty with **no message** | Auto-stop after the pause; name field = `Amina Bansala` ("My name is" trimmed) |
| Kiosk server, Stop pressed after 2.5 s | Worked | Works: `Amina Benson` (cut mid-name by the early Stop, as expected) |
| Browser recognition only | Empty field, no message | Empty field, but the message "We did not catch any words. Please press the microphone and speak again..." is shown |

**Follow-up 2: "The kiosk server did not respond" (reported 2026-10-18).** Root cause: a leftover dev server held port 5173, so Vite started the kiosk on **5174**. The backend only allowed origin 5173, so the browser's CORS preflight got `400 Bad Request` and every request from the page was blocked.

| Check | Before fix | After fix |
|---|---|---|
| Preflight `OPTIONS /speech/transcribe` from `http://localhost:5174` | 400 | 200 |
| Preflight from `localhost:5173`, `127.0.0.1:5175`, `[::1]:5173` | 400 except 5173 | 200 (automated test) |
| Preflight from `http://evil.example.com`, `http://localhost.evil.com:5173` | 400 | 400 (still rejected) |
| Name dictation on the kiosk at `localhost:5174` | "The kiosk server did not respond..." | `Amina Bansala` |

---

## 6. End-to-end browser checks

Full flow in Edge against the running backend and frontend:

| Step | Result |
|---|---|
| Welcome page shows "Who is filling in this form?" with patient / companion / nurse | PASS |
| Patient flow: `I’m going to die, severe chest pain` → result | RED, "Urgent: go to the nurse now", session number shown |
| Patient view hides clinical detail (rule IDs, entities, PDF) | PASS |
| Companion flow uses "Patient's name" / "What is wrong with the patient today?" | PASS |
| Pregnancy question hidden when sex = male | PASS |
| Submitting an empty form | Blocked: "Please describe the problem in words, or mark at least one symptom." |
| Staff login with wrong password | "Invalid username or password." |
| Staff login `nurse` / `nurse2026` → queue | RED patient at the top, "Entered by patient" shown |
| Open summary from queue | Full clinical view (rules R1 + S1) |
| Download Doctor PDF | `triage_<id>.pdf` downloaded (3.4 KB, valid PDF) |
| Speech input set to "Kiosk server" → record → stop | Audio sent to `/speech/transcribe`, result handled |
| JavaScript errors in the console | None (only the expected 401 from the wrong-password test) |

---

## 7. How to rerun

```powershell
# Unit + API tests (from app/backend, venv active)
python -m unittest discover tests -v

# Manual API checks (backend running on :8000)
curl http://localhost:8000/triage                       # 401 without login
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"nurse","password":"nurse2026"}'
```
