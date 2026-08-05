"""Pre-generate the practice-problem bank and flashcard decks.

Run this ONCE per corpus revision, not per request. Two reasons it beats
generating live:

  * Cost. Fifty students asking for an L2 deck currently triggers fifty
    near-identical API calls, each re-reading the ~99K-token corpus. The bank
    is built once, at Batch API rates (50% off), and then served from disk for
    free. It also removes two of the four prompt-cache prefixes the running
    app has to keep warm.
  * Quality. Right now every practice problem reaches a student unvetted.
    A bank is a file you can read through and fix before anyone sees it.

Output is committed to the repo (see course_content/generated/), so it ships
inside the container and survives deploys — Render has no persistent disk.

Usage:
    python scripts/build_bank.py            # submit + wait + write files
    python scripts/build_bank.py --resume BATCH_ID   # collect an earlier run
    python scripts/build_bank.py --per-combo 10      # fewer problems
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import anthropic
from dotenv import load_dotenv

from corpus import CORPUS, TOPIC_INDEX  # noqa: E402
from prompts import FLASHCARD_SYSTEM, PROBLEM_GENERATOR_SYSTEM  # noqa: E402

load_dotenv()

OUT_DIR = Path(__file__).resolve().parent.parent / "course_content" / "generated"
DIFFICULTIES = ("easy", "medium", "hard")
CARDS_PER_DECK = 20          # frontend asks for 10; extra gives sampling room
MODEL_PRACTICE = "claude-sonnet-4-6"
MODEL_CARDS = "claude-haiku-4-5"

client = anthropic.Anthropic()

# Import the schemas from the app so the bank can never drift from what the
# live endpoints would have produced.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app import FLASHCARD_SCHEMA, PROBLEM_SCHEMA, _system_blocks  # noqa: E402


def _requests(per_combo: int) -> list[dict]:
    reqs: list[dict] = []
    for topic, desc in TOPIC_INDEX.items():
        for diff in DIFFICULTIES:
            for i in range(per_combo):
                reqs.append({
                    "custom_id": f"practice-{topic}-{diff}-{i}",
                    "params": {
                        "model": MODEL_PRACTICE,
                        "max_tokens": 4096,
                        "system": _system_blocks(PROBLEM_GENERATOR_SYSTEM),
                        "messages": [{
                            "role": "user",
                            "content": (
                                f"Generate a NEW {diff} difficulty problem on topic: "
                                f"{topic} — {desc}. Ensure it's original (different "
                                f"numbers / framing from the tutorial sheets) but uses "
                                f"the same conventions. This is variant #{i + 1} of "
                                f"{per_combo} — make it materially different from the "
                                f"others: vary the sub-topic, the quantity being solved "
                                f"for, and the physical setting."
                            ),
                        }],
                        "output_config": {"format": {"type": "json_schema", "schema": PROBLEM_SCHEMA}},
                    },
                })
        reqs.append({
            "custom_id": f"cards-{topic}",
            "params": {
                "model": MODEL_CARDS,
                "max_tokens": 8192,
                "system": _system_blocks(FLASHCARD_SYSTEM),
                "messages": [{
                    "role": "user",
                    "content": f"Produce exactly {CARDS_PER_DECK} flashcards for topic {topic} — {desc}.",
                }],
                "output_config": {"format": {"type": "json_schema", "schema": FLASHCARD_SCHEMA}},
            },
        })
    return reqs


def _collect(batch_id: str) -> tuple[dict, dict, dict]:
    practice: dict[str, list] = {}
    decks: dict[str, dict] = {}
    stats = {"succeeded": 0, "failed": 0, "unparseable": 0,
             "in_tokens": 0, "cache_read": 0, "cache_write": 0, "out_tokens": 0}

    for res in client.messages.batches.results(batch_id):
        if res.result.type != "succeeded":
            stats["failed"] += 1
            continue
        msg = res.result.message
        u = msg.usage
        stats["in_tokens"] += u.input_tokens
        stats["cache_read"] += u.cache_read_input_tokens or 0
        stats["cache_write"] += u.cache_creation_input_tokens or 0
        stats["out_tokens"] += u.output_tokens
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            stats["unparseable"] += 1
            continue
        stats["succeeded"] += 1
        if res.custom_id.startswith("practice-"):
            _, topic, diff, _i = res.custom_id.split("-", 3)
            practice.setdefault(f"{topic}|{diff}", []).append(data)
        else:
            decks[res.custom_id.split("-", 1)[1]] = data
    return practice, decks, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-combo", type=int, default=10)
    ap.add_argument("--resume", help="collect results from an existing batch id")
    args = ap.parse_args()

    if args.resume:
        batch_id = args.resume
    else:
        reqs = _requests(args.per_combo)
        print(f"submitting {len(reqs)} requests "
              f"({len(TOPIC_INDEX)} topics x {len(DIFFICULTIES)} difficulties x "
              f"{args.per_combo} + {len(TOPIC_INDEX)} decks)")
        batch = client.messages.batches.create(requests=reqs)
        batch_id = batch.id
        print(f"batch id: {batch_id}   (resume with --resume {batch_id})")

    while True:
        b = client.messages.batches.retrieve(batch_id)
        if b.processing_status == "ended":
            break
        c = b.request_counts
        print(f"  {b.processing_status}: processing={c.processing} succeeded={c.succeeded} errored={c.errored}",
              flush=True)
        time.sleep(30)

    practice, decks, stats = _collect(batch_id)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "practice_bank.json").write_text(json.dumps(practice, indent=1, ensure_ascii=False))
    (OUT_DIR / "flashcard_decks.json").write_text(json.dumps(decks, indent=1, ensure_ascii=False))

    # Batch pricing is 50% of standard; cache reads are 10% of input price.
    price = {"sonnet": (3, 15), "haiku": (1, 5)}
    est = (stats["cache_read"] * 0.1 * 3 + stats["cache_write"] * 1.25 * 3
           + stats["in_tokens"] * 3 + stats["out_tokens"] * 15) / 1e6 * 0.5

    print(f"\npractice: {sum(len(v) for v in practice.values())} problems "
          f"across {len(practice)} topic/difficulty combos")
    print(f"decks:    {len(decks)} topics, "
          f"{sum(len(d.get('cards', [])) for d in decks.values())} cards")
    print(f"failed={stats['failed']} unparseable={stats['unparseable']}")
    print(f"tokens: cache_read={stats['cache_read']:,} cache_write={stats['cache_write']:,} "
          f"in={stats['in_tokens']:,} out={stats['out_tokens']:,}")
    print(f"approx batch cost: ${est:.2f}")
    print(f"written to {OUT_DIR}")


if __name__ == "__main__":
    main()
