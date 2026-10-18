# Rural Triage Kiosk

A self-service triage kiosk for low-resource and rural clinics. The **patient** or the **person with them** (family member, friend, carer) answers simple questions on the kiosk. When nobody can do that, a **nurse** fills it in for them. The system combines symptom ratings with free-text analysis, gives a RED / ORANGE / GREEN priority, and puts the patient in a clinician queue sorted by urgency.

A virtual nurse avatar reads every screen aloud with lip-sync, and patients can **speak their answers** instead of typing.

> This is a triage **support** tool, not a diagnostic system. It helps the clinic decide who to see first. It does not replace clinical judgment.

---

## Logging In: Who Uses What

| Who | How they get in | What they can see |
|---|---|---|
| Patient | No login. Open the kiosk and choose **"I am the patient"** | Their own questions and a plain-language result with a number to show the nurse |
| Companion (family / friend / carer) | No login. Choose **"I am with the patient"** | Same as the patient, worded for the person helping |
| Nurse entering for a patient alone | No login needed. Choose **"Nurse entering for the patient"** | Same intake, plus the option to turn AI text extraction off |
| Clinic staff (nurse / doctor) | **Staff Login** button on the welcome screen | Clinic queue, full clinical summary for each patient, Doctor PDF download |

### Demo staff accounts

| Username | Password | Display name |
|---|---|---|
| `nurse` | `nurse2026` | Nurse on duty |
| `doctor` | `doctor2026` | Duty clinician |

**Change these before using the kiosk anywhere real.** Accounts are set in `app/backend/.env`:

```env
STAFF_ACCOUNTS=nurse:YourStrongPassword:Nurse on duty,doctor:AnotherPassword:Dr. Name
AUTH_SECRET=<output of: python -c "import secrets; print(secrets.token_urlsafe(32))">
```

- Staff are logged out automatically after 10 minutes of inactivity on the kiosk. Login tokens expire after 8 hours (`TOKEN_TTL_MINUTES`).
- If `AUTH_SECRET` is empty, a new secret is generated at each start, so everyone is logged out when the server restarts.
- A patient's answers are cleared from the screen after 3 minutes of inactivity, so the next person never sees them.

### Addresses once running

| Address | What it is |
|---|---|
| `http://localhost:5173` | The kiosk (patients and staff) |
| `http://localhost:8000/health` | Backend health check |
| `http://localhost:8000/docs` | Interactive API documentation |

---

## Demonstrated Safety Performance

**66 automated tests, all passing** (`python -m unittest discover tests` from `app/backend`). Every case tried during the latest review, with before and after results, is listed in **[TEST_CASES.md](TEST_CASES.md)**.

Critical cases that used to be triaged **GREEN** and are now caught:

| Scenario | Before | Now |
|---|---|---|
| "I'm going to die" (with an apostrophe) | GREEN | RED (S1) |
| "I want to kill myself" / "i want to die" | GREEN | RED (S2) + self-harm guidance |
| "I can't breathe" | GREEN | RED (S3) |
| "no fever, chest pain since morning" | GREEN, chest pain missed | ORANGE (O8) |
| Severe back pain, dizziness, or nausea | GREEN | ORANGE |
| Pregnant + bleeding | GREEN | RED (RF1) |
| Ratings outside 0–3 or unknown symptoms | accepted silently | rejected (422) |

| Suite | Tests | Covers |
|---|---|---|
| `test_triage_safety.py` | 8 | Original escalation scenarios (distress, diabetes, pregnancy, elderly, cardiac, clarification) |
| `test_safety_regressions.py` | 24 | Every gap found in review: critical language, negation scope, severity words, 0–3 scale sweeps, pregnancy |
| `test_api.py` | 13 | Login, protected endpoints, PDF from stored session, path traversal, offline model fallback |
| `test_speech.py` | 9 | Speech-to-text decoding, resampling, silence and hallucination guards, error codes |
| `test_nlp_extractor.py` | 5 | Extraction, negation, synonyms, merge, confidence |
| `test_triage_logging.py` | 3 | Session logging, 404, urgency-sorted queue |
| `test_advice_engine.py` | 2 | GREEN guidance, RED escalation language |
| `test_hf_extractor.py` | 2 | Entity normalization, HF output mapping |

---

## What the System Does

