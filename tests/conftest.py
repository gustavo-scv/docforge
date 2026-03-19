"""Shared test fixtures — sample PDFs created via pymupdf."""

from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def tmp_output(tmp_path):
    """Temporary output directory for extracted images."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def simple_pdf(tmp_path):
    """PDF with 2 pages, headings (larger font), body text, and a TOC."""
    path = tmp_path / "simple.pdf"
    doc = pymupdf.open()

    # Page 1: heading + 2 paragraphs
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((72, 72), "1. Introduction", fontsize=18)
    page1.insert_text((72, 110), "This is the first paragraph of the introduction. "
                       "It discusses the background of the study and sets the context "
                       "for what follows in subsequent sections.", fontsize=11)
    page1.insert_text((72, 170), "The second paragraph provides additional detail "
                       "about methodology and approach used in this work.", fontsize=11)

    # Page 2: heading + paragraph + list-like content
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((72, 72), "2. Results", fontsize=18)
    page2.insert_text((72, 110), "The results demonstrate significant improvement "
                       "across all measured endpoints.", fontsize=11)
    page2.insert_text((72, 150), "- Finding one: 42% reduction", fontsize=11)
    page2.insert_text((72, 170), "- Finding two: p < 0.001", fontsize=11)
    page2.insert_text((72, 190), "- Finding three: NNT = 25", fontsize=11)

    # Add TOC
    doc.set_toc([
        [1, "1. Introduction", 1],
        [1, "2. Results", 2],
    ])

    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def no_toc_pdf(tmp_path):
    """PDF with headings detectable by font size but no TOC."""
    path = tmp_path / "no_toc.pdf"
    doc = pymupdf.open()

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "Background", fontsize=16)
    page.insert_text((72, 110), "Some body text about the background.", fontsize=11)
    page.insert_text((72, 160), "Methods", fontsize=16)
    page.insert_text((72, 198), "Description of methods used.", fontsize=11)

    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def uniform_font_pdf(tmp_path):
    """PDF with uniform font size — no heading detection possible."""
    path = tmp_path / "uniform.pdf"
    doc = pymupdf.open()

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "All text is the same size here.", fontsize=11)
    page.insert_text((72, 100), "There are no headings to detect.", fontsize=11)
    page.insert_text((72, 128), "Everything is body text.", fontsize=11)

    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def pdf_with_table(tmp_path):
    """PDF containing a table (drawn with lines for find_tables detection)."""
    path = tmp_path / "with_table.pdf"
    doc = pymupdf.open()

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 50), "Table of Results", fontsize=16)

    # Draw a simple 3x2 table using lines
    x0, y0 = 72, 80
    col_w = 150
    row_h = 25
    cols = 3
    rows = 3

    # Horizontal lines
    for r in range(rows + 1):
        y = y0 + r * row_h
        page.draw_line((x0, y), (x0 + cols * col_w, y))

    # Vertical lines
    for c in range(cols + 1):
        x = x0 + c * col_w
        page.draw_line((x, y0), (x, y0 + rows * row_h))

    # Cell text
    cells = [
        ["Endpoint", "Treatment", "Control"],
        ["Mortality", "4.2%", "8.1%"],
        ["Readmission", "12.0%", "18.5%"],
    ]
    for r, row in enumerate(cells):
        for c, text in enumerate(row):
            page.insert_text(
                (x0 + c * col_w + 5, y0 + r * row_h + 18),
                text, fontsize=10,
            )

    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def pdf_with_image(tmp_path):
    """PDF containing an embedded image."""
    path = tmp_path / "with_image.pdf"
    doc = pymupdf.open()

    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 50), "Figure Section", fontsize=16)

    # Create a small PNG in memory and insert it
    img_doc = pymupdf.open()
    img_page = img_doc.new_page(width=200, height=150)
    img_page.draw_rect(pymupdf.Rect(10, 10, 190, 140), color=(0, 0, 1), fill=(0.8, 0.8, 1))
    img_page.insert_text((50, 80), "Sample Image", fontsize=14)
    pix = img_page.get_pixmap()
    img_bytes = pix.tobytes("png")
    img_doc.close()

    rect = pymupdf.Rect(72, 80, 272, 230)
    page.insert_image(rect, stream=img_bytes)
    page.insert_text((72, 250), "Figure 1 — Sample diagram showing results.", fontsize=9)

    doc.save(str(path))
    doc.close()
    return path
