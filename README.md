# Captain Thermo ⚓

An AI learning companion for **MS1016 Thermodynamics** (NTU, Prof Leonard Ng), built on the Claude API.

## What it does

Three tools in one web app, all grounded in your actual course materials (lecture notes L0–L7, tutorial solutions 1–8, tutorial problem sheets):

| Tool | What it does | Why it helps students learn more |
|---|---|---|
| **Socratic Tutor** | Chat interface that refuses to give final answers upfront — asks guiding questions, requests the student identify the relevant law, escalates hints gradually. | Forces *active* problem solving instead of copy-paste lookup. |
| **Practice Generator** | Serves problems in the style of your tutorials for any topic/difficulty, with worked solutions and common misconceptions — drawn from a pre-generated, reviewable bank. | Infinite practice beyond the 8 tutorial sheets; misconception callouts reinforce conceptual anchors. |
| **Solution Grader** | Student submits a problem + their working as **typed text, photos of handwritten pages, or both** (up to 8 images). Grader reads the handwriting, identifies *where* the reasoning went wrong (conceptual / setup / algebra / units) and gives targeted feedback. | Diagnostic feedback teaches the student *why* they're wrong — the part textbooks skip. Handwriting support means no LaTeX tax on pen-and-paper work. |
| **Flashcards** | Auto-generates 10 flashcards per topic covering definitions, key equations, applications, and pitfalls. Click to flip. | Spaced-repetition practice; works on phones. |

## Architecture

> Diagrams: [`docs/architecture.md`](docs/architecture.md) — request flow, cost structure, build pipeline.

- **Backend**: FastAPI (Python 3.12) + Anthropic Python SDK. Course corpus (~292 KB, ~99K tokens) is supplied as a prompt-cached system block — every request after the first costs ~10% of uncached tokens for that portion.
- **Frontend**: Single static page (Tailwind via CDN, MathJax for LaTeX, `marked` for markdown). No build step.
- **Models**: per-endpoint model selection via env vars.
  - `ANTHROPIC_MODEL_DEFAULT` — tutor / practice (default `claude-sonnet-4-6`, fast + cheap)
  - `ANTHROPIC_MODEL_GRADER` — grader (default `claude-opus-5`, best reasoning for diagnosing errors)
  - `ANTHROPIC_MODEL_FLASHCARDS` — flashcards (default `claude-haiku-4-5`; the least reasoning-sensitive tool, ~3× cheaper)
- **Access control**: optional shared passcode via `APP_PASSCODE`. Frontend prompts once, caches in `localStorage`, sends as `X-Passcode` header.
- **Rate limiting**: sliding window counted **per student**, not per IP. The frontend generates a random client id once and keeps it in `localStorage`, sending it as `X-Client-Id`; limits are 30/min and 40/day against that. A much higher per-IP ceiling (`IP_RATE_LIMIT_*`) remains as an abuse backstop.

  > Why not per IP: campus wifi NATs an entire cohort behind a handful of public addresses, so an IP-keyed limit treats a whole tutorial group as one user — thirty students making one request each would 429 the thirty-first and drain the shared daily quota in an afternoon.
  >
  > A client id is trivially reset by clearing `localStorage`, so this is a *fairness* mechanism, not a security boundary. `APP_PASSCODE` is the actual gate.

  In-memory — fine for a single instance; use Redis for multi-instance.
- **Structured outputs** on Practice / Grade / Flashcards endpoints — guarantees parseable JSON.
- **Streaming** on the Socratic Tutor endpoint for a responsive chat feel.

