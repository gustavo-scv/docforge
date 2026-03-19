"""Core PDF parsing — block-level extraction with heading detection and section mapping.

Uses pymupdf (PyMuPDF/fitz) for structured text extraction, table detection,
and image extraction. Produces indexed blocks with referenciable IDs.
"""

import re
from pathlib import Path

import pymupdf


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def extract_metadata(path: Path) -> dict:
    """Extract PDF metadata and table of contents.

    Returns dict with: title, author, page_count, toc.
    """
    doc = pymupdf.open(str(path))
    meta = doc.metadata or {}

    toc_raw = doc.get_toc()
    toc = [
        {"level": entry[0], "title": entry[1], "page": entry[2]}
        for entry in toc_raw
    ]

    result = {
        "title": meta.get("title", "") or "",
        "author": meta.get("author", "") or "",
        "page_count": len(doc),
        "toc": toc,
    }

    doc.close()
    return result


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

def _collect_spans(doc: pymupdf.Document) -> list[dict]:
    """Collect all text spans with font size and position from all pages."""
    spans = []
    for page_idx, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:  # skip image blocks
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    spans.append({
                        "text": text,
                        "size": round(span["size"], 1),
                        "page": page_idx + 1,
                        "y": round(span["bbox"][1], 1),
                        "bbox": span["bbox"],
                    })
    return spans


def _median(values: list[float]) -> float:
    """Calculate median of a list of floats."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _body_size(sizes: list[float]) -> float:
    """Estimate body text font size as the most frequent size (smallest if tied)."""
    counts: dict[float, int] = {}
    for s in sizes:
        counts[s] = counts.get(s, 0) + 1
    max_count = max(counts.values())
    return min(s for s, c in counts.items() if c == max_count)


def detect_headings(path: Path) -> list[dict]:
    """Detect headings by font size analysis.

    Algorithm:
    1. Collect all text spans with font sizes
    2. Estimate body text size (most frequent font size, smallest if tied)
    3. Spans with font size > body_size * 1.2 = heading candidates
    4. Return heading candidates sorted by page then y-position

    Returns list of dicts: [{"text": "...", "page": 1, "size": 18.0, "y": 72.0}, ...]
    Returns empty list if no headings are detectable (uniform font).
    """
    doc = pymupdf.open(str(path))
    spans = _collect_spans(doc)
    doc.close()

    if not spans:
        return []

    sizes = [s["size"] for s in spans]
    body = _body_size(sizes)

    if body == 0:
        return []

    threshold = body * 1.2

    # Collect heading candidates: spans significantly larger than body text
    headings = []
    for span in spans:
        if span["size"] > threshold:
            headings.append({
                "text": span["text"],
                "page": span["page"],
                "size": span["size"],
                "y": span["y"],
            })

    # Deduplicate: merge spans on same line (same page + similar y)
    merged = []
    for h in headings:
        if merged and merged[-1]["page"] == h["page"] and abs(merged[-1]["y"] - h["y"]) < 2:
            merged[-1]["text"] += " " + h["text"]
        else:
            merged.append(dict(h))

    return merged


# ---------------------------------------------------------------------------
# Block extraction
# ---------------------------------------------------------------------------

_LIST_PATTERN = re.compile(r"^[\s]*([-•●◦▪*]|\d+[.)]\s|[a-zA-Z][.)]\s)")


def _is_list_line(text: str) -> bool:
    """Check if a line looks like a list item."""
    return bool(_LIST_PATTERN.match(text))


def extract_blocks(path: Path) -> list[dict]:
    """Extract all content blocks from a PDF with type classification.

    Block types: heading, paragraph, list.
    (Tables and figures are handled by separate functions.)

    Returns list of dicts with: type, content, page, y, word_count.
    """
    doc = pymupdf.open(str(path))
    headings = detect_headings(path)
    heading_positions = {(h["page"], h["y"]) for h in headings}

    all_blocks = []

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        dict_blocks = page.get_text("dict")["blocks"]

        for block in dict_blocks:
            if block["type"] != 0:  # skip image blocks (handled by extract_figures)
                continue

            # Collect all text from this block
            lines = []
            block_y = round(block["bbox"][1], 1)
            max_size = 0.0

            for line in block["lines"]:
                line_text_parts = []
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        line_text_parts.append(text)
                        max_size = max(max_size, span["size"])
                if line_text_parts:
                    lines.append(" ".join(line_text_parts))

            if not lines:
                continue

            full_text = "\n".join(lines)

            # Classify block type
            is_heading = any(
                page_num == p and abs(block_y - y) < 5
                for p, y in heading_positions
            )

            if is_heading:
                block_type = "heading"
            elif all(_is_list_line(line) for line in lines if line.strip()):
                block_type = "list"
            else:
                block_type = "paragraph"

            all_blocks.append({
                "type": block_type,
                "content": full_text,
                "page": page_num,
                "y": block_y,
                "word_count": len(full_text.split()),
            })

    doc.close()
    return all_blocks
