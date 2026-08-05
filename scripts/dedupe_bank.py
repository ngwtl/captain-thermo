"""Remove near-duplicate problems from the generated practice bank.

Why this is needed: variants are generated in parallel and none of them can see
the others, so "make it materially different from the others" has nothing to
act on. The result converges — in one L2/medium set, five of ten problems were
isothermal expansion or compression of an ideal gas, differing only in which
noble gas was named, and two titles were identical.

Six genuinely distinct problems beat ten with five clones, so this keeps one
representative per cluster.

The similarity test deliberately strips *substance names* before comparing.
"Isothermal compression of nitrogen" and "isothermal expansion of argon" are
the same exercise wearing a different hat; a student who has done one has
learned what the other teaches. Physics words (isothermal, vaporising,
allotropic, Curie) are what actually distinguish problems, so those are kept.

Usage:
    python scripts/dedupe_bank.py            # report only, changes nothing
    python scripts/dedupe_bank.py --apply    # rewrite the bank in place
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BANK = Path(__file__).resolve().parent.parent / "course_content" / "generated" / "practice_bank.json"

# Named substances carry no pedagogical difference — swapping argon for
# nitrogen doesn't change what the problem teaches.
SUBSTANCES = {
    "nitrogen", "argon", "helium", "neon", "krypton", "xenon", "oxygen",
    "hydrogen", "copper", "nickel", "iron", "aluminium", "aluminum", "lead",
    "tin", "silver", "gold", "zinc", "magnesium", "titanium", "tungsten",
    "carbon", "steel", "water", "steam", "ice", "mercury", "sodium", "calcium",
    "methane", "ammonia", "ethanol", "benzene", "co2", "n2", "o2", "h2o",
    "gas", "liquid", "solid", "metal", "sample", "mol", "mole", "moles",
}
FILLER = {
    "the", "a", "an", "of", "on", "in", "for", "to", "and", "with", "at",
    "its", "through", "during", "from", "into", "change", "problem", "find",
    "calculate", "determine", "compute",
}


def _key_terms(text: str) -> set[str]:
    """The physics-bearing words of a title, with substances and filler removed."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for w in words:
        w = re.sub(r"(ing|ion|ions|es|s)$", "", w) if len(w) > 5 else w
        if w and w not in SUBSTANCES and w not in FILLER and len(w) > 2:
            out.add(w)
    return out


def _similar(a: dict, b: dict, threshold: float = 0.6) -> bool:
    ta, tb = _key_terms(a.get("title", "")), _key_terms(b.get("title", ""))
    if not ta or not tb:
        return False
    jaccard = len(ta & tb) / len(ta | tb)
    return jaccard >= threshold


def _score(p: dict) -> tuple:
    """Prefer the richer problem when collapsing a cluster."""
    return (len(p.get("common_mistakes") or []), len(p.get("solution") or ""))


def dedupe(bank: dict) -> tuple[dict, list[tuple[str, str, str]]]:
    out: dict[str, list] = {}
    dropped: list[tuple[str, str, str]] = []
    for combo, problems in bank.items():
        kept: list[dict] = []
        for p in sorted(problems, key=_score, reverse=True):   # richest first
            match = next((k for k in kept if _similar(p, k)), None)
            if match is None:
                kept.append(p)
            else:
                dropped.append((combo, p.get("title", "?"), match.get("title", "?")))
        # restore a stable order
        out[combo] = sorted(kept, key=lambda x: x.get("title", ""))
    return out, dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="rewrite the bank in place")
    args = ap.parse_args()

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    before = sum(len(v) for v in bank.values())
    cleaned, dropped = dedupe(bank)
    after = sum(len(v) for v in cleaned.values())

    for combo, gone, kept_as in dropped:
        print(f"  {combo:14} drop  {gone[:58]:60} ~ {kept_as[:45]}")

    print(f"\n{before} -> {after} problems ({len(dropped)} near-duplicates removed)")
    thin = {c: len(v) for c, v in cleaned.items() if len(v) < 4}
    if thin:
        print(f"thin combos (<4 distinct): {thin}")
    print(f"per-combo distinct: min {min(len(v) for v in cleaned.values())}, "
          f"median {sorted(len(v) for v in cleaned.values())[len(cleaned)//2]}, "
          f"max {max(len(v) for v in cleaned.values())}")

    if args.apply:
        BANK.write_text(json.dumps(cleaned, indent=1, ensure_ascii=False))
        print(f"\nwritten to {BANK}")
    else:
        print("\n(dry run — pass --apply to rewrite)")


if __name__ == "__main__":
    main()
