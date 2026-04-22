"""Load and concatenate all course-material text files into a single cached corpus."""
from pathlib import Path

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


CORPUS = load_corpus()