1. The welcome screen asks **who is filling in the form**: the patient, a companion, or a nurse. Wording adapts ("Your name" / "Patient's name").
2. The person enters the patient profile and describes the problem, by typing or by **speaking into the microphone**.
3. Each symptom is rated with large **None / Mild / Moderate / Severe** buttons (0–3 scale).
4. The backend reads the complaint text. It detects symptoms, respects negation within each clause ("no fever, chest pain" keeps chest pain), and raises the rating from severity words ("severe chest pain" counts as 3).
5. An optional Hugging Face biomedical NER model adds entity detection. If it's offline or missing, triage carries on without it.
6. Manual and extracted scores are merged conservatively (highest wins).
7. Auditable JSON rules in `rules-and-data/rules.json` decide the base level.
8. Risk factors escalate urgency: older adults, pregnancy (bleeding, abdominal pain), diabetes, heart problems.
9. **Critical language forces RED** regardless of ratings: dying (S1), self-harm (S2), breathing emergency (S3), collapse or seizure (S4).
10. Vague or low-confidence complaints trigger short yes/no safety questions.
11. The **patient view** shows the colour, plain next steps, advice, and a session number to show the nurse.
12. **Staff** log in to see the queue (RED, then ORANGE, then GREEN, newest first), open the full clinical summary, and download the Doctor PDF.

---

## Virtual Nurse: Voice, Lip-Sync and Speech Input

Everything is designed to run on modest kiosk hardware: no GPU, and no video decoding for the default avatar.

| Feature | How it works | Works offline? |
|---|---|---|
| **Animated nurse with lip-sync** | SVG face. Each spoken letter maps to a mouth shape (open, wide, round, closed, f/v), eased in one animation loop that runs only while speaking. | Yes |
| **Device voice** (default) | Browser `speechSynthesis`. Word-boundary events keep the mouth in sync. Installed (offline) voices are preferred. | Yes, with installed voices |
| **AI voice** | `POST /speech` runs `facebook/mms-tts-eng` on the kiosk server. The mouth follows the real audio loudness. Falls back to the device voice automatically. | Yes, after the first model download |
| **Captions** | The spoken text is shown with the current word highlighted. | Yes |
| **Read Aloud** | Button on the patient result reads the steps and advice. | Yes |
| **Speech-to-text** | Mic buttons on name, illness and complaint fields. Audio is recorded as WAV and sent to `POST /speech/transcribe` (Whisper-tiny on the kiosk server). Recording **stops by itself** about 1.5 s after the person stops talking. The browser's built-in recognition is only a backup. "My name is…" is trimmed to just the name. | Yes |
| **Settings** | Voice on/off, device vs AI voice, voice picker, speed 0.7x–1.4x, captions, speech-input mode, animated vs video avatar. Saved per kiosk. | — |

Notes:
- Browsers only allow sound after the first tap. Until then the nurse shows "Tap anywhere to hear the nurse".
- **Automatic** speech input uses the kiosk server first. Browser recognition is a backup only: Chrome and Edge send its audio online, and in testing Edge often returned an empty result. If nothing is recognised, the kiosk always says so and asks the person to try again.
- Whisper auto-detects the spoken language (e.g. Arabic, French, English). To force one, set `STT_LANGUAGE=en` (or `fr`, `ar`).
- Silence and non-speech noise return no text (Whisper invents text on silence otherwise). The kiosk then asks the person to try again.
- The **video avatar** is the old looping clip. It cannot lip-sync and is kept only as an option.

---

## Triage Levels and Rating Scale

| Level | Meaning | What the patient is told |
|---|---|---|
| `RED` | Urgent clinical review now | Go to the nurse now, sit or lie down, show your number |
| `ORANGE` | Prompt same-day review | Stay in the clinic, report if worse |
| `GREEN` | Lower immediate risk | Follow the advice, come back if worse |

Symptom ratings use **0 = none, 1 = mild, 2 = moderate, 3 = severe** everywhere (UI, API, rules, PDF). Any other value is rejected.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, `fetch` API client |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Auth | Stateless HMAC-signed bearer tokens (stdlib only) |
| NLP | Local clause-aware keyword/synonym extractor + optional `transformers` biomedical NER |
| Voice | Browser speech synthesis; server TTS `facebook/mms-tts-eng`; server STT `openai/whisper-tiny` |
| Storage | SQLite |
| PDF | ReportLab (rendered in memory) |
| Tests | Python `unittest` + FastAPI `TestClient` |

---

## Project Structure

