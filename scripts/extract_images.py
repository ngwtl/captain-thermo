"""Extract embedded images from a lecture PDF into a per-lecture folder.

Usage:
    python extract_images.py <source.pdf> <output_dir> [--prefix NAME]

Output filenames are `{prefix}_p{page:02d}_{index}.{ext}` so you can cross-
reference to the source page easily. Skips images smaller than 10KB to avoid
pulling logo-sized decorations.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import fitz  # PyMuPDF


MIN_BYTES = 10_000  # skip tiny decorative images


def extract(pdf_path: Path, out_dir: Path, prefix: str) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    saved = 0
    for page_num, page in enumerate(doc, start=1):
        for img_idx, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            try:
                base = doc.extract_image(xref)
            except Exception as e:
                print(f"  p{page_num} img {img_idx}: failed ({e})")
                continue
            data = base["image"]
            if len(data) < MIN_BYTES:
                continue
            ext = base["ext"]
            name = f"{prefix}_p{page_num:02d}_{img_idx}.{ext}"
            (out_dir / name).write_bytes(data)
            saved += 1
            print(f"  saved {name}  ({len(data)//1024} KB, {ext})")
    doc.close()
    return saved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--prefix", default="img")
    args = ap.parse_args()

    n = extract(args.pdf, args.out_dir, args.prefix)
    print(f"\nExtracted {n} images -> {args.out_dir}")


if __name__ == "__main__":
    main()
