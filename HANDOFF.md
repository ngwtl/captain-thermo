# Handoff — Captain Thermo

Working notes for picking this up in a new session. Written 2026-08-05.
The README is the user-facing doc; this is the "what happened and what's left" doc.

---

## Current state

**Live and working.** `https://captain-thermo.onrender.com`, auto-deploys from `main`
on push (~90 s). Repo `github.com/ngwtl/captain-thermo` is **private**.

Four tools: Socratic tutor (streaming), practice generator, solution grader
(text + photos of handwriting), flashcards.

| | |
|---|---|
| Tutor / practice fallback | `claude-sonnet-4-6` |
| Grader | `claude-opus-5`, adaptive thinking, `effort: medium` |
| Flashcards fallback | `claude-haiku-4-5` |
| Practice + flashcards | served from a **pre-generated bank**, no API call |
| Corpus | ~99K tokens (~292 KB), prompt-cached at 1h TTL |
| Rate limits | 30/min, 120/day **per student**; 600/20000 per-IP backstop |
| Spend cap | $800/month, alert at $400 (set in Console) |

11 commits this session, `063b887`..`78b206f`. All pushed.

---

## ⚠️ Open items

### 1. The problem bank was never collected — highest priority

`scripts/build_bank.py` submitted batch **`msgbatch_01GsyL5qJ5XZ1kcDMnCdnV8T`**
(248 requests: 8 topics × 3 difficulties × 10 problems + 8 decks of 20 cards).
It sat `in_progress` with **zero** requests started for 30+ minutes and was never
collected before the session ended.

```bash
python scripts/build_bank.py --resume msgbatch_01GsyL5qJ5XZ1kcDMnCdnV8T
```

If it expired (batches expire at 24h) just re-run `python scripts/build_bank.py`.
If the Batch API is still backlogged, generating with regular API calls costs
~$19 instead of ~$10 — not worth waiting days for.

**Until the bank exists nothing is broken**, but none of the projected savings are
real: `USE_BANK` falls back to live generation and all four cache prefixes stay
warm. Confirm success with `/api/health` → `bank.live_endpoints` showing
`["chat","grade"]` instead of all four.

### 2. `ANALYTICS_SALT` is unset in Render

Dashboard shows a warning banner for this. Without it, pseudonyms regenerate on
every restart, so retention and improvement analysis are silently wrong.
Render → Environment → add any long random string (`openssl rand -hex 32`).
**Set once, never change** — changing it splits each student into two identities.

### 3. NTU ethics review before term

Publishing on the analytics is human-subjects research. Consent generally cannot
be retro-fitted to data already collected. A draft student notice is in the app
footer (`frontend/index.html`); the ethics board should approve the wording.

### 4. Test with real handwriting

The grader was verified against a *generated* sample (handwriting font, rotated,
blurred, unevenly lit) and did well — read the working, caught a missing `ln`,
cited L2 §2.4. But that is not real handwriting. One photo of an actual student
page before term would close this.

### 5. Not done, low value

Corpus trim (~5.5%), image cap (8 → 5), chat-history cap, seasonal `CACHE_TTL`.
Together ~2–5%. Deliberately skipped.

---

## Measured facts — don't re-derive these

Each cost real API calls to establish.

**Prompt cache partitions by `(model, schema)`, not by role prompt.**
Several role prompts sharing one model+schema read the same corpus entry and
write only their own few hundred tokens. But `output_config` forks the cache at
the root: a schema-carrying request shares nothing with a plain one, and two
different schemas share nothing with each other. The four endpoints are four
distinct pairs, so nothing shares. I predicted a second cache breakpoint would
merge them; **it doesn't**. Kept anyway (caches the role prompt; helps any future
endpoint added to an existing pair).

**Measured prefix sizes:** chat/Sonnet 99,063 · generate/Sonnet 99,486 ·
grade/Opus-5 127,743 · flashcards/Haiku 99,439. Opus 5 tokenizes the same corpus
~28% higher than Sonnet — different tokenizer.