```text
rural-triage-kiosk/
├── app/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── advice/       # Advice catalog (JSON) and guidance assembly
│   │   │   ├── api/          # Routes: auth, triage, pdf, speech (TTS + STT)
│   │   │   ├── nlp/          # Local symptom extractor and HF biomedical NER wrapper
│   │   │   ├── pdf/          # In-memory PDF report generation
│   │   │   ├── storage/      # SQLite session persistence
│   │   │   ├── triage/       # Schemas, rules loader, engine, critical-language safety
│   │   │   ├── auth.py       # Staff login tokens
│   │   │   ├── config.py     # Settings from environment / .env
│   │   │   └── main.py
│   │   ├── tests/            # 66 tests (see table above)
│   │   ├── .env.example
│   │   └── requirements.txt
│   └── frontend/
│       ├── public/assets/    # Optional video avatar clip
│       ├── src/
│       │   ├── api/          # API client + staff session handling
│       │   ├── components/   # AvatarAssistant, NurseAvatar (SVG), MicButton
│       │   ├── pages/        # Welcome, Intake, Result, Login, Queue
│       │   └── voice/        # Lip-sync, text-to-speech, speech-to-text, settings
│       ├── index.html
│       └── package.json
├── rules-and-data/
│   └── rules.json            # Auditable triage rules (RED / ORANGE)
├── TEST_CASES.md             # Every test case tried, before and after results
└── README.md
```

---

## Local Setup

Run backend and frontend in separate terminals. All commands start from the **repo root** (`rural-triage-kiosk/`).

> **If your `.venv` was created at a different path** (e.g. after moving the repo folder), delete it and recreate it. Python venvs store absolute paths and break when moved:
> ```powershell
> Remove-Item -Recurse -Force app\backend\.venv
> ```

### Backend

```powershell
cd app\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then edit STAFF_ACCOUNTS and AUTH_SECRET
uvicorn src.main:app --reload --port 8000
```

### Frontend

```powershell
cd app\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. To point the kiosk at a backend on another machine, create `app/frontend/.env.local` with `VITE_API_BASE=http://<server>:8000`, and add the kiosk's address to `CORS_ORIGINS` in the backend `.env`.

### First-run model downloads

The optional AI models download once from Hugging Face on first use, then work offline:

| Model | Used for | Size | Triggered by |
|---|---|---|---|
| `d4data/biomedical-ner-all` | Entity detection | ~255 MB | First triage with AI extraction on |
| `facebook/mms-tts-eng` | AI voice | ~140 MB | First AI-voice narration |
| `openai/whisper-tiny` | Server speech-to-text | ~150 MB | First server transcription |

To prepare a kiosk that will be offline, run each feature once while connected. If a model can't load, that feature is skipped (or falls back to the browser), and triage always keeps working.

---

## Configuration (`app/backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `STAFF_ACCOUNTS` | demo `nurse` / `doctor` accounts | `user:password[:Display name]`, comma separated |
| `AUTH_SECRET` | random per start | Signs login tokens |
| `TOKEN_TTL_MINUTES` | `480` | Staff login lifetime |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Frontend addresses allowed to call the API |
| `ENABLE_HF_NER` | `true` | Turn the biomedical NER layer off entirely |
| `HF_NER_MODEL_NAME` | `d4data/biomedical-ner-all` | NER model |
| `TTS_MODEL_NAME` | `facebook/mms-tts-eng` | AI voice (`facebook/mms-tts-fra`, `facebook/mms-tts-ara` for French/Arabic) |
| `STT_MODEL_NAME` | `openai/whisper-tiny` | Server speech-to-text |
| `STT_LANGUAGE` | empty (auto-detect) | Force a language, e.g. `en`, `fr`, `ar` |

---

## API Reference

| Method | Route | Login | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `POST` | `/auth/login` | — | `{username, password}` → bearer token |
| `GET` | `/auth/me` | Staff | Current staff user |
| `POST` | `/triage` | — | Submit intake; returns level, matched rules, extracted data, advice |
| `GET` | `/triage?limit=50` | Staff | Queue sorted by urgency |
| `GET` | `/triage/{session_id}` | Staff | One stored session |
| `GET` | `/pdf/{session_id}` | Staff | Doctor PDF, rebuilt from the stored session |
| `POST` | `/speech` | — | `{text}` → WAV narration (AI voice) |
| `POST` | `/speech/transcribe` | — | PCM WAV body → `{text}` (max 2 MB, about 1 minute) |

Staff routes need `Authorization: Bearer <token>`.

---

## Running Tests

From `app/backend` (venv active):

```powershell
python -m unittest discover tests -v
```

Tests use throwaway databases in a temp folder and never touch `outputs/`. They don't need internet: model loading is mocked where it matters.

