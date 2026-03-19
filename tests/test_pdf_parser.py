"""Integration tests for pdf_parser CLI."""

import json
import subprocess
import sys
from pathlib import Path


def _run_parser(*args) -> dict:
    """Run pdf_parser.py as subprocess and return parsed JSON."""
    cmd = [sys.executable, "-m", "lib.pdf_parser", *args]
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    return json.loads(result.stdout)


class TestCLIManifest:
    def test_manifest_mode(self, simple_pdf):
        data = _run_parser("manifest", str(simple_pdf))
        assert "metadata" in data
        assert "blocks" in data
        assert "stats" in data

    def test_manifest_with_ref_label(self, simple_pdf):
        data = _run_parser("manifest", str(simple_pdf), "--ref", "ref1")
        for block in data["blocks"]:
            assert block["id"].startswith("ref1:")

    def test_manifest_blocks_have_no_full_content(self, simple_pdf):
        data = _run_parser("manifest", str(simple_pdf))
        for block in data["blocks"]:
            assert "content" not in block
            assert "preview" in block


class TestCLIBlocks:
    def test_blocks_mode(self, simple_pdf):
        manifest = _run_parser("manifest", str(simple_pdf))
        block_id = manifest["blocks"][0]["id"]

        data = _run_parser("blocks", str(simple_pdf), "--ids", block_id)
        assert "blocks" in data
        assert len(data["blocks"]) == 1
        assert "content" in data["blocks"][0]

    def test_blocks_multiple_ids(self, simple_pdf):
        manifest = _run_parser("manifest", str(simple_pdf))
        ids = ",".join(b["id"] for b in manifest["blocks"][:2])

        data = _run_parser("blocks", str(simple_pdf), "--ids", ids)
        assert len(data["blocks"]) == 2


class TestCLISection:
    def test_section_mode(self, simple_pdf):
        manifest = _run_parser("manifest", str(simple_pdf))
        sections = {b["section"] for b in manifest["blocks"] if b.get("section")}
        if sections:
            section_id = next(iter(sections))
            data = _run_parser("section", str(simple_pdf), "--id", section_id)
            assert "blocks" in data
            assert len(data["blocks"]) >= 1