```
captain_thermo/
├── backend/
│   ├── app.py          FastAPI routes + Claude API calls
│   ├── corpus.py       Loads & concatenates course_content/*.txt
│   ├── bank.py         Serves the pre-generated practice/flashcard bank
│   ├── prompts.py      Role-specific system prompts (4 tools)
│   └── requirements.txt
├── frontend/
│   ├── index.html      Tabbed single-page UI
│   └── app.js          Vanilla JS, calls /api/*
├── course_content/     Extracted text from lectures + tutorials
│   └── generated/      Pre-built problem bank + flashcard decks (committed)
├── scripts/build_bank.py   Rebuilds the bank via the Batch API
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
   - `APP_PASSCODE` — a shared secret of your choosing; students enter it once on first visit.
     Don't reuse an example from any doc, and don't commit the real value — it lives only in
     the Render dashboard (`sync: false` in `render.yaml`) and your gitignored local `.env`.
5. Wait ~3 min for build. You'll get a URL like `https://captain-thermo.onrender.com`. Share the URL + passcode with students.
6. Run the smoke test against the deployed URL to confirm everything works: `python smoke_test.py --url https://... --passcode ...`.

> The Starter plan (~$7/mo) keeps the app always-on. The free tier works too but sleeps after inactivity (~30s cold start).

### Alternative: Fly.io, Railway, Google Cloud Run
Any platform that runs a Docker container works. The `Dockerfile` listens on `$PORT`.

## Cost notes

**Cache hit rate is the dominant cost variable — not model choice.** A miss re-writes the whole corpus; a hit costs a tenth of that. All figures below are *measured*, not estimated (`POST /api/prewarm` reports the real prefix sizes).

| Endpoint | Model | Cached prefix | Cache **hit** | Cache **miss** |
|---|---|---:|---:|---:|
| Tutor | `claude-sonnet-4-6` | 99.1K tok | ~$0.043 | ~$0.59 |
| Grader | `claude-opus-5` | 127.7K tok | ~$0.092 | ~$1.28 |
| Practice | *served from bank* | — | **$0** | — |
| Flashcards | *served from bank* | — | **$0** | — |

