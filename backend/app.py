"""Captain Thermo — FastAPI backend for MS1016 student learning tools.

Four tools in one app:
  /api/chat            Socratic tutor (streaming)
  /api/generate        Practice problem generator (JSON)
  /api/grade           Student-work grader (JSON, adaptive thinking)
  /api/flashcards      Spaced-repetition deck generator (JSON)

Models:
  ANTHROPIC_MODEL_DEFAULT     tutor + practice (default: sonnet-4-6, cheap & fast)
  ANTHROPIC_MODEL_GRADER      grader (default: opus-5, best reasoning)
  ANTHROPIC_MODEL_FLASHCARDS  flashcards (default: haiku-4-5, ~3x cheaper)

Practice and flashcards are normally served from a pre-generated bank
(see bank.py) and make no API call at all; they fall back to live generation
when the bank has no entry.

Cost control:
  CACHE_TTL   corpus cache lifetime, "5m" or "1h" (default 1h).
              A cache miss re-writes the ~99K-token corpus at 1.25-2x input
              price; a hit costs 0.1x. Usage is bursty around tutorials, so
              the 1h TTL bridges the gaps that would otherwise be misses.
  USE_BANK    serve practice/flashcards from the bank (default true).
  GRADER_EFFORT  Opus 5 reasoning depth (default medium; see the constant).
  PREWARM_*   see _prewarm_loop. Warming is demand-gated: only models used
              recently are re-warmed, so idle periods cost nothing.

Access control:
  APP_PASSCODE    if set, clients must send X-Passcode header matching this value
  RATE_LIMIT_PER_MIN    per-student requests per minute on /api/* (default 30)
  RATE_LIMIT_PER_DAY    per-student requests per day on /api/* (default 40)
  IP_RATE_LIMIT_*       per-IP abuse backstop, deliberately much higher

Limits key on the X-Client-Id header, not the IP — see require_access.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import analytics
import bank
from corpus import CORPUS, TOPIC_INDEX
from prompts import (
    FLASHCARD_SYSTEM,
    GRADER_SYSTEM,
    PROBLEM_GENERATOR_SYSTEM,
    TUTOR_SYSTEM,
)

load_dotenv()

log = logging.getLogger("captain_thermo")

MODEL_DEFAULT = os.getenv("ANTHROPIC_MODEL_DEFAULT", "claude-sonnet-4-6")
MODEL_GRADER = os.getenv("ANTHROPIC_MODEL_GRADER", "claude-opus-5")
MODEL_FLASHCARDS = os.getenv("ANTHROPIC_MODEL_FLASHCARDS", "claude-haiku-4-5")
APP_PASSCODE = os.getenv("APP_PASSCODE", "").strip()
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "300"))
# Per-IP ceiling: an abuse backstop only. Must comfortably exceed a whole
# tutorial group behind one campus NAT address, or it recreates the very
# problem the per-client limits above are there to avoid.
IP_RATE_LIMIT_PER_MIN = int(os.getenv("IP_RATE_LIMIT_PER_MIN", "600"))
IP_RATE_LIMIT_PER_DAY = int(os.getenv("IP_RATE_LIMIT_PER_DAY", "20000"))

CACHE_TTL = os.getenv("CACHE_TTL", "1h").strip() or "1h"
# Serve practice problems and flashcards from the pre-generated bank. Set false
# to force live generation (useful when validating a corpus change before
# rebuilding the bank). Falls back to live automatically when the bank has no
# entry for a topic, so a partial bank is safe.
USE_BANK = os.getenv("USE_BANK", "true").lower() in ("1", "true", "yes")
# Grader reasoning depth. Measured on Opus 5: medium costs ~9% less than high
# and returns the same verdict/score/error-type, but runs ~30% faster (16.0s ->
# 13.1s). The win here is latency — the cached corpus read dominates cost, so
# effort barely moves the bill.
GRADER_EFFORT = os.getenv("GRADER_EFFORT", "medium").strip()
PREWARM_ON_STARTUP = os.getenv("PREWARM_ON_STARTUP", "true").lower() in ("1", "true", "yes")
PREWARM_INTERVAL_MIN = int(os.getenv("PREWARM_INTERVAL_MIN", "50"))
PREWARM_IDLE_AFTER_MIN = int(os.getenv("PREWARM_IDLE_AFTER_MIN", "90"))

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Distinct models in play. Caches are model-scoped, so each one is a separate
# cache prefix that has to be warmed independently.
ALL_MODELS = sorted({MODEL_DEFAULT, MODEL_GRADER, MODEL_FLASHCARDS})

client = anthropic.Anthropic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if PREWARM_ON_STARTUP:
        # Warm every endpoint shape once so the first student of the session
        # doesn't pay the cache-miss latency (and the write is one we'd owe
        # anyway on their request).
        await _prewarm_all()
    if PREWARM_INTERVAL_MIN > 0:
        task = asyncio.create_task(_prewarm_loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title="Captain Thermo", version="1.2", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- access control & rate limiting ----------

# In-memory sliding-window counters. Fine for a single-instance deploy.
# For multi-instance, swap for Redis or an external limiter.
# Keyed by client id (per student); the _ip_* pair is the abuse backstop.
_minute_hits: dict[str, list[float]] = defaultdict(list)
_day_hits: dict[str, list[float]] = defaultdict(list)
_ip_minute_hits: dict[str, list[float]] = defaultdict(list)
_ip_day_hits: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    # Render/Cloudflare put the real IP in X-Forwarded-For
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(hits: list[float], window_s: float, now: float) -> None:
    cutoff = now - window_s
    while hits and hits[0] < cutoff:
        hits.pop(0)


def _bump(bucket: dict[str, list[float]], key: str, window: float, limit: int,
          now: float, message: str) -> None:
    """Sliding-window check-and-record for one counter."""
    hits = bucket[key]
    _prune(hits, window, now)
    if len(hits) >= limit:
        raise HTTPException(429, message)
    hits.append(now)


def require_access(
    request: Request,
    x_passcode: str | None = Header(default=None),
    x_client_id: str | None = Header(default=None),
) -> str:
    """Dependency: check passcode (if configured) and rate limits.

    Limits are counted per *client id* — a random UUID the frontend generates
    once and keeps in localStorage — not per IP. Campus wifi NATs the whole
    cohort behind a few public addresses, so IP-keyed limits would let thirty
    students in a tutorial exhaust a 30/min quota between them and 429 the
    thirty-first, then burn the shared 300/day cap in an afternoon.

    A client id is trivially reset by clearing localStorage, so this is a
    fairness mechanism, not a security boundary — APP_PASSCODE is the actual
    gate. The per-IP ceiling below stays as an abuse backstop, set high enough
    that a legitimate lab full of students never reaches it.
    """
    if APP_PASSCODE and x_passcode != APP_PASSCODE:
        raise HTTPException(401, "Invalid or missing passcode")

    now = time.time()
    ip = _client_ip(request)
    # Fall back to IP when the header is absent (old cached frontend, curl).
    client = (x_client_id or "").strip()[:64] or f"ip:{ip}"

    _bump(_minute_hits, client, 60, RATE_LIMIT_PER_MIN, now,
          "Rate limit (per minute) exceeded — slow down.")
    _bump(_day_hits, client, 86400, RATE_LIMIT_PER_DAY, now,
          "Daily quota exceeded — try again tomorrow.")

    _bump(_ip_minute_hits, ip, 60, IP_RATE_LIMIT_PER_MIN, now,
          "This network is sending too many requests — try again shortly.")
    _bump(_ip_day_hits, ip, 86400, IP_RATE_LIMIT_PER_DAY, now,
          "This network has hit its daily quota.")

    return client


# ---------- helpers ----------


def _extract_json(resp) -> dict:
    """Pull JSON out of a Messages response, tolerating markdown fences and preambles.

    Structured outputs *should* return pure JSON in the first text block, but
    occasionally the model wraps it in ```json ... ``` or prepends a sentence.
    Try strict parse first; fall back to fence-stripping and brace-scanning.
    """
    # Check stop_reason before touching content: a safety refusal returns HTTP
    # 200 with empty or partial content, which would otherwise surface as a
    # confusing "non-JSON" error.
    if getattr(resp, "stop_reason", None) == "refusal":
        raise HTTPException(422, "The model declined this request. Try rephrasing.")
    if getattr(resp, "stop_reason", None) == "max_tokens":
        raise HTTPException(502, "Response was truncated — retry, or raise max_tokens.")

    text = next((b.text for b in resp.content if b.type == "text"), "").strip()
    if not text:
        raise HTTPException(502, "Model returned no text content")

    # Strip a ```json ... ``` or ``` ... ``` fence if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Last resort: find the first {...} or [...] block
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise HTTPException(502, f"Model returned non-JSON: {text[:160]}")


def _cache_control() -> dict:
    """Cache directive for the corpus block.

    The API defaults to a 5-minute TTL, which is too short for this workload:
    students arrive in bursts around tutorial deadlines and the corpus is
    ~70K tokens, so every gap over 5 min costs a full re-write. The 1h TTL
    doubles the write premium (1.25x -> 2x) but breaks even at 3 requests
    per hour, which any active session clears easily.
    """
    cc: dict = {"type": "ephemeral"}
    if CACHE_TTL != "5m":
        cc["ttl"] = CACHE_TTL
    return cc


def _api_error(e: anthropic.APIError) -> HTTPException:
    """Translate an Anthropic error into something a student can act on.

    `f"Anthropic error: {e}"` leaks internal detail and reads as a crash. Two
    cases genuinely reach students: the organisation's monthly spend cap being
    hit — which looks like a total outage unless it's named — and transient
    overload. Everything else is logged for you and shown as a generic retry.
    """
    etype = getattr(e, "type", None)
    status = getattr(e, "status_code", None)

    if etype == "billing_error" or status == 402:
        log.error("BILLING: spend cap or credit exhausted — %s", e)
        return HTTPException(
            503,
            "Captain Thermo has reached its monthly usage budget. "
            "Please let Prof Ng know — normal service resumes once it's topped up.",
        )
    if status == 429:
        return HTTPException(429, "Captain Thermo is busy right now — try again in a moment.")
    if status == 401 or status == 403:
        log.error("AUTH/PERMISSION problem talking to Anthropic: %s", e)
        return HTTPException(503, "Captain Thermo is misconfigured. Please let Prof Ng know.")
    if status and status >= 500:
        return HTTPException(503, "Captain Thermo is temporarily unavailable — try again shortly.")

    log.warning("Unclassified Anthropic error: %s", e)
    return HTTPException(502, "Something went wrong reaching Claude. Please try again.")


def _system_blocks(role_prompt: str) -> list[dict]:
    """Build a two-block system: [cached course corpus, role-specific instructions].

    Two breakpoints: end of corpus, end of role prompt.

    How the cache actually partitions here, measured against the live API:

      * Role prompt does NOT fork the cache. Several role prompts sharing one
        (model, schema) read the same corpus entry and write only their own
        few hundred tokens.
      * `output_config` DOES fork it, at the root. A request carrying a JSON
        schema shares nothing with one that doesn't, and two different schemas
        share nothing with each other.

    So entries partition by (model, schema), and the four endpoints are already
    four distinct pairs — chat/Sonnet-none, generate/Sonnet-PROBLEM,
    grade/Opus-GRADE, flashcards/Haiku-FLASHCARD. Nothing shares today, and
    ~$2.40 per cold round is the floor for a 99K corpus across four entries.

    The second breakpoint is therefore not a cost win at present; it caches the
    role prompt (worth ~0.1x on a few hundred tokens) and means any future
    endpoint added to an existing (model, schema) pair costs ~450 tokens to
    warm rather than ~99,000.

    Keeping the role prompt in `system` rather than folding it into the user
    turn preserves its authority — the tutor's refusal to hand over answers is
    the whole point of the tool.
    """
    return [
        {
            "type": "text",
            "text": (
                "You have access to the complete MS1016 Thermodynamics course "
                "materials below. Use these as the source of truth for notation, "
                "conventions, and equations.\n\n"
                "===== MS1016 COURSE CORPUS =====\n\n"
                + CORPUS
                + "\n\n===== END CORPUS ====="
            ),
            "cache_control": _cache_control(),
        },
        {"type": "text", "text": role_prompt, "cache_control": _cache_control()},
    ]


# ---------- cache accounting & pre-warming ----------

# Per-model counters so you can confirm the cache is actually being hit.
# Exposed on /api/health; if hits stay at 0 across repeated requests,
# something is invalidating the prefix.
def _new_stats() -> dict:
    return {"hits": 0, "misses": 0, "cache_read_tokens": 0, "cache_write_tokens": 0}


_cache_stats: dict[str, dict] = defaultdict(_new_stats)
_last_used: dict[str, float] = {}


def _mark_used(model: str) -> None:
    _last_used[model] = time.time()


def _record_usage(model: str, usage) -> None:
    if usage is None:
        return
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    written = getattr(usage, "cache_creation_input_tokens", 0) or 0
    s = _cache_stats[model]
    s["cache_read_tokens"] += read
    s["cache_write_tokens"] += written
    s["hits" if read else "misses"] += 1


def _warm_targets() -> list[tuple[str, str, str, dict | None]]:
    """(label, model, role_prompt, schema) for every endpoint shape.

    Measured behaviour: the corpus breakpoint IS shared across role prompts —
    tutor, generator and grader prompts all read the same entry. But a request
    carrying output_config caches a *different*, slightly longer prefix. So
    plain and structured shapes need warming separately; warming only the
    tutor shape leaves /generate, /grade and /flashcards cold.

    Schemas are referenced lazily because they're defined further down.

    Endpoints served from the pre-generated bank are skipped: warming a prefix
    nothing reads is pure waste, and these two are the reason the bank pays
    twice — less traffic AND two fewer ~99K entries to keep warm (~$0.79 off
    every cold round). They're still warmed if the bank is empty for them, so
    the fallback path stays fast.
    """
    targets = [
        ("chat", MODEL_DEFAULT, TUTOR_SYSTEM, None),
        ("grade", MODEL_GRADER, GRADER_SYSTEM, GRADE_SCHEMA),
    ]
    if not (USE_BANK and bank.PRACTICE):
        targets.append(("generate", MODEL_DEFAULT, PROBLEM_GENERATOR_SYSTEM, PROBLEM_SCHEMA))
    if not (USE_BANK and bank.DECKS):
        targets.append(("flashcards", MODEL_FLASHCARDS, FLASHCARD_SYSTEM, FLASHCARD_SCHEMA))
    return targets


def _prewarm_shape(label: str, model: str, role: str, schema: dict | None) -> dict:
    """Write one endpoint's prefix into cache without generating a real response.

    If the entry is already warm this is a cache *read* (~0.1x), so warming a
    live shape is nearly free. The full write price is only paid when the entry
    had actually expired — a cost the next real request would have owed anyway.
    """
    kwargs: dict = {}
    if schema is None:
        # max_tokens=0 runs prefill only and returns immediately.
        attempts = [0, 1]
    else:
        # max_tokens=0 is rejected alongside output_config, so ask for the
        # smallest completion instead. Warming also pre-compiles the schema.
        kwargs["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
        attempts = [1]

    for max_tokens in attempts:
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_system_blocks(role),
                messages=[{"role": "user", "content": "warmup"}],
                **kwargs,
            )
        except (anthropic.APIError, TypeError, ValueError) as e:
            if max_tokens != attempts[-1]:
                continue
            log.warning("prewarm failed for %s/%s: %s", label, model, e)
            return {"endpoint": label, "model": model, "ok": False, "error": str(e)}
        _record_usage(model, resp.usage)
        read = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        log.info("prewarm %s (%s): %s", label, model, "hit" if read else "wrote cache")
        return {"endpoint": label, "model": model, "ok": True, "cache_read_tokens": read}
    return {"endpoint": label, "model": model, "ok": False, "error": "unreachable"}


async def _prewarm_all(targets=None) -> list:
    targets = targets if targets is not None else _warm_targets()
    results = await asyncio.gather(
        *(asyncio.to_thread(_prewarm_shape, *t) for t in targets),
        return_exceptions=True,
    )
    return [r if isinstance(r, dict) else {"ok": False, "error": str(r)} for r in results]


async def _prewarm_loop() -> None:
    """Re-warm only the shapes whose model is actually seeing traffic.

    A blind timer over all four shapes would cost roughly $2.40 per round —
    about $58/day of pure waste on an idle deployment, which would dwarf the
    savings this is meant to produce. Gating on recent use means a quiet night
    costs nothing while an active teaching window stays warm.
    """
    while True:
        await asyncio.sleep(PREWARM_INTERVAL_MIN * 60)
        cutoff = time.time() - PREWARM_IDLE_AFTER_MIN * 60
        active = [t for t in _warm_targets() if _last_used.get(t[1], 0) > cutoff]
        if active:
            await _prewarm_all(active)


# ---------- schemas ----------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class GenerateRequest(BaseModel):
    topic: str = Field(description="Lecture code (L1..L8) or topic name")
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class GradeImage(BaseModel):
    media_type: Literal["image/jpeg", "image/png", "image/webp", "image/gif"]
    data: str = Field(description="Base64-encoded image bytes (no data: prefix)")


class GradeRequest(BaseModel):
    problem: str
    student_work: str = ""
    images: list[GradeImage] = Field(default_factory=list, max_length=8)
    reference_solution: str | None = None


class FlashcardRequest(BaseModel):
    topic: str
    count: int = Field(default=10, ge=3, le=20)


# ---------- open endpoints (no passcode / rate limit) ----------


@app.get("/api/topics")
def topics() -> dict:
    return {"topics": TOPIC_INDEX}


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_default": MODEL_DEFAULT,
        "model_grader": MODEL_GRADER,
        "model_flashcards": MODEL_FLASHCARDS,
        "passcode_required": bool(APP_PASSCODE),
        "corpus_chars": len(CORPUS),
        "cache_ttl": CACHE_TTL,
        "grader_effort": GRADER_EFFORT,
        "bank": {
            "enabled": USE_BANK,
            "practice_problems": bank.practice_count(),
            "flashcard_cards": bank.deck_card_count(),
            "live_endpoints": [t[0] for t in _warm_targets()],
        },
        # If `hits` stays 0 while `misses` climbs, the cached prefix is being
        # invalidated — check that nothing volatile crept into the corpus.
        "cache": {m: dict(_cache_stats[m]) for m in ALL_MODELS},
    }


@app.get("/api/config")
def config() -> dict:
    """Public config the frontend uses to know if a passcode is required."""
    return {"passcode_required": bool(APP_PASSCODE)}


# ---------- protected endpoints ----------


@app.post("/api/chat")
def chat(req: ChatRequest, student: str = Depends(require_access)):
    if not req.messages:
        raise HTTPException(400, "messages cannot be empty")
    t0 = time.time()
    turn = sum(1 for m in req.messages if m.role == "user")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    _mark_used(MODEL_DEFAULT)

    def event_stream():
        try:
            with client.messages.stream(
                model=MODEL_DEFAULT,
                max_tokens=4096,
                system=_system_blocks(TUTOR_SYSTEM),
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
                # Accounting only — if the client disconnects mid-stream this
                # is skipped, so /api/health can undercount chat calls. The
                # cache entry is still written server-side either way.
                u = stream.get_final_message().usage
                _record_usage(MODEL_DEFAULT, u)
                analytics.record(
                    student=analytics.pseudonym(student), tool="chat", served_from="live",
                    model=MODEL_DEFAULT, turn_index=turn,
                    latency_ms=int((time.time() - t0) * 1000),
                    cache_read=u.cache_read_input_tokens, cache_write=u.cache_creation_input_tokens,
                    in_tokens=u.input_tokens, out_tokens=u.output_tokens,
                    cost_usd=analytics.cost(MODEL_DEFAULT, u, CACHE_TTL))
                yield f"data: {json.dumps({'done': True})}\n\n"
        except anthropic.APIError as e:
            analytics.record(student=analytics.pseudonym(student), tool="chat",
                             served_from="live", model=MODEL_DEFAULT, turn_index=turn,
                             ok=False, error_kind=type(e).__name__)
            # Same translation as the JSON endpoints; the raw message would be
            # shown verbatim in the chat bubble.
            yield f"data: {json.dumps({'error': _api_error(e).detail})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


PROBLEM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Short problem title"},
        "statement": {
            "type": "string",
            "description": "Full problem statement with all required data, LaTeX math allowed",
        },
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "topic": {"type": "string", "description": "Lecture code, e.g. L2"},
        "solution": {
            "type": "string",
            "description": "Fully worked step-by-step solution in markdown with LaTeX",
        },
        "final_answer": {"type": "string", "description": "The final numerical or symbolic answer with units"},
        "common_mistakes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "1-3 misconceptions students typically make on this problem",
        },
    },
    "required": [
        "title",
        "statement",
        "difficulty",
        "topic",
        "solution",
        "final_answer",
        "common_mistakes",
    ],
    "additionalProperties": False,
}


@app.post("/api/generate")
def generate_problem(req: GenerateRequest, student: str = Depends(require_access)):
    t0 = time.time()
    if USE_BANK:
        banked = bank.get_problem(req.topic, req.difficulty)
        if banked:
            analytics.record(student=analytics.pseudonym(student), tool="generate",
                             topic=req.topic, difficulty=req.difficulty,
                             served_from="bank", cost_usd=0.0,
                             latency_ms=int((time.time() - t0) * 1000))
            return banked  # pre-vetted, no API call

    topic_desc = TOPIC_INDEX.get(req.topic, req.topic)
    user_msg = (
        f"Generate a NEW {req.difficulty} difficulty problem on topic: "
        f"{req.topic} — {topic_desc}. Ensure it's original (different numbers / "
        f"framing from the tutorial sheets) but uses the same conventions."
    )
    _mark_used(MODEL_DEFAULT)
    try:
        resp = client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=4096,
            system=_system_blocks(PROBLEM_GENERATOR_SYSTEM),
            messages=[{"role": "user", "content": user_msg}],
            output_config={"format": {"type": "json_schema", "schema": PROBLEM_SCHEMA}},
        )
    except anthropic.APIError as e:
        analytics.record(student=analytics.pseudonym(student), tool="generate",
                         topic=req.topic, difficulty=req.difficulty, served_from="live",
                         model=MODEL_DEFAULT, ok=False, error_kind=type(e).__name__)
        raise _api_error(e) from e

    _record_usage(MODEL_DEFAULT, resp.usage)
    u = resp.usage
    analytics.record(student=analytics.pseudonym(student), tool="generate",
                     topic=req.topic, difficulty=req.difficulty, served_from="live",
                     model=MODEL_DEFAULT, latency_ms=int((time.time() - t0) * 1000),
                     cache_read=u.cache_read_input_tokens, cache_write=u.cache_creation_input_tokens,
                     in_tokens=u.input_tokens, out_tokens=u.output_tokens,
                     cost_usd=analytics.cost(MODEL_DEFAULT, u, CACHE_TTL))
    return _extract_json(resp)


GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["correct", "partially_correct", "incorrect"],
        },
        "score_out_of_10": {"type": "integer", "description": "Integer score from 0 to 10"},
        "error_type": {
            "type": "string",
            "enum": ["none", "conceptual", "setup", "algebra_arithmetic", "units"],
        },
        "first_error_step": {
            "type": "string",
            "description": "If incorrect, describe where the student's reasoning first went wrong. Empty if correct.",
        },
        "feedback": {
            "type": "string",
            "description": "Focused feedback (<200 words) that helps the student learn. LaTeX allowed.",
        },
        "what_was_right": {
            "type": "string",
            "description": "Brief acknowledgement of what the student did correctly.",
        },
        "suggested_next_step": {
            "type": "string",
            "description": "A specific next action to take (e.g. 'revisit L2 §Entropy, redo part (b) using dS = dQ_rev/T').",
        },
        # Classification for analytics. Free: the model is already producing
        # structured output, so these add no extra call. They're what turns a
        # usage log into teaching signal — "61% of L4 errors were conceptual,
        # clustered on Clausius-Clapeyron" is actionable; "340 gradings" isn't.
        "topic": {
            "type": "string",
            "enum": ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "unknown"],
            "description": "Which lecture this problem belongs to.",
        },
        "concept_tested": {
            "type": "string",
            "description": "The specific concept or relationship under test, as a short "
                           "canonical noun phrase reusable across submissions — e.g. "
                           "'entropy change on heating at constant P', 'Clausius-Clapeyron', "
                           "'lever rule'. Not a restatement of the problem.",
        },
    },
    "required": [
        "verdict",
        "score_out_of_10",
        "error_type",
        "first_error_step",
        "feedback",
        "what_was_right",
        "suggested_next_step",
        "topic",
        "concept_tested",
    ],
    "additionalProperties": False,
}


@app.post("/api/grade")
def grade(req: GradeRequest, student: str = Depends(require_access)):
    t0 = time.time()
    if not req.student_work.strip() and not req.images:
        raise HTTPException(400, "Provide typed work, an image, or both.")

    content: list[dict] = [{"type": "text", "text": f"PROBLEM:\n{req.problem}"}]

    if req.student_work.strip():
        content.append({"type": "text", "text": f"STUDENT WORK (typed):\n{req.student_work}"})

    if req.images:
        content.append({
            "type": "text",
            "text": (
                f"STUDENT WORK ({len(req.images)} handwritten page"
                f"{'s' if len(req.images) > 1 else ''} attached). Transcribe the "
                "student's steps as you read them, then grade the reasoning. If "
                "handwriting is ambiguous on a key step, call it out in feedback "
                "rather than guessing."
            ),
        })
        for img in req.images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": img.data,
                },
            })

    if req.reference_solution:
        content.append({
            "type": "text",
            "text": f"REFERENCE SOLUTION (for your eyes only):\n{req.reference_solution}",
        })

    content.append({"type": "text", "text": "Grade this submission."})

    _mark_used(MODEL_GRADER)
    try:
        resp = client.messages.create(
            model=MODEL_GRADER,
            # max_tokens caps thinking AND response text together. Adaptive
            # thinking on a multi-page handwritten submission can eat most of a
            # 4096 budget and truncate the JSON mid-object, so give it headroom.
            # Unused tokens aren't billed.
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=_system_blocks(GRADER_SYSTEM),
            messages=[{"role": "user", "content": content}],
            output_config={
                "format": {"type": "json_schema", "schema": GRADE_SCHEMA},
                "effort": GRADER_EFFORT,
            },
        )
    except anthropic.APIError as e:
        analytics.record(student=analytics.pseudonym(student), tool="grade",
                         served_from="live", model=MODEL_GRADER,
                         image_count=len(req.images), ok=False, error_kind=type(e).__name__)
        raise _api_error(e) from e

    _record_usage(MODEL_GRADER, resp.usage)
    out = _extract_json(resp)
    u = resp.usage
    analytics.record(
        student=analytics.pseudonym(student), tool="grade", served_from="live",
        model=MODEL_GRADER, latency_ms=int((time.time() - t0) * 1000),
        # The classification the grader just produced for free — this is the
        # column that answers "which lecture produces which errors".
        topic=out.get("topic"), concept=out.get("concept_tested"),
        verdict=out.get("verdict"), error_type=out.get("error_type"),
        score=out.get("score_out_of_10"), image_count=len(req.images),
        cache_read=u.cache_read_input_tokens, cache_write=u.cache_creation_input_tokens,
        in_tokens=u.input_tokens, out_tokens=u.output_tokens,
        cost_usd=analytics.cost(MODEL_GRADER, u, CACHE_TTL))
    return out


FLASHCARD_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "front": {"type": "string", "description": "Question or prompt"},
                    "back": {"type": "string", "description": "Answer (1-3 sentences or one equation)"},
                    "difficulty": {"type": "integer", "description": "1 (foundational), 2 (intermediate), or 3 (tricky)"},
                    "category": {
                        "type": "string",
                        "enum": ["definition", "equation", "concept", "pitfall"],
                    },
                },
                "required": ["front", "back", "difficulty", "category"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["topic", "cards"],
    "additionalProperties": False,
}


@app.post("/api/flashcards")
def flashcards(req: FlashcardRequest, student: str = Depends(require_access)):
    t0 = time.time()
    if USE_BANK:
        banked = bank.get_cards(req.topic, req.count)
        if banked:
            analytics.record(student=analytics.pseudonym(student), tool="flashcards",
                             topic=req.topic, served_from="bank", cost_usd=0.0,
                             latency_ms=int((time.time() - t0) * 1000))
            return banked  # sampled from a larger pre-built deck

    topic_desc = TOPIC_INDEX.get(req.topic, req.topic)
    user_msg = (
        f"Produce exactly {req.count} flashcards for topic {req.topic} — {topic_desc}."
    )
    _mark_used(MODEL_FLASHCARDS)
    try:
        resp = client.messages.create(
            model=MODEL_FLASHCARDS,
            max_tokens=4096,
            system=_system_blocks(FLASHCARD_SYSTEM),
            messages=[{"role": "user", "content": user_msg}],
            output_config={"format": {"type": "json_schema", "schema": FLASHCARD_SCHEMA}},
        )
    except anthropic.APIError as e:
        analytics.record(student=analytics.pseudonym(student), tool="flashcards",
                         topic=req.topic, served_from="live", model=MODEL_FLASHCARDS,
                         ok=False, error_kind=type(e).__name__)
        raise _api_error(e) from e

    _record_usage(MODEL_FLASHCARDS, resp.usage)
    u = resp.usage
    analytics.record(student=analytics.pseudonym(student), tool="flashcards",
                     topic=req.topic, served_from="live", model=MODEL_FLASHCARDS,
                     latency_ms=int((time.time() - t0) * 1000),
                     cache_read=u.cache_read_input_tokens, cache_write=u.cache_creation_input_tokens,
                     in_tokens=u.input_tokens, out_tokens=u.output_tokens,
                     cost_usd=analytics.cost(MODEL_FLASHCARDS, u, CACHE_TTL))
    return _extract_json(resp)


@app.post("/api/prewarm")
async def prewarm(_: str = Depends(require_access)) -> dict:
    """Warm every model's corpus cache on demand.

    Point a cron job at this ~10 minutes before a tutorial slot so the first
    student of the session doesn't wait on a cold cache.
    """
    return {"results": await _prewarm_all()}


# ---------- analytics (passcode-protected) ----------


@app.get("/api/admin/stats")
def admin_stats(_: str = Depends(require_access)) -> dict:
    """Aggregates for the dashboard and for sharing with colleagues."""
    return analytics.summary()


@app.get("/api/admin/export.csv")
def admin_export(since: str | None = None, _: str = Depends(require_access)):
    """Full pseudonymous event export for analysis in R / Python / SPSS.

    `since` is an inclusive YYYY-MM-DD lower bound. Contains no student work —
    see analytics.py for what is and isn't retained.
    """
    import csv
    import io

    cols, rows = analytics.export_rows(since)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    w.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="captain_thermo_events.csv"'},
    )


# ---------- static frontend ----------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
