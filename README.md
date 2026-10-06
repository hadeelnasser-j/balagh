# BALAGH Backend (FastAPI)

Backend for the existing BALAGH frontend (`../frontend`). It takes an uploaded video through audio extraction, transcription, Quran/Hadith detection, source verification, translation, human review, TTS dubbing and final rendering.

## Quick start (Windows)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

1. **FFmpeg ≥ 5** must be on `PATH` (or set `FFMPEG_PATH` / `FFPROBE_PATH`).
2. **Supabase:** run `supabase/migrations/001_balagh_schema.sql` in the SQL editor once.
3. **Sources DB:** put `balagh_sources.sqlite3` in `backend/data/`. Check how it is read with:
   `python -m scripts.inspect_sources_db` (add `"اهدنا الصراط المستقيم"` to try a search).
4. Frontend: `frontend/.env.local` already points to `VITE_API_BASE_URL=http://localhost:8000`.

Offline development without Supabase: `DATA_BACKEND=memory` (data is lost on restart).

Tests: `pytest` (the service tests use real FFmpeg and fake AI providers; no API keys needed).

Live validation (real Supabase + AI providers, full workflow over HTTP):
`python -m scripts.validate_backend` writes `validation_report.md`. Run `supabase/verify_schema.sql`
in the Supabase SQL editor to check tables, RLS and the Quran constraint.

## Architecture

```
app/
  main.py                 FastAPI app, CORS, Arabic error responses, lifespan
  config.py               Settings (env + backend/.env)
  routers/                HTTP layer, one file per area (matches frontend/src/services/api.ts)
  schemas/                Pydantic request/response models (field names = frontend types)
  models/                 Enums (content types, job statuses…) and table names
  repositories/           Supabase + in-memory data repos; LocalSourcesRepository (SQLite)
  services/
    arabic.py             Arabic normalization (Uthmani ↔ standard spelling)
    content_detection.py  quran / hadith / general / uncertain rules
    verification.py       source matches, recovery, human source review
    translation.py        per-content-type translation rules
    review.py             edit / approve / reject
    meaning_locks.py      Islamic-term consistency checks
    dubbing.py            readiness, TTS generation, audio review, timing
    rendering.py          final video mix
    srt.py                subtitles with attribution
    providers/            OpenAI, Gemini (and Fake for tests)
  workers/                background job runner + job bodies
supabase/migrations/      Postgres schema
scripts/                  sources DB helpers
tests/
```

## Content rules (enforced in code)

| Type | Detection | Translation | Dubbing |
|---|---|---|---|
| **quran** | local match ≥ 0.92 | QuranEnc from SQLite **only**; never AI, never editable | **never**: original recitation kept |
| **hadith** | local match ≥ 0.85 | HadeethEnc if the segment is the whole hadith; otherwise an AI draft constrained by the verified text | after human approval |
| **general** | no religious match | AI (`openai_general`) | after human approval |
| **uncertain** | Quran score 0.85–0.92 (no reference attached), a substantial Quran/Hadith quote mixed into speech, a Quran+Hadith conflict, or "قال الله تعالى" without a match | none if Quran is suspected; otherwise an unverified AI draft | **blocked** until a reviewer approves it, then TTS (or original audio if Quran is suspected) |

A source reference (and a `source_matches` row) is attached **only** at or above the threshold: Quran 0.92, Hadith 0.85. Near-misses (e.g. 0.70–0.85) are treated as general speech. Ayahs that are everyday expressions ("الحمد لله رب العالمين", "إنا لله وإنا إليه راجعون") count as formulas when they appear inside longer speech. Very short ayahs ("ملك الناس") only match when they make up the whole segment.

Quran protection is layered: detection → translation service refuses AI → TTS service refuses Quran → renderer refuses → Postgres `CHECK (content_type <> 'quran' or dubbed_audio_path is null)`.

Approval sets `review_status=approved, translation_verified=true, ready_for_dubbing=true, needs_human_review=false`.

**Approved audio is final too.** Timing is advisory: an approved clip longer than its slot is sped up (≤ `APPROVED_OVERFLOW_MAX_TEMPO`), plays in full, and is reported as a warning (`warning_reasons`, report check severity `warning`). It is only ever cut where a Quran / original-audio segment begins. Rendering hard-blocks only on missing or unreadable audio files (`audio_file_missing`, `audio_corrupted`), plus the human review gates.

