"""Compress the past CA papers into a marking-standard digest.

The grader does not need 14 complete past papers in its context. What it needs
is what those papers *encode*: how marks are allocated, how much working earns
full credit, which sub-topics recur, and the house phrasing. That is a small
document, and the full papers are an expensive way to carry it.

Measured: the CAs add ~80K tokens to the grader's prefix, taking it from 99.5K
to 179.5K. Every cold cache write pays 2x input price on all of it, so those
80K tokens cost about $0.80 per cold round on Opus 5 — roughly $440 across a
16-week term. A digest of ~8K tokens keeps the marking standard at a tenth of
the size.

This is a one-off run per CA revision. Output goes to ca_digest.txt, which
corpus.py prefers over ca_papers.txt when present.

Usage:
    python scripts/build_ca_digest.py
    python scripts/build_ca_digest.py --keep-full   # write digest but don't switch
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import anthropic
from dotenv import load_dotenv

load_dotenv()

CONTENT = Path(__file__).resolve().parent.parent / "course_content"
SRC = CONTENT / "ca_papers.txt"
OUT = CONTENT / "ca_digest.txt"
MODEL = "claude-opus-5"

INSTRUCTION = """\
Below are the past continuous-assessment papers for MS1016 Thermodynamics of
Materials, with solutions, spanning several years.

Produce a **marking-standard digest** for an automated grader that must decide
whether a student's submitted working would earn full marks in THIS course. The
grader will see your digest instead of the papers themselves, so it has to carry
everything about the examining style that the papers encode.

Cover, concisely and concretely:

1. **Structure** — how many questions, of what kind (short answer, MCQ,
   multi-part), typical mark totals, and time allowed.
2. **Mark allocation** — how marks are distributed within a question. What
   earns method marks versus answer marks. Whether a correct final answer with
   no working scores, and whether a wrong final answer with sound method does.
3. **Expected working depth** — what a full-credit answer actually looks like
   here. Does it state the law being applied? Substitute values explicitly?
   Carry units through? Quote to how many significant figures?
4. **Recurring topics** — which concepts appear year after year, and in what
   form. Note anything that appears in nearly every sitting.
5. **House conventions** — sign conventions, symbols, notation, and phrasing
   this course uses, especially anywhere it differs from a generic textbook.
6. **Common student errors** the solutions explicitly call out or correct.

Write it as structured markdown a grader can apply directly. Be specific and
quantitative wherever the papers let you be — "part (a) is typically 3 marks,
of which 2 are for stating and substituting into the Clapeyron equation" is
useful; "marks are given for correct working" is not.

Do NOT reproduce whole questions or solutions. This is a description of the
standard, not a copy of the papers.

Aim for roughly 2,500-3,500 words.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-full", action="store_true",
                    help="write the digest but leave corpus.py using the full papers")
    args = ap.parse_args()

    if not SRC.exists():
        sys.exit(f"{SRC.name} not found — run scripts/extract_ca.py first")
    papers = SRC.read_text(encoding="utf-8")

    client = anthropic.Anthropic()
    before = client.messages.count_tokens(
        model=MODEL, messages=[{"role": "user", "content": papers}]).input_tokens
    print(f"source: {SRC.name}  {len(papers):,} chars  {before:,} tokens")
    print("generating digest (one Opus 5 call, ~1-2 min)...", flush=True)

    resp = client.messages.create(
        model=MODEL, max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": INSTRUCTION + "\n\n" + papers}],
    )
    digest = next((b.text for b in resp.content if b.type == "text"), "")
    if len(digest) < 2000:
        sys.exit(f"digest suspiciously short ({len(digest)} chars) — not writing")

    OUT.write_text(digest, encoding="utf-8")
    after = client.messages.count_tokens(
        model=MODEL, messages=[{"role": "user", "content": digest}]).input_tokens

    u = resp.usage
    cost = (u.input_tokens * 5 + u.output_tokens * 25) / 1e6
    print(f"\nwrote {OUT.name}  {len(digest):,} chars  {after:,} tokens")
    print(f"  {before:,} -> {after:,} tokens  ({(1 - after/before)*100:.0f}% smaller)")
    print(f"  saves ~${(before - after) * 2 * 5 / 1e6:.2f} on every cold Opus 5 cache write")
    print(f"  this run cost ${cost:.2f}")
    if args.keep_full:
        print("\n--keep-full: corpus.py still using the full papers. "
              "Review ca_digest.txt, then remove the flag.")
    else:
        print("\ncorpus.py prefers ca_digest.txt automatically when it exists.")
        print("Read it before deploying — it is now the grader's only source "
              "for what earns marks.")


if __name__ == "__main__":
    main()
