# Captain Thermo ⚓

An AI learning companion for **MS1016 Thermodynamics** (NTU, Prof Leonard Ng), built on the Claude API.

## What it does

Three tools in one web app, all grounded in your actual course materials (lecture notes L0–L7, tutorial solutions 1–8, tutorial problem sheets):

| Tool | What it does | Why it helps students learn more |
|---|---|---|
| **Socratic Tutor** | Chat interface that refuses to give final answers upfront — asks guiding questions, requests the student identify the relevant law, escalates hints gradually. | Forces *active* problem solving instead of copy-paste lookup. |
| **Practice Generator** | Generates fresh problems in the style of your tutorials for any topic/difficulty, with worked solutions and a list of common misconceptions. | Infinite practice beyond the 8 tutorial sheets; misconception callouts reinforce conceptual anchors. |
| **Solution Grader** | Student submits a problem + their working as **typed text, photos of handwritten pages, or both** (up to 8 images). Grader reads the handwriting, identifies *where* the reasoning went wrong (conceptual / setup / algebra / units) and gives targeted feedback. | Diagnostic feedback teaches the student *why* they're wrong — the part textbooks skip. Handwriting support means no LaTeX tax on pen-and-paper work. |
| **Flashcards** | Auto-generates 10 flashcards per topic covering definitions, key equations, applications, and pitfalls. Click to flip. | Spaced-repetition practice; works on phones. |

## Architecture

- **Backend**: FastAPI (Python 3.12) + Anthropic Python SDK. Course corpus (~280KB, ~70K tokens) is supplied as a prompt-cached system block — every request after the first costs ~10% of uncached tokens for that portion.
- **Frontend**: Single static page (Tailwind via CDN, MathJax for LaTeX, `marked` for markdown). No build step.
- **Models**: per-endpoint model selection via env vars.
  - `ANTHROPIC_MODEL_DEFAULT` — tutor / practice (default `claude-sonnet-4-6`, fast + cheap)
  - `ANTHROPIC_MODEL_GRADER` — grader (default `claude-opus-5`, best reasoning for diagnosing errors)
  - `ANTHROPIC_MODEL_FLASHCARDS` — flashcards (default `claude-haiku-4-5`; the least reasoning-sensitive tool, ~3× cheaper)
- **Access control**: optional shared passcode via `APP_PASSCODE`. Frontend prompts once, caches in `localStorage`, sends as `X-Passcode` header.
- **Rate limiting**: per-IP sliding window (30/min, 300/day by default; tunable via env). In-memory — fine for a single instance; use Redis for multi-instance.
- **Structured outputs** on Practice / Grade / Flashcards endpoints — guarantees parseable JSON.
- **Streaming** on the Socratic Tutor endpoint for a responsive chat feel.

```
captain_thermo/
├── backend/
│   ├── app.py          FastAPI routes + Claude API calls
│   ├── corpus.py       Loads & concatenates course_content/*.txt
│   ├── prompts.py      Role-specific system prompts (4 tools)
│   └── requirements.txt
├── frontend/
│   ├── index.html      Tabbed single-page UI
│   └── app.js          Vanilla JS, calls /api/*
├── course_content/     Extracted text from lectures + tutorials
├── Dockerfile
├── render.yaml         One-click deploy config for Render.com
└── .env.example
```

## Run locally

```bash
cd captain_thermo
cp .env.example .env      # then fill in ANTHROPIC_API_KEY; optionally set APP_PASSCODE
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend && uvicorn app:app --reload --port 8000
```

Open http://localhost:8000.

## Smoke test (before deploying)

With the server running, in another terminal:

```bash
python smoke_test.py                                    # localhost
python smoke_test.py --passcode your-code               # if APP_PASSCODE is set
python smoke_test.py --url https://captain-thermo.onrender.com --passcode your-code
```

Prints PASS/FAIL for all 6 endpoints. Full pass ≈ 60–90 s (Opus on the grader is the slowest step).

## Deploy to Render (5 minutes)

