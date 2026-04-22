"""Captain Thermo — FastAPI backend for MS1016 student learning tools.

Four tools in one app:
  /api/chat            Socratic tutor (streaming)
  /api/generate        Practice problem generator (JSON)
  /api/grade           Student-work grader (JSON, adaptive thinking)
  /api/flashcards      Spaced-repetition deck generator (JSON)

Models:
  ANTHROPIC_MODEL_DEFAULT  used for tutor, practice, flashcards (default: sonnet-4-6, cheap & fast)
  ANTHROPIC_MODEL_GRADER   used for the grader (default: opus-4-7, best reasoning)

Access control:
  APP_PASSCODE    if set, clients must send X-Passcode header matching this value
  RATE_LIMIT_PER_MIN    per-IP requests per minute on /api/* (default 30)
  RATE_LIMIT_PER_DAY    per-IP requests per day on /api/* (default 300)
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from corpus import CORPUS, TOPIC_INDEX
from prompts import (
    FLASHCARD_SYSTEM,
    GRADER_SYSTEM,
    PROBLEM_GENERATOR_SYSTEM,
    TUTOR_SYSTEM,
)

load_dotenv()

MODEL_DEFAULT = os.getenv("ANTHROPIC_MODEL_DEFAULT", "claude-sonnet-4-6")
MODEL_GRADER = os.getenv("ANTHROPIC_MODEL_GRADER", "claude-opus-4-7")
APP_PASSCODE = os.getenv("APP_PASSCODE", "").strip()
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "300"))

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

client = anthropic.Anthropic()

app = FastAPI(title="Captain Thermo", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- access control & rate limiting ----------

# In-memory sliding-window counters. Fine for a single-instance deploy.
# For multi-instance, swap for Redis or an external limiter.
_minute_hits: dict[str, list[float]] = defaultdict(list)
_day_hits: dict[str, list[float]] = defaultdict(list)


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


def require_access(
    request: Request,
    x_passcode: str | None = Header(default=None),
) -> str:
    """Dependency: check passcode (if configured) and rate limits."""
    if APP_PASSCODE and x_passcode != APP_PASSCODE:
        raise HTTPException(401, "Invalid or missing passcode")

    ip = _client_ip(request)
    now = time.time()

    _prune(_minute_hits[ip], 60, now)
    if len(_minute_hits[ip]) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Rate limit (per minute) exceeded — slow down.")

    _prune(_day_hits[ip], 86400, now)
    if len(_day_hits[ip]) >= RATE_LIMIT_PER_DAY:
        raise HTTPException(429, "Daily quota exceeded — try again tomorrow.")

    _minute_hits[ip].append(now)
    _day_hits[ip].append(now)
    return ip


# ---------- helpers ----------


def _extract_json(resp) -> dict:
    """Pull JSON out of a Messages response, tolerating markdown fences and preambles.

    Structured outputs *should* return pure JSON in the first text block, but
    occasionally the model wraps it in ```json ... ``` or prepends a sentence.
    Try strict parse first; fall back to fence-stripping and brace-scanning.
    """
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


def _system_blocks(role_prompt: str) -> list[dict]:
    """Build a two-block system: [cached course corpus, role-specific instructions].

    The corpus is the stable prefix — cache_control on this block means subsequent
    requests reuse it at ~10% cost.
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
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": role_prompt},
    ]


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
        "passcode_required": bool(APP_PASSCODE),
        "corpus_chars": len(CORPUS),
    }


@app.get("/api/config")
def config() -> dict:
    """Public config the frontend uses to know if a passcode is required."""
    return {"passcode_required": bool(APP_PASSCODE)}


# ---------- protected endpoints ----------


@app.post("/api/chat")
def chat(req: ChatRequest, _: str = Depends(require_access)):
    if not req.messages:
        raise HTTPException(400, "messages cannot be empty")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

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
                yield f"data: {json.dumps({'done': True})}\n\n"
        except anthropic.APIError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

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
def generate_problem(req: GenerateRequest, _: str = Depends(require_access)):
    topic_desc = TOPIC_INDEX.get(req.topic, req.topic)
    user_msg = (
        f"Generate a NEW {req.difficulty} difficulty problem on topic: "
        f"{req.topic} — {topic_desc}. Ensure it's original (different numbers / "
        f"framing from the tutorial sheets) but uses the same conventions."
    )
    try:
        resp = client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=4096,
            system=_system_blocks(PROBLEM_GENERATOR_SYSTEM),
            messages=[{"role": "user", "content": user_msg}],
            output_config={"format": {"type": "json_schema", "schema": PROBLEM_SCHEMA}},
        )
    except anthropic.APIError as e:
        raise HTTPException(502, f"Anthropic error: {e}") from e

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
    },
    "required": [
        "verdict",
        "score_out_of_10",
        "error_type",
        "first_error_step",
        "feedback",
        "what_was_right",
        "suggested_next_step",
    ],
    "additionalProperties": False,
}


@app.post("/api/grade")
def grade(req: GradeRequest, _: str = Depends(require_access)):
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

    try:
        resp = client.messages.create(
            model=MODEL_GRADER,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=_system_blocks(GRADER_SYSTEM),
            messages=[{"role": "user", "content": content}],
            output_config={"format": {"type": "json_schema", "schema": GRADE_SCHEMA}},
        )
    except anthropic.APIError as e:
        raise HTTPException(502, f"Anthropic error: {e}") from e

    return _extract_json(resp)


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
def flashcards(req: FlashcardRequest, _: str = Depends(require_access)):
    topic_desc = TOPIC_INDEX.get(req.topic, req.topic)
    user_msg = (
        f"Produce exactly {req.count} flashcards for topic {req.topic} — {topic_desc}."
    )
    try:
        resp = client.messages.create(
            model=MODEL_DEFAULT,
            max_tokens=4096,
            system=_system_blocks(FLASHCARD_SYSTEM),
            messages=[{"role": "user", "content": user_msg}],
            output_config={"format": {"type": "json_schema", "schema": FLASHCARD_SCHEMA}},
        )
    except anthropic.APIError as e:
        raise HTTPException(502, f"Anthropic error: {e}") from e

    return _extract_json(resp)


# ---------- static frontend ----------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
