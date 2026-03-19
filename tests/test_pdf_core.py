"""Unit tests for pdf_core parsing logic."""

from pathlib import Path

import pymupdf
import pytest

from lib.pdf_core import (
    extract_metadata, detect_headings, extract_blocks,
    assign_sections, build_manifest,
    extract_tables, extract_figures,
)


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


class TestAssignSections:
    def test_assigns_sections_from_headings(self, simple_pdf):
        blocks = extract_blocks(simple_pdf)
        headings = detect_headings(simple_pdf)
        toc = extract_metadata(simple_pdf)["toc"]
        sectioned = assign_sections(blocks, headings, toc)

        # Blocks after "1. Introduction" heading should be in section "s1"
        intro_blocks = [b for b in sectioned if b.get("section") == "s1"]
        assert len(intro_blocks) >= 1

    def test_sections_detected_flag_true(self, simple_pdf):
        blocks = extract_blocks(simple_pdf)
        headings = detect_headings(simple_pdf)
        toc = extract_metadata(simple_pdf)["toc"]
        sectioned = assign_sections(blocks, headings, toc)
        # At least one block has a section
        assert any(b.get("section") for b in sectioned)

    def test_no_sections_for_uniform_font(self, uniform_font_pdf):
        blocks = extract_blocks(uniform_font_pdf)
        headings = detect_headings(uniform_font_pdf)
        toc = extract_metadata(uniform_font_pdf)["toc"]
        sectioned = assign_sections(blocks, headings, toc)
        assert all(b.get("section") is None for b in sectioned)


class TestBuildManifest:
    def test_manifest_has_metadata(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        assert manifest["metadata"]["page_count"] == 2

    def test_manifest_has_blocks(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        assert len(manifest["blocks"]) > 0

    def test_blocks_have_ids(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        assert all("id" in b for b in manifest["blocks"])

    def test_block_ids_include_ref_prefix(self, simple_pdf):
        manifest = build_manifest(simple_pdf, ref_label="ref1")
        for b in manifest["blocks"]:
            assert b["id"].startswith("ref1:")

    def test_block_ids_no_prefix_when_no_label(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        for b in manifest["blocks"]:
            assert not b["id"].startswith("ref")

    def test_block_ids_include_section_when_detected(self, simple_pdf):
        manifest = build_manifest(simple_pdf, ref_label="ref1")
        ids_with_section = [b["id"] for b in manifest["blocks"] if ":s" in b["id"]]
        assert len(ids_with_section) > 0

    def test_block_ids_fallback_without_section(self, uniform_font_pdf):
        manifest = build_manifest(uniform_font_pdf, ref_label="ref1")
        for b in manifest["blocks"]:
            # Has ref prefix but no section
            assert b["id"].startswith("ref1:p")
            assert ":s" not in b["id"]

    def test_sections_detected_flag(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        assert manifest["sections_detected"] is True

    def test_sections_not_detected_flag(self, uniform_font_pdf):
        manifest = build_manifest(uniform_font_pdf)
        assert manifest["sections_detected"] is False

    def test_image_only_flag_false(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        assert manifest["image_only"] is False

    def test_manifest_has_stats(self, simple_pdf):
        manifest = build_manifest(simple_pdf)
        stats = manifest["stats"]
        assert "total_blocks" in stats
        assert "total_words" in stats
        assert stats["total_blocks"] > 0


class TestExtractTables:
    def test_finds_tables(self, pdf_with_table):
        tables = extract_tables(pdf_with_table)
        assert len(tables) >= 1

    def test_table_has_headers_and_rows(self, pdf_with_table):
        tables = extract_tables(pdf_with_table)
        t = tables[0]
        assert "headers" in t
        assert "rows" in t
        assert len(t["rows"]) >= 2

    def test_table_has_page(self, pdf_with_table):
        tables = extract_tables(pdf_with_table)
        assert tables[0]["page"] == 1

    def test_no_tables_in_simple_pdf(self, simple_pdf):
        tables = extract_tables(simple_pdf)
        assert tables == []


class TestExtractFigures:
    def test_finds_images(self, pdf_with_image, tmp_output):
        figures = extract_figures(pdf_with_image, tmp_output)
        assert len(figures) >= 1

    def test_figure_has_path(self, pdf_with_image, tmp_output):
        figures = extract_figures(pdf_with_image, tmp_output)
        fig = figures[0]
        assert "path" in fig
        assert Path(fig["path"]).exists()

    def test_figure_has_dimensions(self, pdf_with_image, tmp_output):
        figures = extract_figures(pdf_with_image, tmp_output)
        fig = figures[0]
        assert fig["width"] >= 50
        assert fig["height"] >= 50

    def test_figure_caption_detection(self, pdf_with_image, tmp_output):
        figures = extract_figures(pdf_with_image, tmp_output)
        fig = figures[0]
        assert "caption" in fig

    def test_no_figures_in_simple_pdf(self, simple_pdf, tmp_output):
        figures = extract_figures(simple_pdf, tmp_output)
        assert figures == []