1. Push this folder to a GitHub repo.
2. Sign in at [render.com](https://render.com), click **New → Blueprint**.
3. Point it at your repo. Render reads `render.yaml` and creates a `captain-thermo` web service.
4. In the service's **Environment** tab, set:
   - `ANTHROPIC_API_KEY` — your key from console.anthropic.com
   - `APP_PASSCODE` — any shared secret (e.g. `thermo2026`); students enter this once on first visit
5. Wait ~3 min for build. You'll get a URL like `https://captain-thermo.onrender.com`. Share the URL + passcode with students.
6. Run the smoke test against the deployed URL to confirm everything works: `python smoke_test.py --url https://... --passcode ...`.

> The Starter plan (~$7/mo) keeps the app always-on. The free tier works too but sleeps after inactivity (~30s cold start).

### Alternative: Fly.io, Railway, Google Cloud Run
Any platform that runs a Docker container works. The `Dockerfile` listens on `$PORT`.

## Cost notes

**Cache hit rate is the dominant cost variable — not model choice.** A miss re-writes the whole corpus; a hit costs a tenth of that. All figures below are *measured*, not estimated (`POST /api/prewarm` reports the real prefix sizes).

| Endpoint | Model | Cached prefix | Cache **hit** | Cache **miss** |
|---|---|---:|---:|---:|
| Tutor, Practice | `claude-sonnet-4-6` | 99.5K tok | ~$0.045 | ~$0.60 |
| Grader | `claude-opus-5` | 127.7K tok | ~$0.11 | ~$1.28 |
| Flashcards | `claude-haiku-4-5` | 99.4K tok | ~$0.018 | ~$0.20 |

A miss costs **10–13×** a hit, so the whole cost strategy is "stay warm":

- **`CACHE_TTL=1h`** (default). A 1h write costs 2× base vs 1.25× for 5m, but survives the gaps that make usage bursty. It pays off from the 2nd request in an hour onward; below that, `5m` is marginally cheaper.
- **Pre-warming.** `PREWARM_ON_STARTUP` warms all four endpoint shapes at boot. The interval loop (`PREWARM_INTERVAL_MIN`) re-warms only models used within `PREWARM_IDLE_AFTER_MIN`, so an idle deployment costs nothing — a blind timer over all four shapes would burn ~$58/day doing nothing. Warming a *live* shape is a cache read (~$0.06), not a write.
- **Cron the warm-up.** `POST /api/prewarm` (passcode-protected) about 10 min before a tutorial slot so the first student doesn't eat the miss.

> The corpus is **~99K tokens** (~292 KB), not the ~70K quoted in earlier revisions. Note also that Opus 5 tokenizes the same corpus to 127.7K — a different tokenizer, ~28% more tokens — which is why the grader costs more than the price-per-token ratio alone suggests.

Verify caching is working via `GET /api/health` → `cache`. If `hits` stays 0 while `misses` climbs, something volatile is invalidating the prefix.

Knobs:
- **Cheaper grader**: `ANTHROPIC_MODEL_GRADER=claude-sonnet-4-6` (~$0.045/hit). Quality drops noticeably on diagnosing *why* a student is wrong — this is the endpoint most worth paying for.
- **Best quality**: `ANTHROPIC_MODEL_DEFAULT=claude-opus-5` for all endpoints.
- **Don't** switch to `claude-sonnet-5` expecting savings: its tokenizer produces ~30% more tokens, so at list price it costs *more* than Sonnet 4.6 for identical text.

`RATE_LIMIT_PER_MIN` / `RATE_LIMIT_PER_DAY` cap any single student's usage. Note the limiter keys on IP, so students behind a shared campus NAT share one quota — raise the limits if that bites.

## Refreshing course content

If you update lecture notes or tutorial solutions:

```bash
cd "Classes/Thermo/2025-26 S1 - Claude code"
pdftotext -layout "Notes/Complete_thermo_notes.pdf" "captain_thermo/course_content/notes_complete.txt"
# repeat for any updated tutorial solution PDFs
```

Then rebuild / redeploy. The app concatenates all `course_content/*.txt` files at startup.

## Tuning the tutor

The Socratic behaviour is controlled by `backend/prompts.py::TUTOR_SYSTEM`. If you want the tutor to be more (or less) gating, edit that string — no code changes needed.

## Credits

Built with the Claude API. Course material © Prof Leonard Ng, NTU MSE.
