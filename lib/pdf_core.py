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


# ---------------------------------------------------------------------------
# Table extraction
# ---------------------------------------------------------------------------

def extract_tables(path: Path) -> list[dict]:
    """Extract tables from PDF using pymupdf's find_tables.

    Returns list of dicts with: type, page, headers, rows, bbox, word_count, y.
    """
    doc = pymupdf.open(str(path))
    tables = []

    for page_idx, page in enumerate(doc):
        page_tables = page.find_tables()
        for table in page_tables:
            df = table.extract()
            if not df or len(df) < 2:
                continue

            headers = [str(cell) if cell else "" for cell in df[0]]
            rows = [
                [str(cell) if cell else "" for cell in row]
                for row in df[1:]
            ]

            all_text = " ".join(headers + [c for r in rows for c in r])
            word_count = len(all_text.split())

            tables.append({
                "type": "table",
                "page": page_idx + 1,
                "headers": headers,
                "rows": rows,
                "bbox": list(table.bbox),
                "word_count": word_count,
                "y": round(table.bbox[1], 1),
            })

    doc.close()
    return tables


# ---------------------------------------------------------------------------
# Figure extraction
# ---------------------------------------------------------------------------

def extract_figures(path: Path, output_dir: Path) -> list[dict]:
    """Extract images from PDF and detect nearby captions.

    Saves images to output_dir. Detects captions by looking for small-font
    text below the image bbox (within 40px).

    Returns list of dicts with: type, page, path, width, height, caption, bbox, y.
    """
    doc = pymupdf.open(str(path))
    output_dir.mkdir(parents=True, exist_ok=True)
    figures = []

    for page_idx, page in enumerate(doc):
        page_images = page.get_images(full=True)

        for img_idx, img_info in enumerate(page_images):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue

            if not base_image or not base_image.get("image"):
                continue

            width = base_image.get("width", 0)
            height = base_image.get("height", 0)

            if width < 50 or height < 50:
                continue

            ext = base_image.get("ext", "png")
            img_filename = f"p{page_idx + 1}_f{img_idx}.{ext}"
            img_path = output_dir / img_filename
            img_path.write_bytes(base_image["image"])

            # Find image bbox on page for caption detection
            img_rects = page.get_image_rects(xref)
            bbox = list(img_rects[0]) if img_rects else [0, 0, width, height]

            # Detect caption: text below image (within 40px of bottom edge)
            caption = ""
            if img_rects:
                caption_rect = pymupdf.Rect(
                    bbox[0], bbox[3], bbox[2], bbox[3] + 40
                )
                caption_text = page.get_text("text", clip=caption_rect).strip()
                if caption_text:
                    caption = caption_text

            figures.append({
                "type": "figure",
                "page": page_idx + 1,
                "path": str(img_path),
                "width": width,
                "height": height,
                "ext": ext,
                "caption": caption,
                "bbox": bbox,
                "y": round(bbox[1], 1),
                "word_count": len(caption.split()) if caption else 0,
            })

    doc.close()
    return figures


# ---------------------------------------------------------------------------
# Section assignment
# ---------------------------------------------------------------------------

def assign_sections(
    blocks: list[dict],
    headings: list[dict],
    toc: list[dict],
) -> list[dict]:
    """Assign section IDs to blocks based on headings.

    Each block gets a 'section' field (e.g., 's1', 's2.1') based on
    the most recent heading above it. Blocks before any heading get section=None.

    If no headings exist, all blocks get section=None.
    """
    if not headings:
        for b in blocks:
            b["section"] = None
        return blocks

    # Build section labels from TOC hierarchy if available
    section_labels = {}
    if toc:
        level_counters: list[int] = []
        for entry in toc:
            level = entry["level"]
            while len(level_counters) < level:
                level_counters.append(0)
            level_counters = level_counters[:level]
            level_counters[-1] += 1
            label = "s" + ".".join(str(c) for c in level_counters)
            # Match TOC entry to heading by text similarity
            for h in headings:
                if entry["title"].strip() in h["text"] or h["text"] in entry["title"].strip():
                    section_labels[(h["page"], h["y"])] = label
                    break

    # Fallback: label headings sequentially if TOC matching didn't cover all
    fallback_counter = 0
    for h in headings:
        key = (h["page"], h["y"])
        if key not in section_labels:
            fallback_counter += 1
            section_labels[key] = f"s{fallback_counter}"

    # Sort headings by position
    sorted_headings = sorted(headings, key=lambda h: (h["page"], h["y"]))

    # Assign sections to blocks
    for block in blocks:
        block["section"] = None
        for h in reversed(sorted_headings):
            if (block["page"] > h["page"]) or (
                block["page"] == h["page"] and block["y"] >= h["y"]
            ):
                block["section"] = section_labels.get((h["page"], h["y"]))
                break

    return blocks


# ---------------------------------------------------------------------------
# Block ID generation
# ---------------------------------------------------------------------------

