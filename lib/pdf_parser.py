"""CLI entry point for PDF parser — manifest/blocks/section modes.

Usage:
    python -m lib.pdf_parser manifest <pdf_path>
    python -m lib.pdf_parser blocks <pdf_path> --ids "id1,id2,id3"
    python -m lib.pdf_parser section <pdf_path> --id "s1"
"""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

from lib.pdf_core import build_manifest, fetch_blocks_by_id, fetch_section, parse_full


def _json_default(obj):
    """Handle non-serializable types."""
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _clean_block(b: dict) -> dict:
    """Build a clean output dict for a block, adding type-specific fields."""
    entry = {
        "id": b["id"],
        "type": b["type"],
        "page": b["page"],
        "section": b.get("section"),
        "content": b.get("content", ""),
        "word_count": b.get("word_count", 0),
    }
    if b["type"] == "table":
        entry["headers"] = b.get("headers", [])
        entry["rows"] = b.get("rows", [])
    if b["type"] == "figure":
        entry["path"] = b.get("path", "")
        entry["caption"] = b.get("caption", "")
        entry["width"] = b.get("width", 0)
        entry["height"] = b.get("height", 0)
    return entry


def _suppress_library_noise(func):
    """Suppress stdout noise from pymupdf during parsing operations."""
    def wrapper(*args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return func(*args, **kwargs)
    return wrapper


def cmd_manifest(args):
    """Output compact manifest of all blocks (no full content)."""
    ref_label = args.ref or ""
    manifest = _suppress_library_noise(build_manifest)(Path(args.pdf), ref_label=ref_label)
    json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2, default=_json_default)


def cmd_blocks(args):
    """Output full content of specific blocks by ID."""
    output_dir = Path(args.output_dir) if args.output_dir else None
    ref_label = args.ref or ""
    full = _suppress_library_noise(parse_full)(Path(args.pdf), output_dir=output_dir, ref_label=ref_label)
    block_ids = [bid.strip() for bid in args.ids.split(",")]
    blocks = fetch_blocks_by_id(full, block_ids)
    json.dump(
        {"blocks": [_clean_block(b) for b in blocks]},
        sys.stdout, ensure_ascii=False, indent=2, default=_json_default,
    )


def cmd_section(args):
    """Output all blocks in a specific section."""
    output_dir = Path(args.output_dir) if args.output_dir else None
    ref_label = args.ref or ""
    full = _suppress_library_noise(parse_full)(Path(args.pdf), output_dir=output_dir, ref_label=ref_label)
    blocks = fetch_section(full, args.id)
    json.dump(
        {"blocks": [_clean_block(b) for b in blocks]},
        sys.stdout, ensure_ascii=False, indent=2, default=_json_default,
    )


def main():
    parser = argparse.ArgumentParser(description="Docforge PDF Parser")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # manifest mode
    p_manifest = subparsers.add_parser("manifest", help="Compact index of all blocks")
    p_manifest.add_argument("pdf", help="Path to PDF file")
    p_manifest.add_argument("--ref", help="Reference label prefix for block IDs (e.g., ref1)")

    # blocks mode
    p_blocks = subparsers.add_parser("blocks", help="Full content of specific blocks")
    p_blocks.add_argument("pdf", help="Path to PDF file")
    p_blocks.add_argument("--ids", required=True, help="Comma-separated block IDs")
    p_blocks.add_argument("--ref", help="Reference label prefix for block IDs (e.g., ref1)")
    p_blocks.add_argument("--output-dir", help="Directory for extracted images")

    # section mode
    p_section = subparsers.add_parser("section", help="All blocks in a section")
    p_section.add_argument("pdf", help="Path to PDF file")
    p_section.add_argument("--id", required=True, help="Section ID (e.g., s1, s2.3)")
    p_section.add_argument("--ref", help="Reference label prefix for block IDs (e.g., ref1)")
    p_section.add_argument("--output-dir", help="Directory for extracted images")

    args = parser.parse_args()

    if args.mode == "manifest":
        cmd_manifest(args)
    elif args.mode == "blocks":
        cmd_blocks(args)
    elif args.mode == "section":
        cmd_section(args)


if __name__ == "__main__":
    main()
