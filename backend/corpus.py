"""Load and concatenate all course-material text files into a single cached corpus."""
import os
from pathlib import Path

# Tutorial solution files restate each problem verbatim before working it, so
# shipping the problem sheets too duplicates ~5,400 tokens on every cache write.
INCLUDE_PROBLEM_SHEETS = os.getenv("INCLUDE_PROBLEM_SHEETS", "false").lower() in ("1", "true", "yes")

CONTENT_DIR = Path(__file__).resolve().parent.parent / "course_content"

TOPIC_INDEX = {
    "L0": "Introduction to Thermodynamics",
    "L1": "First Law",
    "L2": "Second Law",
    "L3": "Property Relationships, Free Energy, Equilibrium",
    "L4": "Equilibrium in Single-Component Systems",
    "L5": "Solid Solutions",
    "L6": "Gibbs Phase Rule and Phase Diagrams",
    "L7": "Chemical Equilibrium",
}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


CONSOLIDATED_DIR = CONTENT_DIR / "consolidated"


def _load_consolidated_notes() -> str:
    """Load the clean consolidated lecture notes (L0.md .. L7.md) if present.

    These are the hand-curated notes — preferred over the pdftotext-mangled
    notes_complete.txt. Returns empty string if the folder doesn't exist.
    """
    if not CONSOLIDATED_DIR.exists():
        return ""
    parts: list[str] = []
    for i in range(8):
        path = CONSOLIDATED_DIR / f"L{i}.md"
        if path.exists():
            parts.append("\n" + "=" * 72)
            parts.append(f"LECTURE L{i} — consolidated notes")
            parts.append("=" * 72)
            parts.append(_read(path))
    return "\n".join(parts)


def load_corpus() -> str:
    """Concatenate notes + tutorial solutions + problem sheets into one LLM-ready blob.

    Prefers the consolidated markdown notes in consolidated/ (clean, structured,
    with correct math) over the pdftotext-mangled notes_complete.txt. Falls back
    to the latter if consolidated notes aren't present yet.
    Order matters for prompt caching: keep stable (notes) first, then tutorials.
    """
    parts: list[str] = []

    consolidated = _load_consolidated_notes()
    if consolidated:
        parts.append("=" * 72)
        parts.append("LECTURE NOTES — MS1016 THERMODYNAMICS (consolidated, L0–L7)")
        parts.append("=" * 72)
        parts.append(consolidated)
    else:
        notes = _read(CONTENT_DIR / "notes_complete.txt")
        if notes:
            parts.append("=" * 72)
            parts.append("LECTURE NOTES — MS1016 THERMODYNAMICS (pdftotext fallback)")
            parts.append("=" * 72)
            parts.append(notes)

    for i in range(1, 9):
        for stem in (
            f"Solution_Tutorial_{i}",
            f"Solution_Tutorial_{i}updated",
        ):
            path = CONTENT_DIR / f"{stem}.txt"
            if path.exists():
                parts.append("\n" + "=" * 72)
                parts.append(f"TUTORIAL {i} — WORKED SOLUTIONS")
                parts.append("=" * 72)
                parts.append(_read(path))
                break

    # Problem sheets are omitted by default: the solution files restate each
    # problem verbatim before working it, so including both duplicates ~5,400
    # tokens on every cache write for no added information. Verified by
    # comparing Tutorial 3's sheet against its solution file.
    # Set INCLUDE_PROBLEM_SHEETS=true if a sheet ever carries something its
    # solution doesn't (a syllabus note, a figure caption).
    if INCLUDE_PROBLEM_SHEETS:
        for i in range(1, 9):
            for stem in (
                f"problems_Tutorial_{i}",
                f"problems_Tutorial_{i}__Updated",
                f"problems_Tutorial_{i}__updated",
                f"problems_Tutorial_{i}updated",
            ):
                path = CONTENT_DIR / f"{stem}.txt"
                if path.exists():
                    parts.append("\n" + "=" * 72)
                    parts.append(f"TUTORIAL {i} — PROBLEM SHEET")
                    parts.append("=" * 72)
                    parts.append(_read(path))
                    break

    return "\n".join(parts)


def load_ca() -> str:
    """Past continuous assessments, extracted by scripts/extract_ca.py.

    Kept as a separate block rather than folded into CORPUS because it is not
    equally useful to every tool, and it is not free: the CAs add ~40% to the
    corpus (99K -> 139K tokens on Sonnet, 128K -> 178K on Opus 5), which lands
    on every cache write and every cached read.

    Tutorials show the *teaching* style; the CAs show the *examining* style —
    phrasing, mark allocation, how much working earns full credit, which
    sub-topics recur year on year. That is decisive for the grader, which
    otherwise has no way to know what "good enough for full marks" means in
    this course. It matters much less to the tutor, whose job is to ask the
    next question, so the tutor is not charged 40% for it by default.

    Appended last so that re-extracting CAs never invalidates the stable
    prefix ahead of it.
    """
    # Prefer the compressed digest. The full papers are ~80K tokens and the
    # grader doesn't need them — it needs what they encode: mark allocation,
    # expected working depth, house conventions. The digest is ~8K and carries
    # that, saving ~$0.80 on every cold Opus 5 cache write.
    # Falls back to the full papers if no digest has been built yet.
    digest = _read(CONTENT_DIR / "ca_digest.txt")
    if digest:
        return ("\n" + "=" * 72
                + "\nMARKING STANDARD — distilled from past CA papers 2021-2025\n"
                + "=" * 72 + "\n" + digest)

    ca = _read(CONTENT_DIR / "ca_papers.txt")
    if not ca:
        return ""
    return ("\n" + "=" * 72
            + "\nPAST CONTINUOUS ASSESSMENTS (CA1 + CA2, with solutions)\n"
            + "=" * 72 + "\n" + ca)


CORPUS = load_corpus()
CA_PAPERS = load_ca()