**Per-action, cache-warm:** chat $0.043 · grade $0.087 · practice/flashcards $0
(bank). Cold cache round: ~$1.87 with the bank, ~$2.40 without.

**Grader effort is a latency lever, not a cost one.** high/medium/low returned
identical verdict, score and error type; cost fell only ~9% because the cached
corpus read is ~70% of per-action cost. Latency fell 16.0 s → 11.2 s. Hence
`medium`.

**Corpus composition:** consolidated notes 79,040 tok (80%), tutorial solutions
14,584 (15%), problem sheets 5,402 (5.5%). Solutions restate each problem
verbatim, so the problem sheets are redundant — but only ~5% of writes.

**Cache economics:** hit = 0.1× input price, 1h write = 2×, 5m write = 1.25×.
1h TTL pays off from the 2nd request in an hour. Verified: 851,462 tokens read,
0 written across 8 production requests.

**Cost projection, 170 students × 16 weeks:** ~$810 light / ~$1,580 moderate /
~$2,710 heavy, *with* the bank. Peak month ~$560 moderate. Out-of-term ~$7/mo.

---

## Gotchas hit this session

- **Render's filesystem is wiped on every deploy.** Analytics needs the 1 GB disk
  at `/var/data` (in `render.yaml`); the bank is committed to the repo for the
  same reason. Attaching a disk pins the service to one instance.
- **`max_tokens` caps thinking + response together.** The grader ran adaptive
  thinking under 4096 and could truncate JSON mid-object on a multi-page
  submission, surfacing as a 502. Now 8192.
- **The progress indicator rendered below the fold** on Grader and Practice, so
  students saw only a greyed button — the exact failure it existed to prevent.
  `scrollIntoView({block:"nearest"})` was not enough; it stops once the top edge
  appears. Uses `"center"` with a visibility check.
- **Rate limits keyed on IP** collapsed the whole cohort into one quota behind
  campus NAT. Now keyed on `X-Client-Id` from `localStorage`.
- **The README's example passcode became the real passcode**, in a then-public
  repo. Replaced with guidance, no literal.
- **CRLF line endings** made 25 files show as fully modified. `.gitattributes`
  with `* text=auto` fixed it.

---

## Operational reference

**Secrets — none are in the repo.** `ANTHROPIC_API_KEY` and `APP_PASSCODE` live in
the gitignored local `.env` and in the Render dashboard (`sync: false`).
`ANALYTICS_SALT` belongs in Render only. Git auth is an ed25519 SSH key in the
macOS keychain (`~/.ssh/id_ed25519`, no passphrase).

**Analytics:** `/dashboard.html` (passcode-gated, print-friendly),
`GET /api/admin/export.csv` (26 cols, one row per request),
`GET /api/admin/stats` (JSON + `collection` health block).
Metadata only — no student work, submissions, photos or feedback text is stored.
The grader classifies `topic` and `concept_tested` as part of its existing
structured output, at no extra cost; that is what makes the data teaching signal
rather than a hit counter.

**Useful commands**

```bash
# local run
cd backend && uvicorn app:app --reload --port 8000

# full endpoint check against production
python smoke_test.py --url https://captain-thermo.onrender.com --passcode <code>

# warm the caches before a tutorial slot (cron this)
curl -X POST https://captain-thermo.onrender.com/api/prewarm -H 'X-Passcode: <code>'

# rebuild the bank after a corpus change
python scripts/build_bank.py
```

**Verify a deploy landed:** `/api/health` reports models, `cache_ttl`,
`grader_effort`, cache hit/miss counters, and bank size.

---

## Things worth building next

- **Did the tool help?** The analytics can show a student's grade scores over
  time, but nothing links usage to course outcomes. Even a coarse join against
  final marks would turn usage reporting into an actual research result.
- **Do students retry after feedback?** The event log has the data (per-student
  sequence of gradings on the same concept); nothing surfaces it yet. This is the
  most interesting pedagogical question the schema can already answer.
- **Weekly digest** — email or Slack summary of the misconception table, so it
  informs teaching during the term rather than after it.
- **Bank quality review pass.** The point of pre-generating was that problems can
  be vetted. Nobody has read them yet.
