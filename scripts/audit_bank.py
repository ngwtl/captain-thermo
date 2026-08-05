"""Audit the practice bank for defects that a student cannot detect themselves.

These three checks exist because a review of the first generated bank found 24%
of problems carrying at least one of them. What makes them worth automating is
not their frequency but their invisibility: a student who already knows the
right answer will spot them, and that student doesn't need the tool. The
student who does need it will absorb the error.

  sign-convention  Uses dU = Q - W. The consolidated notes standardise on
                   dU = Q + W and explicitly flag that the original slides
                   sometimes differ, so a problem using the other convention
                   reintroduces exactly the confusion the notes exist to
                   remove. Sign errors are the most common failure in the
                   course. This is the serious one.
  reversibility    Statement says heat is supplied "reversibly" while the
                   solution concludes the process is irreversible. Internally
                   contradictory; confuses precisely the careful students.
  latex            Nested subscripts (Q_\\text{rev,N}_2) that MathJax cannot
                   render, so the student sees an error where an equation
                   should be.

Removing a defective problem is enough to fix it: build_bank.py only generates
what is missing, so re-running refills the gap using the corrected prompt.

Usage:
    python scripts/audit_bank.py             # report only
    python scripts/audit_bank.py --remove    # drop defective problems
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

BANK = Path(__file__).resolve().parent.parent / "course_content" / "generated" / "practice_bank.json"

CHECKS = {
    "sign-convention": lambda t, s: bool(re.search(r"\\Delta U\s*=\s*Q\s*-\s*W|\bU\s*=\s*Q\s*-\s*W", t)),
    "reversibility": lambda t, s: bool(re.search(r"reversibl", s, re.I))
                                 and bool(re.search(r"irreversib", t, re.I)),
    "latex": lambda t, s: bool(re.search(r"_\{[^}]*\}_|_[a-zA-Z0-9]_\{|\}_\d", t)),
}


def defects(p: dict) -> list[str]:
    full = " ".join([p.get("statement", ""), p.get("solution", ""),
                     *(p.get("common_mistakes") or [])])
    return [name for name, test in CHECKS.items() if test(full, p.get("statement", ""))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true", help="drop defective problems")
    args = ap.parse_args()

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    total = sum(len(v) for v in bank.values())
    kinds: collections.Counter = collections.Counter()
    flagged = 0
    cleaned: dict[str, list] = {}

    for combo, problems in bank.items():
        keep = []
        for p in problems:
            d = defects(p)
            if not d:
                keep.append(p)
                continue
            flagged += 1
            kinds.update(d)
            if "sign-convention" in d:
                print(f"  {combo:12} [{'+'.join(d)}] {p.get('title','?')[:56]}")
        cleaned[combo] = keep

    print(f"\n{flagged} of {total} problems defective ({flagged/total*100:.0f}%)")
    for k, n in kinds.most_common():
        print(f"  {n:>4}  {k}")

    if args.remove:
        BANK.write_text(json.dumps(cleaned, indent=1, ensure_ascii=False))
        left = sum(len(v) for v in cleaned.values())
        thin = {c: len(v) for c, v in sorted(cleaned.items()) if len(v) < 5}
        print(f"\nremoved -> {left} problems remain")
        if thin:
            print(f"combos now under 5: {thin}")
        print("re-run `python scripts/build_bank.py --direct` to refill with the corrected prompt")
    else:
        print("\n(report only — pass --remove to drop them)")


if __name__ == "__main__":
    main()
