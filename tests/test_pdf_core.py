"""Unit tests for pdf_core parsing logic."""

from pathlib import Path

import pymupdf
import pytest

from lib.pdf_core import (
    extract_metadata, detect_headings, extract_blocks,
    assign_sections, build_manifest,
    extract_tables, extract_figures,
    parse_full, fetch_blocks_by_id, fetch_section,
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


class TestFetchBlocksById:
    def test_fetches_specific_blocks(self, simple_pdf):
        full = parse_full(simple_pdf)
        all_ids = [b["id"] for b in full["blocks"]]
        target_ids = all_ids[:2]
        fetched = fetch_blocks_by_id(full, target_ids)
        assert len(fetched) == 2
        assert all("content" in b for b in fetched)

    def test_returns_empty_for_unknown_ids(self, simple_pdf):
        full = parse_full(simple_pdf)
        fetched = fetch_blocks_by_id(full, ["nonexistent:p99:b1"])
        assert fetched == []


class TestFetchSection:
    def test_fetches_all_blocks_in_section(self, simple_pdf):
        full = parse_full(simple_pdf)
        sections = {b.get("section") for b in full["blocks"] if b.get("section")}
        if sections:
            section_id = next(iter(sections))
            result = fetch_section(full, section_id)
            assert len(result) >= 1
            assert all(b["section"] == section_id for b in result)

    def test_returns_empty_for_unknown_section(self, simple_pdf):
        full = parse_full(simple_pdf)
        result = fetch_section(full, "s999")
        assert result == []


class TestEdgeCases:
    def test_image_only_pdf(self, tmp_path):
        """PDF with only an image and no text — should flag image_only."""
        path = tmp_path / "image_only.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 400, 300), 1)
        pix.set_rect(pix.irect, (200, 200, 200, 255))
        page.insert_image(pymupdf.Rect(50, 50, 450, 350), pixmap=pix)
        doc.save(str(path))
        doc.close()

        manifest = build_manifest(path)
        assert manifest["metadata"]["page_count"] == 1
        assert manifest["image_only"] is True
        text_blocks = [b for b in manifest["blocks"] if b["type"] in ("paragraph", "heading")]
        assert len(text_blocks) == 0

    def test_empty_pdf(self, tmp_path):
        """PDF with no content at all."""
        path = tmp_path / "empty.pdf"
        doc = pymupdf.open()
        doc.new_page()
        doc.save(str(path))
        doc.close()

        manifest = build_manifest(path)
        assert manifest["metadata"]["page_count"] == 1
        assert manifest["blocks"] == []
        assert manifest["image_only"] is False
        assert manifest["stats"]["total_blocks"] == 0

    def test_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(Exception):
            build_manifest(tmp_path / "doesnt_exist.pdf")

    def test_multi_font_pdf_heading_detection(self, tmp_path):
        """PDF with many font sizes — heading detection should use body size heuristic."""
        path = tmp_path / "multi_font.pdf"
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 60), "Main Title", fontsize=16)
        page.insert_text((72, 100), "Body text paragraph one.", fontsize=11)
        page.insert_text((72, 140), "1. Footnote reference text.", fontsize=8)
        page.insert_text((72, 160), "Figure 1 — Caption text.", fontsize=9)
        page.insert_text((72, 200), "Second Section", fontsize=16)
        page.insert_text((72, 240), "More body text here.", fontsize=11)
        doc.save(str(path))
        doc.close()

        headings = detect_headings(path)
        heading_texts = [h["text"] for h in headings]
        assert "Main Title" in heading_texts
        assert "Second Section" in heading_texts
        assert not any("Footnote" in t for t in heading_texts)
        assert not any("Caption" in t for t in heading_texts)