**The reviewer's approval is final.** An approved uncertain segment is resolved: it never blocks dubbing or the render again until the approval is revoked (reject, edit or re-translate). Each segment's `audio_mode` (`tts` / `original` / `blocked`, returned on every segment) is the single source of truth for dubbing and rendering. Approved segments flagged as possible Quran (`quran_suspected`) stay `original`: they are resolved but never synthesized. `verify-sources` never overturns an approved segment.

**Resolving an uncertain segment:**
- Approve a source match or recovered source → reclassified as quran or hadith and re-translated.
- Or `PATCH /api/segments/{id}` with `{"content_type": "general", "edited_translation": "..."}`. The current UI has no control for this yet.

## Job status contract (polled by the frontend)

| Endpoint | Statuses | Final |
|---|---|---|
| `POST …/upload`, `…/extract-audio` | uploaded → extracting_audio | `audio_extracted` |
| `POST …/transcribe` | transcribing → detecting_content → verifying_sources → translating | `awaiting_review` |
| `POST …/translate` | translating | `awaiting_review` |
| `POST …/generate-dubbing` | generating_audio | `completed` |
| `POST …/render-dubbed-video` | rendering_video | `completed` |

Any job can end in `failed`, with `error_message` in Arabic. Starting a job of a type that is already running returns the running job; starting a different job while one runs returns 409.

## Endpoints

General: `GET /`, `GET /api/health`, `GET /api/jobs/{job_id}`, `GET /api/pipeline/sources-status`

Projects: `POST /api/projects`, `GET /api/projects/{id}`, `POST …/upload`, `POST …/extract-audio`, `POST …/transcribe`, `POST …/translate`, `GET …/segments?page&page_size`, `GET …/review-summary`, `GET …/pipeline-status`

Segments: `GET|PATCH /api/segments/{id}`, `POST …/translate`, `POST …/approve`, `POST …/reject`, `GET …/source-matches`, `POST …/source-matches/{mid}/approve|reject`, `GET …/meaning-locks`, `PATCH /api/meaning-locks/{id}`

Sources: `POST …/verify-sources`, `GET …/source-summary`, `POST …/dubbing-check`, `POST …/recover-sources`, `GET …/recovered-sources`, `POST …/recovered-sources/{rid}/review`

Subtitles: `POST …/generate-srt?mode=draft|final`, `GET …/srt`

Dubbing & reports: `GET …/dubbing-readiness`, `GET …/dubbing-status`, `GET …/dubbing-report`, `GET …/integrity-report`, `POST …/generate-dubbing?force=`, `POST …/segments/{sid}/generate-audio`, `GET …/segments/{sid}/audio`, `POST …/segments/{sid}/approve-audio`, `POST …/segments/{sid}/reject-audio`, `POST …/approve-all-audio`, `POST …/render-dubbed-video`, `GET …/dubbed-audio`, `GET …/dubbed-video`

Interactive docs: http://localhost:8000/docs

## Troubleshooting

- **`ConnectTimeout` / `WinError 10060` to Supabase:** the API still starts; `/api/health` reports `supabase: unavailable`. Run `python -m scripts.check_supabase`. It checks the URL format, DNS, TCP and HTTPS, and whether the key and tables are accepted, then says which step fails (wrong URL, paused project, firewall/VPN, wrong key, missing migration).

## Notes

- **Transcription (OpenAI):** only `whisper-1` returns segment timestamps. The backend gets the timing from whisper-1, then re-transcribes each segment with `OPENAI_TRANSCRIPTION_MODEL` (e.g. `gpt-4o-transcribe`) for accuracy. Set `OPENAI_REFINE_SEGMENTS=false` to skip that second pass.
- **Gemini transcription** timestamps are model-estimated and less precise than Whisper.
- **Health check:** the frontend blocks processing unless `openai_configured` is true, even when Gemini is the selected provider.
- **Sources DB columns** are detected automatically (`python -m scripts.inspect_sources_db` shows the mapping). With the current `balagh_sources.sqlite3`: Quran matching and display use `aya_text_emlaey` (`aya_text` is font-encoded glyph codes, so it is never shown), the translation comes from `translation` with `[n]` footnote markers removed, and surah names come from a built-in table. Hadiths use `hadith_text_ar` / `hadith_text_en` / `grade_en` / `takhrij_en` / `link_en`. Coverage is measured against the «quoted text» without the narrator chain.
- **Data access:** the source DB is read with Python's built-in `sqlite3` (read-only, loaded once into an in-memory index), so SQLAlchemy is not needed.
# balagh
