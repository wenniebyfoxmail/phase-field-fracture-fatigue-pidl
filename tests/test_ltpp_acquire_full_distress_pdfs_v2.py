from pathlib import Path

import pytest

from scripts import ltpp_acquire_full_distress_pdfs_v2 as subject


def test_frozen_eight_dates_are_unique_and_chronological():
    assert [date_id for date_id, _ in subject.DATES] == [
        "19910610",
        "19951024",
        "19970228",
        "19980407",
        "20010913",
        "20030514",
        "20071106",
        "20120417",
    ]


def test_manifest_excludes_its_own_hash(tmp_path: Path):
    (tmp_path / "one.txt").write_text("one\n", encoding="utf-8")
    subject.write_manifest(tmp_path)
    manifest = (tmp_path / "manifest.sha256").read_text(encoding="utf-8")
    assert "one.txt" in manifest
    assert "manifest.sha256" not in manifest


def test_acquire_requires_new_output_root(tmp_path: Path):
    with pytest.raises(FileExistsError, match="must be new"):
        subject.acquire(tmp_path, "2056", 4)


def test_render_lookup_accepts_pdftoppm_zero_padded_suffix(tmp_path: Path):
    prefix = tmp_path / "page"
    generated = tmp_path / "page-04.png"
    generated.write_bytes(b"png")
    assert sorted(prefix.parent.glob(f"{prefix.name}-*.png")) == [generated]