Practice and flashcards cost nothing at request time (see [the bank](#the-pre-generated-bank)); only the tutor and grader hit the API.

A miss costs **10–13×** a hit, so the whole cost strategy is "stay warm":

- **`CACHE_TTL=1h`** (default). A 1h write costs 2× base vs 1.25× for 5m, but survives the gaps that make usage bursty. It pays off from the 2nd request in an hour onward; below that, `5m` is marginally cheaper.
- **Pre-warming.** `PREWARM_ON_STARTUP` warms the live endpoint shapes at boot — just tutor and grader once the bank is populated. The interval loop (`PREWARM_INTERVAL_MIN`) re-warms only models used within `PREWARM_IDLE_AFTER_MIN`, so an idle deployment costs nothing — a blind timer would burn tens of dollars a day doing nothing. Warming a *live* shape is a cache read (~$0.06), not a write.
- **Cron the warm-up.** `POST /api/prewarm` (passcode-protected) about 10 min before a tutorial slot so the first student doesn't eat the miss.

> The corpus is **~99K tokens** (~292 KB), not the ~70K quoted in earlier revisions. Note also that Opus 5 tokenizes the same corpus to 127.7K — a different tokenizer, ~28% more tokens — which is why the grader costs more than the price-per-token ratio alone suggests.

Verify caching is working via `GET /api/health` → `cache`. If `hits` stays 0 while `misses` climbs, something volatile is invalidating the prefix.

Knobs:
- **Cheaper grader**: `ANTHROPIC_MODEL_GRADER=claude-sonnet-4-6` (~$0.045/hit). Quality drops noticeably on diagnosing *why* a student is wrong — this is the endpoint most worth paying for.
- **Best quality**: `ANTHROPIC_MODEL_DEFAULT=claude-opus-5` for all endpoints.
- **Don't** switch to `claude-sonnet-5` expecting savings: its tokenizer produces ~30% more tokens, so at list price it costs *more* than Sonnet 4.6 for identical text.

`RATE_LIMIT_PER_MIN` / `RATE_LIMIT_PER_DAY` (30/min, 40/day) cap each student individually — they key on the per-browser client id, so a shared campus NAT no longer collapses the cohort into one quota.

> **These are fairness limits, not a budget control.** 170 students × 40/day is still a theoretical ~$610/day. The only real ceiling is an org-level spend limit in the [Anthropic Console](https://console.anthropic.com) (Billing → Limits) — set one before sharing the URL widely.

## Analytics and education research

Every request writes one pseudonymous row to a SQLite event log (`backend/analytics.py`). Two surfaces on top of it:

| | |
|---|---|
| `/dashboard.html` | Charts and tables — enter the access code. Print-friendly for sharing with colleagues. |
| `GET /api/admin/export.csv` | Full event export, one row per request, for R / Python / SPSS. |
| `GET /api/admin/stats` | The same aggregates as JSON. |

### What makes this worth analysing

The grader already emits structured JSON, so asking it for `topic` and `concept_tested` costs **nothing extra** — and that turns a usage log into teaching signal. Instead of *"340 gradings this term"* you get:

> *L4 · Clausius–Clapeyron · 14 submissions · mean score 5.5 — the lowest on the course.*

Questions the schema answers directly:

- **Misconception cartography** — `error_type` × `topic` × `concept`, ranked by frequency and by mean score. Which lectures produce conceptual errors versus algebra slips.
- **Adoption and retention** — distinct students per week, and how many distinct days each student returns.
- **Temporal patterns** — hour of day, day of week, daily volume against tutorial deadlines.
- **Tool preference** — do students choose being asked (tutor) or being told (grader)?
- **Cost** — spend per tool, per day, per student.

### Privacy

Metadata only. **No student work, submissions, photos, or feedback text is stored** — inspect the `CREATE TABLE` in `analytics.py`; there is no column for any of it. Client ids are HMAC'd with `ANALYTICS_SALT` before storage, so rows link into a per-student sequence without identifying anyone.

> ⚠️ **Before the term starts.** Publishing on student data means human-subjects research: get NTU IRB/ethics review and student notice in place first — consent cannot usually be retro-fitted to data already collected. A notice is in the app footer; check it satisfies your ethics board. Note also that `ANALYTICS_SALT` must be **set and stable** — leave it unset and pseudonyms regenerate on every restart, which silently breaks retention and improvement analysis.

Storage is a 1 GB Render disk at `/var/data` (see `render.yaml`). The container filesystem is wiped on every deploy, so without the disk a term of data would vanish. Attaching a disk pins the service to one instance — fine here, but it rules out horizontal scaling without moving to Postgres.

## The pre-generated bank

Practice problems and flashcards are **not** generated per request. They're built once by `scripts/build_bank.py` via the Batch API (50% off) and committed to `course_content/generated/`, so they ship inside the container and survive deploys — Render has no persistent disk.

```bash
python scripts/build_bank.py --direct             # ordinary API calls, ~15 min
python scripts/build_bank.py                      # Batch API, 50% off, queue-dependent
python scripts/build_bank.py --resume BATCH_ID    # collect an earlier batch
python scripts/build_bank.py --per-combo 15       # more variety per topic
```

`--direct` costs about 2× what batch does (~$19 vs ~$10) but finishes in minutes. Batch runs on Anthropic's queue and can sit for hours — and every hour spent waiting is an hour the app keeps generating live at the higher per-request rate, which erases the saving. If a batch hasn't started after ~30 minutes, cancel it and use `--direct`.

Why this beats generating live:

- **Cost.** Fifty students asking for an L2 deck used to be fifty near-identical API calls, each re-reading the ~99K-token corpus. It also drops two of the four prompt-cache prefixes the app keeps warm — roughly a third off every cold round.
- **Quality.** Every practice problem now passes through a file you can read before a student sees it. Live generation never gave you that.

Rebuild it whenever the corpus changes materially. `USE_BANK=false` forces live generation, and any topic missing from the bank falls back to live automatically — a partial bank is safe.

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
