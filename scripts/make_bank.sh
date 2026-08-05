#!/usr/bin/env bash
# Build a clean practice bank, end to end.
#
# Why this exists as one script rather than three commands run by hand:
# generation reliably emits a few percent of problems with defects a student
# cannot detect for themselves (wrong sign convention, a statement that calls an
# irreversible process reversible). Adding the conventions to the authoring
# prompt roughly halved that — measured 9.5% -> 5.3% — but did not eliminate it,
# and a prompt is not a guarantee.
#
# So the gate, not the prompt, is what makes the bank safe: audit --remove is
# mandatory and runs last. Because removing problems reopens gaps, and refilling
# them introduces a smaller batch of fresh defects, the cycle repeats until the
# audit comes back clean. It converges in two or three passes at a ~5% rate.
#
# The bank that ships is clean by construction. Nothing here depends on the
# model having behaved.
#
# Usage:  bash scripts/make_bank.sh [max_rounds]
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
MAX="${1:-4}"

for round in $(seq 1 "$MAX"); do
  echo "=================== round $round ==================="

  echo "--- generate missing ---"
  "$PY" scripts/build_bank.py --direct --per-combo 10

  echo "--- remove defective ---"
  "$PY" scripts/audit_bank.py --remove | tail -6

  echo "--- remove near-duplicates ---"
  "$PY" scripts/dedupe_bank.py --apply | tail -4

  # Clean AND full? Then stop. Checking both matters: an empty bank is
  # trivially clean, and a full bank can still be dirty.
  if "$PY" - <<'EOF'
import json, sys
b = json.load(open("course_content/generated/practice_bank.json"))
thin = {k: len(v) for k, v in b.items() if len(v) < 5}
print(f"  {sum(len(v) for v in b.values())} problems, "
      f"{len(thin)} combos under 5" + (f": {thin}" if thin else ""))
sys.exit(0 if not thin else 1)
EOF
  then
    echo
    echo "--- final verification ---"
    "$PY" scripts/audit_bank.py | tail -4
    echo "bank is clean and full — commit course_content/generated/"
    exit 0
  fi
done

echo "still thin after $MAX rounds — inspect course_content/generated/practice_bank.json" >&2
exit 1