def _generate_block_id(
    block: dict, page_counters: dict, sections_detected: bool,
    ref_label: str = "",
) -> str:
    """Generate a referenciable block ID.

    Format with ref + sections: ref1:p{page}:s{section}:b{n}
    Format with ref, no sections: ref1:p{page}:b{n}
    Format without ref: p{page}:s{section}:b{n} or p{page}:b{n}
    """
    page = block["page"]
    section = block.get("section")

    key = (page, section) if sections_detected else (page,)
    page_counters[key] = page_counters.get(key, 0) + 1
    n = page_counters[key]

    type_prefix = {"table": "t", "figure": "f"}.get(block["type"], "b")

    prefix = f"{ref_label}:" if ref_label else ""
    if sections_detected and section:
        return f"{prefix}p{page}:{section}:{type_prefix}{n}"
    return f"{prefix}p{page}:{type_prefix}{n}"


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

def build_manifest(path: Path, ref_label: str = "") -> dict:
    """Build a complete manifest of the PDF — compact index of all blocks.

    This is the primary entry point for the MANIFEST mode.

    Args:
        path: Path to the PDF file.
        ref_label: Optional reference label (e.g., "ref1") prepended to block IDs.

    Returns metadata, blocks (with IDs and previews), sections_detected flag,
    image_only flag, and stats.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    metadata = extract_metadata(path)
    blocks = extract_blocks(path)
    headings = detect_headings(path)
    blocks = assign_sections(blocks, headings, metadata["toc"])

    sections_detected = any(b.get("section") is not None for b in blocks)

    # Detect image-only PDFs (no text blocks but at least one page)
    has_text = len(blocks) > 0
    doc = pymupdf.open(str(path))
    has_images = any(page.get_images() for page in doc)
    doc.close()
    image_only = not has_text and has_images

    # Generate IDs
    page_counters: dict = {}
    for block in blocks:
        block["id"] = _generate_block_id(block, page_counters, sections_detected, ref_label)
        block["preview"] = block["content"][:80].replace("\n", " ")

    # Build stats
    type_counts: dict[str, int] = {}
    total_words = 0
    for b in blocks:
        type_counts[b["type"]] = type_counts.get(b["type"], 0) + 1
        total_words += b.get("word_count", 0)

    # Manifest block entries (compact — no full content)
    manifest_blocks = [
        {
            "id": b["id"],
            "type": b["type"],
            "page": b["page"],
            "section": b.get("section"),
            "preview": b["preview"],
            "words": b.get("word_count", 0),
        }
        for b in blocks
    ]

    return {
        "metadata": metadata,
        "blocks": manifest_blocks,
        "sections_detected": sections_detected,
        "image_only": image_only,
        "stats": {
            "total_blocks": len(blocks),
            "total_words": total_words,
            **{f"{k}s" if not k.endswith("s") else k: v for k, v in type_counts.items()},
        },
    }


# ---------------------------------------------------------------------------
# Full parse and fetch operations
# ---------------------------------------------------------------------------

def parse_full(
    path: Path, output_dir: Path | None = None, ref_label: str = "",
) -> dict:
    """Parse PDF completely — all blocks with full content, sections, and IDs.

    This is the internal full parse used by BLOCKS and SECTION modes.
    Unlike build_manifest, blocks here retain their full content.

    Args:
        path: Path to the PDF file.
        output_dir: Optional directory for extracted images.
        ref_label: Optional reference label prepended to block IDs.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    metadata = extract_metadata(path)
    text_blocks = extract_blocks(path)
    headings = detect_headings(path)
    text_blocks = assign_sections(text_blocks, headings, metadata["toc"])

    tables = extract_tables(path)
    figures = extract_figures(path, output_dir) if output_dir else []

    # Assign sections to tables and figures
    tables = assign_sections(tables, headings, metadata["toc"])
    figures = assign_sections(figures, headings, metadata["toc"])

    # Merge all blocks and sort by page + y position
    all_blocks = text_blocks + tables + figures
    all_blocks.sort(key=lambda b: (b["page"], b.get("y", 0)))

    sections_detected = any(b.get("section") is not None for b in all_blocks)

    # Generate IDs
    page_counters: dict = {}
    for block in all_blocks:
        block["id"] = _generate_block_id(block, page_counters, sections_detected, ref_label)

    return {
        "metadata": metadata,
        "blocks": all_blocks,
        "sections_detected": sections_detected,
    }


def fetch_blocks_by_id(full_parse: dict, block_ids: list[str]) -> list[dict]:
    """Fetch specific blocks by their IDs from a full parse result.

    Returns list of blocks with full content, in the order requested.
    """
    id_to_block = {b["id"]: b for b in full_parse["blocks"]}
    return [id_to_block[bid] for bid in block_ids if bid in id_to_block]


def fetch_section(full_parse: dict, section_id: str) -> list[dict]:
    """Fetch all blocks belonging to a specific section.

    Returns list of blocks with full content, in document order.
    """
    return [b for b in full_parse["blocks"] if b.get("section") == section_id]
