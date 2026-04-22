"""Dump the text content of a PDF page-by-page to a UTF-8 file."""
import sys
from pathlib import Path
import fitz

pdf_path = Path(sys.argv[1])
out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else pdf_path.with_suffix(".txt")

doc = fitz.open(pdf_path)
lines = [f"Pages: {len(doc)}"]
for i, page in enumerate(doc, 1):
    lines.append(f"\n===== PAGE {i} =====")
    lines.append(page.get_text())

out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out_path} ({len(doc)} pages)")