---

## Changes in This Update (October 2026)

Fixes are listed in the order they were made: 🔴 safety first, then 🟠 reliability and security, then 🟢 polish, then the voice features. Full before/after evidence is in [TEST_CASES.md](TEST_CASES.md).

### 🔴 Safety fixes
- **Critical language detection rewritten** (`src/triage/safety.py`). Apostrophes are normalized (`I'm` / `I’m` / `Im`), and new categories were added: self-harm (S2, with "do not leave the patient alone" advice), breathing emergency (S3), collapse/seizure (S4, which respects negation such as "no seizures").
- **Negation scoped to the clause.** "no fever, chest pain" and "not eating, headache" no longer hide the second symptom. Every mention is checked, not just the first. Contractions like "don't" now count as negation.
- **Severity words** in the complaint set the rating ("mild" = 1, "bad" = 2, "severe" / "crushing" / "heavy" = 3). "can't breathe" is extracted as severe breathlessness.
- **One 0–3 rating scale everywhere.** The UI used to allow 0–5 and some rules matched only `== 2`, so severe back pain scored GREEN. Rules now use `>= 2`, and the new rule **O7** keeps any severe symptom at least ORANGE.
- **New rule O8:** any chest pain or breathing difficulty is at least ORANGE. *This is a conservative choice that a clinician should review.*
- **Pregnancy:** any bleeding (RF1) or abdominal pain (RF8 / RF9) now escalates.
- **Input validation:** ratings 0–3 only, unknown symptom keys rejected, fixed values for age group / sex / entered-by.

### 🟠 Reliability and security
- **Staff login** for the queue, session detail and PDF, which used to be open to anyone on the network.
- **PDF route** is now `GET /pdf/{session_id}`. The session ID is validated (this closes a path-traversal bug), the report is rebuilt from the stored session instead of trusting client data, and it is rendered in memory so no patient files pile up on disk.
- **Offline-safe models:** if the NER or TTS model can't download or load, triage still works (it used to return a 500 error).
- **`.env` is actually loaded now.** It was documented before but never read.
- **SQLite connections are closed.** One leaked per request before.
- **Tests** use temp databases. 51 leftover `test_*.db` files were removed.

### 🟢 Polish and kiosk flow
- Patient-first welcome screen (patient / companion / nurse), stored as `entered_by` and shown in the queue and PDF.
- Plain-language symptom names, large severity buttons, pregnancy questions hidden where they don't apply, empty form blocked.
- Separate patient result view (colour, next steps, number for the nurse). Clinical detail is shown only to logged-in staff opening a case from the queue.
- Idle reset for patient data (3 min) and staff logout (10 min).
- FastAPI `lifespan` instead of the deprecated `on_event`; rules and advice files cached until changed on disk; API address configurable with `VITE_API_BASE`; README corrected (the client uses `fetch`, not Axios).

### 🗣️ Virtual nurse and speech
- New lightweight SVG nurse with lip-sync, captions with word highlighting, Read Aloud, and a voice settings panel.
- **The AI voice now works.** The old default model `Vedika35/Vedika_text_to_speech` uses an architecture `transformers` 4.x can't load, so it always failed. The default is now `facebook/mms-tts-eng`.
- **Speech-to-text** on intake fields: offline Whisper-tiny on the kiosk server with auto-stop on silence, browser recognition as backup.
- **Fix:** speaking into the name field gave nothing in Edge. Its built-in recognizer returned an empty result and the kiosk failed silently. Automatic mode now uses the server first, keeps any words heard live, and always shows a message if nothing was caught.

---

## Known Limitations

- Rules and escalation thresholds (especially new rule O8) are engineering choices and need **clinical validation** before real use.
- Demo staff passwords are public in this README. Always set your own in `.env`.
- Text extraction and critical-language detection are **English-only**. Speech-to-text can transcribe other languages, but the triage rules won't understand them yet.
- Staff accounts are configured in `.env` (no admin screen or password hashing). This is fine for one kiosk, but not for multi-site use.
- Lip-sync is approximate (letter-based), not phoneme-accurate.

---

## Runtime Artifacts

The SQLite database is written to `app/backend/outputs/` and excluded from version control. PDFs are no longer saved to disk.

---

## GitHub Remote

```text
origin https://github.com/mahatrabelsi1/rural-triage-kiosk.git
```

If tracked cache files ever appear again, remove them from the Git index with:

```bash
git rm -r --cached app/backend/src/__pycache__ app/backend/tests/__pycache__
```
