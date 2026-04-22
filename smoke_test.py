"""Captain Thermo end-to-end smoke test.

Hits every endpoint with a real request. Use against a locally running server
(http://localhost:8000) or a deployed URL. Prints PASS/FAIL per endpoint.

Usage:
  python smoke_test.py                               # tests http://localhost:8000
  python smoke_test.py --url https://captain-thermo.onrender.com
  python smoke_test.py --passcode secret123          # if APP_PASSCODE is set
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from urllib import error, request


def _req(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: float = 120.0):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = request.Request(url, data=data, method=method, headers=hdrs)
    with request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def test_health(base: str, headers: dict) -> bool:
    print("→ /api/health ...", end=" ", flush=True)
    try:
        status, body = _req(f"{base}/api/health", headers=headers)
        data = json.loads(body)
        ok = status == 200 and data.get("status") == "ok" and data.get("corpus_chars", 0) > 50_000
        print("PASS" if ok else f"FAIL ({status}, corpus_chars={data.get('corpus_chars')})")
        if ok:
            print(f"   model_default={data['model_default']}, model_grader={data['model_grader']}, passcode_required={data['passcode_required']}")
        return ok
    except error.URLError as e:
        print(f"FAIL (connection: {e})")
        return False


def test_topics(base: str, headers: dict) -> bool:
    print("→ /api/topics ...", end=" ", flush=True)
    try:
        status, body = _req(f"{base}/api/topics", headers=headers)
        data = json.loads(body)
        ok = status == 200 and "L1" in data.get("topics", {})
        print("PASS" if ok else f"FAIL ({status})")
        return ok
    except error.URLError as e:
        print(f"FAIL ({e})")
        return False


def test_chat(base: str, headers: dict) -> bool:
    print("→ /api/chat (streaming) ...", end=" ", flush=True)
    try:
        t0 = time.time()
        status, body = _req(
            f"{base}/api/chat",
            method="POST",
            body={"messages": [{"role": "user", "content": "What is the Second Law in one sentence?"}]},
            headers=headers,
        )
        text = body.decode()
        # SSE format: data: {...}\n\n repeated
        chunks = [line for line in text.split("\n") if line.startswith("data: ")]
        accumulated = ""
        for c in chunks:
            try:
                obj = json.loads(c[6:])
                if "text" in obj:
                    accumulated += obj["text"]
            except json.JSONDecodeError:
                pass
        elapsed = time.time() - t0
        ok = status == 200 and len(accumulated) > 20 and "entropy" in accumulated.lower()
        print(f"PASS ({elapsed:.1f}s, {len(accumulated)} chars)" if ok else f"FAIL (status={status}, len={len(accumulated)})")
        if not ok:
            print(f"   body preview: {accumulated[:120]}")
        return ok
    except error.URLError as e:
        print(f"FAIL ({e})")
        return False


def test_generate(base: str, headers: dict) -> bool:
    print("→ /api/generate (L2 medium) ...", end=" ", flush=True)
    try:
        t0 = time.time()
        status, body = _req(
            f"{base}/api/generate",
            method="POST",
            body={"topic": "L2", "difficulty": "medium"},
            headers=headers,
        )
        data = json.loads(body)
        ok = (
            status == 200
            and all(k in data for k in ("title", "statement", "solution", "final_answer", "common_mistakes"))
            and len(data["statement"]) > 40
            and isinstance(data["common_mistakes"], list)
        )
        elapsed = time.time() - t0
        print(f"PASS ({elapsed:.1f}s — '{data.get('title', '?')[:50]}')" if ok else f"FAIL ({status})")
        return ok
    except error.URLError as e:
        print(f"FAIL ({e})")
        return False


def test_grade(base: str, headers: dict) -> bool:
    print("→ /api/grade (deliberate wrong answer) ...", end=" ", flush=True)
    try:
        t0 = time.time()
        status, body = _req(
            f"{base}/api/grade",
            method="POST",
            body={
                "problem": "A reversible isothermal expansion of 1 mol of ideal gas at 300 K from 1 L to 10 L. Find ΔS of the system.",
                "student_work": "ΔS = nRT ln(V2/V1) = 1 × 8.314 × 300 × ln(10) = 5743 J/K. Answer: ΔS ≈ 5743 J/K.",
            },
            headers=headers,
            timeout=180.0,
        )
        data = json.loads(body)
        ok = (
            status == 200
            and data.get("verdict") in ("incorrect", "partially_correct")
            and data.get("error_type") in ("conceptual", "setup")
            and len(data.get("feedback", "")) > 30
        )
        elapsed = time.time() - t0
        print(f"PASS ({elapsed:.1f}s — verdict={data.get('verdict')}, error={data.get('error_type')})" if ok else f"FAIL ({status}, verdict={data.get('verdict')})")
        if not ok:
            print(f"   response: {json.dumps(data)[:200]}")
        return ok
    except error.URLError as e:
        print(f"FAIL ({e})")
        return False


def test_flashcards(base: str, headers: dict) -> bool:
    print("→ /api/flashcards (L1, 5 cards) ...", end=" ", flush=True)
    try:
        t0 = time.time()
        status, body = _req(
            f"{base}/api/flashcards",
            method="POST",
            body={"topic": "L1", "count": 5},
            headers=headers,
        )
        data = json.loads(body)
        cards = data.get("cards", [])
        ok = status == 200 and len(cards) == 5 and all("front" in c and "back" in c for c in cards)
        elapsed = time.time() - t0
        print(f"PASS ({elapsed:.1f}s, {len(cards)} cards)" if ok else f"FAIL ({status}, n={len(cards)})")
        return ok
    except error.URLError as e:
        print(f"FAIL ({e})")
        return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000", help="Base URL of the server")
    p.add_argument("--passcode", default="", help="X-Passcode header value (if APP_PASSCODE is set)")
    args = p.parse_args()

    base = args.url.rstrip("/")
    headers = {"X-Passcode": args.passcode} if args.passcode else {}

    print(f"Captain Thermo smoke test → {base}")
    print("=" * 60)

    tests = [
        ("health", test_health),
        ("topics", test_topics),
        ("chat", test_chat),
        ("generate", test_generate),
        ("grade", test_grade),
        ("flashcards", test_flashcards),
    ]
    results = {name: fn(base, headers) for name, fn in tests}

    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
