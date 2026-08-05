"""Pre-generated practice problems and flashcard decks, loaded from disk.

Built once by scripts/build_bank.py at Batch API rates and committed to the
repo, so it ships inside the container and survives deploys (Render has no
persistent disk). Serving from here instead of generating live removes ~35%
of API traffic and two of the four prompt-cache prefixes the app keeps warm.

Every entry has the same shape the live endpoints return, so the frontend is
unchanged and falling back to live generation is transparent.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

BANK_DIR = Path(__file__).resolve().parent.parent / "course_content" / "generated"


def _load(name: str) -> dict:
    path = BANK_DIR / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# {"L2|medium": [problem, ...]}
PRACTICE: dict[str, list[dict]] = _load("practice_bank.json")
# {"L2": {"topic": ..., "cards": [...]}}
DECKS: dict[str, dict] = _load("flashcard_decks.json")


def practice_count() -> int:
    return sum(len(v) for v in PRACTICE.values())


def deck_card_count() -> int:
    return sum(len(d.get("cards", [])) for d in DECKS.values())


def get_problem(topic: str, difficulty: str, exclude: str | None = None) -> dict | None:
    """A random banked problem, avoiding an immediate repeat where possible."""
    pool = PRACTICE.get(f"{topic}|{difficulty}") or []
    if not pool:
        return None
    if exclude and len(pool) > 1:
        pool = [p for p in pool if p.get("title") != exclude] or pool
    return random.choice(pool)


def get_cards(topic: str, count: int) -> dict | None:
    """A banked deck sampled down to `count` cards.

    Decks are built with more cards than the UI asks for, so sampling gives
    each student a different subset rather than an identical deck. Sampling is
    stratified by category so a short draw doesn't come out all-definitions.
    """
    deck = DECKS.get(topic)
    cards = (deck or {}).get("cards") or []
    if not deck or len(cards) < count:
        return None

    by_cat: dict[str, list[dict]] = {}
    for c in cards:
        by_cat.setdefault(c.get("category", "concept"), []).append(c)
    for group in by_cat.values():
        random.shuffle(group)

    picked: list[dict] = []
    # Round-robin across categories preserves the definition/equation/concept/
    # pitfall mix the prompt asks for.
    while len(picked) < count:
        added = False
        for group in by_cat.values():
            if group and len(picked) < count:
                picked.append(group.pop())
                added = True
        if not added:
            break
    random.shuffle(picked)
    return {"topic": deck.get("topic", topic), "cards": picked}
