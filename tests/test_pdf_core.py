"""Unit tests for pdf_core parsing logic."""

from pathlib import Path

import pymupdf
import pytest

from lib.pdf_core import extract_metadata, detect_headings, extract_blocks


class TestExtractMetadata:
    def test_returns_page_count(self, simple_pdf):
        meta = extract_metadata(simple_pdf)
        assert meta["page_count"] == 2

    def test_returns_toc_entries(self, simple_pdf):
        meta = extract_metadata(simple_pdf)
        assert len(meta["toc"]) == 2
        assert meta["toc"][0]["title"] == "1. Introduction"
        assert meta["toc"][0]["page"] == 1
        assert meta["toc"][1]["title"] == "2. Results"

    def test_empty_toc_when_missing(self, no_toc_pdf):
        meta = extract_metadata(no_toc_pdf)
        assert meta["toc"] == []


class TestDetectHeadings:
    def test_detects_headings_by_font_size(self, simple_pdf):
        headings = detect_headings(simple_pdf)
        titles = [h["text"] for h in headings]
        assert "1. Introduction" in titles
        assert "2. Results" in titles

    def test_detects_headings_without_toc(self, no_toc_pdf):
        headings = detect_headings(no_toc_pdf)
        titles = [h["text"] for h in headings]
        assert "Background" in titles
        assert "Methods" in titles

    def test_no_headings_in_uniform_font(self, uniform_font_pdf):
        headings = detect_headings(uniform_font_pdf)
        assert headings == []

    def test_heading_has_page_number(self, simple_pdf):
        headings = detect_headings(simple_pdf)
        assert headings[0]["page"] == 1
        assert headings[1]["page"] == 2


class TestExtractBlocks:
    def test_returns_blocks_with_types(self, simple_pdf):
        blocks = extract_blocks(simple_pdf)
        types = {b["type"] for b in blocks}
        assert "heading" in types
        assert "paragraph" in types

    def test_blocks_have_page_numbers(self, simple_pdf):
        blocks = extract_blocks(simple_pdf)
        assert all("page" in b for b in blocks)

    def test_blocks_have_content(self, simple_pdf):
        blocks = extract_blocks(simple_pdf)
        paragraphs = [b for b in blocks if b["type"] == "paragraph"]
        assert len(paragraphs) >= 2
        assert any("first paragraph" in b["content"].lower() for b in paragraphs)

    def test_detects_list_items(self, simple_pdf):
        blocks = extract_blocks(simple_pdf)
        lists = [b for b in blocks if b["type"] == "list"]
        assert len(lists) >= 1
        # List block should contain the bullet items
        assert any("Finding one" in b["content"] for b in lists)

    def test_uniform_font_all_paragraphs(self, uniform_font_pdf):
        blocks = extract_blocks(uniform_font_pdf)
        assert all(b["type"] == "paragraph" for b in blocks)
