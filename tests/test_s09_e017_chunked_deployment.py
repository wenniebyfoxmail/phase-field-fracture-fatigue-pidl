from __future__ import annotations

import hashlib
import gzip
import json
from pathlib import Path
import subprocess
import sys

import pytest

import s09_e017_chunked_deployment as deployment

from s09_e017_chunked_deployment import (
    DeploymentStop,
    assemble_with_receipt,
    audit_legacy_partial,
    build_chunk_store,
    canonical_json,
    import_verified_legacy_chunks,
    inspect_chunk_store,
    load_manifest,
    manifest_sha256,
    verify_git_archive_identity,
)


COMMIT = "2" * 40


def _fixture(tmp_path: Path, payload: bytes = b"abcdefghij"):
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(payload)
    chunk_dir = tmp_path / "chunks"
    manifest = build_chunk_store(
        archive,
        chunk_dir,
        chunk_size_bytes=4,
        expected_archive_bytes=len(payload),
        expected_archive_sha256=hashlib.sha256(payload).hexdigest(),
        reviewed_control_commit=COMMIT,
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(canonical_json(manifest))
    return payload, archive, chunk_dir, manifest, manifest_path


def test_build_manifest_and_store_are_exact(tmp_path: Path) -> None:
    payload, _, chunk_dir, manifest, manifest_path = _fixture(tmp_path)
    assert manifest["chunking"] == {
        "algorithm": "fixed-size-sha256",
        "chunk_count": 3,
        "chunk_size_bytes": 4,
    }
    assert [chunk["size"] for chunk in manifest["chunks"]] == [4, 4, 2]
    assert sum(path.stat().st_size for path in chunk_dir.iterdir()) == len(payload)
    loaded = load_manifest(manifest_path, expected_sha256=manifest_sha256(manifest))
    assert loaded == manifest


def test_manifest_hash_and_canonical_text_are_required(tmp_path: Path) -> None:
    _, _, _, manifest, manifest_path = _fixture(tmp_path)
    with pytest.raises(DeploymentStop, match="manifest SHA-256 mismatch") as caught:
        load_manifest(manifest_path, expected_sha256="0" * 64)
    assert caught.value.first_reason == "MANIFEST_HASH_MISMATCH"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pretty_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    with pytest.raises(DeploymentStop, match="not canonical") as caught:
        load_manifest(manifest_path, expected_sha256=pretty_sha)
    assert caught.value.first_reason == "MANIFEST_INVALID"


def test_missing_chunk_is_reported_and_blocks_publish(tmp_path: Path) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    (chunk_dir / manifest["chunks"][1]["name"]).unlink()
    inspection = inspect_chunk_store(manifest, chunk_dir)
    assert inspection["missing"] == [1]
    assert inspection["missing_names"] == [manifest["chunks"][1]["name"]]
    assert inspection["complete"] is False
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    result = assemble_with_receipt(
        manifest, chunk_dir, output, receipt, max_wall_seconds=30
    )
    assert result["first_reason"] == "CHUNK_MISSING"
    assert result["published"] is False
    assert not output.exists()
    assert json.loads(receipt.read_text()) == result


def test_corrupt_chunk_is_reported_and_blocks_publish(tmp_path: Path) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    corrupt = chunk_dir / manifest["chunks"][0]["name"]
    corrupt.write_bytes(b"xxxx")
    inspection = inspect_chunk_store(manifest, chunk_dir)
    assert inspection["corrupt"] == [0]
    assert inspection["corrupt_names"] == [manifest["chunks"][0]["name"]]
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    result = assemble_with_receipt(
        manifest, chunk_dir, output, receipt, max_wall_seconds=30
    )
    assert result["first_reason"] == "CHUNK_HASH_MISMATCH"
    assert not output.exists()


def test_unexpected_store_entry_is_visible_but_does_not_vote(tmp_path: Path) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    (chunk_dir / "unrelated.partial").write_bytes(b"not trusted")
    inspection = inspect_chunk_store(manifest, chunk_dir)
    assert inspection["complete"] is True
    assert inspection["unexpected"] == ["unrelated.partial"]


def test_legacy_audit_does_not_trust_size_or_prefix_claim(tmp_path: Path) -> None:
    payload, _, _, manifest, _ = _fixture(tmp_path)
    legacy = tmp_path / "legacy.partial"
    legacy.write_bytes(payload[:6])
    report = audit_legacy_partial(manifest, legacy)
    assert report["verified_complete_chunks"] == [0]
    assert report["incomplete_chunks"] == [1]
    assert report["absent_chunks"] == [2]
    assert report["verified_reusable_bytes"] == 4
    assert report["read_only"] is True


def test_legacy_complete_but_wrong_range_is_not_reusable(tmp_path: Path) -> None:
    payload, _, _, manifest, _ = _fixture(tmp_path)
    legacy = tmp_path / "legacy.partial"
    legacy.write_bytes(b"xxxx" + payload[4:8])
    report = audit_legacy_partial(manifest, legacy)
    assert report["mismatched_complete_chunks"] == [0]
    assert report["verified_complete_chunks"] == [1]


def test_legacy_import_reverifies_and_publishes_only_matching_chunks(
    tmp_path: Path,
) -> None:
    payload, _, _, manifest, _ = _fixture(tmp_path)
    legacy = tmp_path / "legacy.partial"
    legacy.write_bytes(payload[:9])
    imported_dir = tmp_path / "imported"
    result = import_verified_legacy_chunks(manifest, legacy, imported_dir)
    assert result["imported_chunks"] == [0, 1]
    inspection = inspect_chunk_store(manifest, imported_dir)
    assert inspection["present_valid"] == [0, 1]
    assert inspection["missing"] == [2]


def test_path_conflict_preserves_existing_output_and_records_first_reason(
    tmp_path: Path,
) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "published.tar.gz"
    output.write_bytes(b"preserve me")
    receipt = tmp_path / "receipt.json"
    result = assemble_with_receipt(
        manifest, chunk_dir, output, receipt, max_wall_seconds=30
    )
    assert result["first_reason"] == "PUBLISH_PATH_CONFLICT"
    assert result["published"] is False
    assert output.read_bytes() == b"preserve me"


def test_wall_clock_starts_before_verification_and_stops_before_publish(
    tmp_path: Path,
) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    ticks = iter([0.0, 0.0, 2.0, 3.0])
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    result = assemble_with_receipt(
        manifest,
        chunk_dir,
        output,
        receipt,
        max_wall_seconds=1.0,
        monotonic=lambda: next(ticks),
    )
    assert result["first_reason"] == "DEPLOYMENT_WALL_CAP_EXCEEDED"
    assert result["elapsed_seconds"] == 3.0
    assert not output.exists()
    assert not list(tmp_path.glob(".*.assembly-*.tmp"))


def test_prepared_journal_cannot_publish_after_wall_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    clock = {"value": 0.0}
    real_publish = deployment._publish_bytes_no_replace

    def delayed_prepared(path: Path, data: bytes) -> None:
        real_publish(path, data)
        if path == receipt.with_name(f"{receipt.name}.prepared"):
            clock["value"] = 5.0

    monkeypatch.setattr(deployment, "_publish_bytes_no_replace", delayed_prepared)
    result = assemble_with_receipt(
        manifest,
        chunk_dir,
        output,
        receipt,
        max_wall_seconds=1.0,
        monotonic=lambda: clock["value"],
    )
    assert result["first_reason"] == "DEPLOYMENT_WALL_CAP_EXCEEDED"
    assert result["published"] is False
    assert receipt.with_name(f"{receipt.name}.prepared").exists()
    assert not output.exists()


def test_complete_store_publishes_original_bytes_atomically(tmp_path: Path) -> None:
    payload, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    result = assemble_with_receipt(
        manifest, chunk_dir, output, receipt, max_wall_seconds=30
    )
    assert result["terminal_state"] == "DEPLOYMENT_ARCHIVE_PUBLISHED"
    assert result["published"] is True
    assert result["archive_sha256"] == hashlib.sha256(payload).hexdigest()
    assert output.read_bytes() == payload
    assert not list(tmp_path.glob(".*.assembly-*.tmp"))


def test_post_link_directory_fsync_failure_records_true_publication_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    real_link = deployment.os.link
    real_open = deployment.os.open
    state = {"linked": False, "failed": False}

    def tracking_link(source, destination):
        real_link(source, destination)
        if Path(destination) == output:
            state["linked"] = True

    def one_failure_open(path, flags):
        if state["linked"] and not state["failed"] and Path(path) == output.parent:
            state["failed"] = True
            raise OSError("injected directory fsync open failure")
        return real_open(path, flags)

    monkeypatch.setattr(deployment.os, "link", tracking_link)
    monkeypatch.setattr(deployment.os, "open", one_failure_open)
    result = assemble_with_receipt(
        manifest, chunk_dir, output, receipt, max_wall_seconds=30
    )
    assert result["terminal_state"] == "DEPLOYMENT_STOPPED_AFTER_PUBLICATION"
    assert result["first_reason"] == "PUBLISH_DURABILITY_UNCONFIRMED"
    assert result["published"] is True
    assert result["output_exists"] is True
    assert output.read_bytes() == payload
    assert json.loads(receipt.read_text()) == result


def test_success_receipt_failure_leaves_prepared_journal_and_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    real_publish = deployment._publish_bytes_no_replace
    failed = {"value": False}

    def fail_terminal_once(path: Path, data: bytes) -> None:
        if path == receipt and not failed["value"]:
            failed["value"] = True
            raise OSError("injected terminal receipt failure")
        real_publish(path, data)

    monkeypatch.setattr(deployment, "_publish_bytes_no_replace", fail_terminal_once)
    result = assemble_with_receipt(
        manifest, chunk_dir, output, receipt, max_wall_seconds=30
    )
    assert result["terminal_state"] == "DEPLOYMENT_TERMINAL_RECEIPT_WRITE_FAILED"
    assert result["published"] is True
    assert output.read_bytes() == payload
    assert receipt.with_name(f"{receipt.name}.attempt").exists()
    assert receipt.with_name(f"{receipt.name}.prepared").exists()
    assert receipt.with_name(f"{receipt.name}.failure").exists()


def test_cli_stopped_assembly_returns_nonzero(tmp_path: Path) -> None:
    _, _, chunk_dir, manifest, manifest_path = _fixture(tmp_path)
    (chunk_dir / manifest["chunks"][0]["name"]).unlink()
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    cli = Path(__file__).resolve().parents[1] / "scripts/s09_e017_chunked_archive.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(cli),
            "assemble",
            "--manifest",
            str(manifest_path),
            "--manifest-sha256",
            manifest_sha256(manifest),
            "--chunk-dir",
            str(chunk_dir),
            "--output",
            str(output),
            "--receipt",
            str(receipt),
            "--max-wall-seconds",
            "30",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert json.loads(completed.stdout)["first_reason"] == "CHUNK_MISSING"
    assert not output.exists()


def test_cli_inspect_success_without_terminal_state_returns_zero(
    tmp_path: Path
) -> None:
    _, _, chunk_dir, manifest, manifest_path = _fixture(tmp_path)
    cli = Path(__file__).resolve().parents[1] / "scripts/s09_e017_chunked_archive.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(cli),
            "inspect-store",
            "--manifest",
            str(manifest_path),
            "--manifest-sha256",
            manifest_sha256(manifest),
            "--chunk-dir",
            str(chunk_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["complete"] is True


def test_git_archive_identity_verification_consumes_full_gzip_stream(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repo, check=True)
    (repo / "value.txt").write_text("archive identity\n", encoding="utf-8")
    subprocess.run(["git", "add", "value.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    tar_payload = subprocess.check_output(["git", "archive", commit], cwd=repo)
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(gzip.compress(tar_payload, mtime=0))
    result = verify_git_archive_identity(
        archive,
        expected_bytes=archive.stat().st_size,
        expected_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        expected_commit=commit,
    )
    assert result["terminal_state"] == "DEPLOYMENT_ARCHIVE_VERIFIED"
    assert result["reviewed_control_commit"] == commit


def test_import_report_conflict_is_checked_before_chunk_mutation(
    tmp_path: Path
) -> None:
    payload, _, _, manifest, manifest_path = _fixture(tmp_path)
    legacy = tmp_path / "legacy.partial"
    legacy.write_bytes(payload)
    imported = tmp_path / "imported"
    report = tmp_path / "import-report.json"
    report.write_text("preserve", encoding="utf-8")
    cli = Path(__file__).resolve().parents[1] / "scripts/s09_e017_chunked_archive.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(cli),
            "import-legacy",
            "--manifest",
            str(manifest_path),
            "--manifest-sha256",
            manifest_sha256(manifest),
            "--legacy-partial",
            str(legacy),
            "--chunk-dir",
            str(imported),
            "--report",
            str(report),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stderr)["first_reason"] == "REPORT_PATH_CONFLICT"
    assert not imported.exists()
    assert report.read_text() == "preserve"


def test_receipt_is_write_once(tmp_path: Path) -> None:
    _, _, chunk_dir, manifest, _ = _fixture(tmp_path)
    output = tmp_path / "published.tar.gz"
    receipt = tmp_path / "receipt.json"
    receipt.write_text("preserve", encoding="utf-8")
    with pytest.raises(DeploymentStop, match="refusing to replace") as caught:
        assemble_with_receipt(manifest, chunk_dir, output, receipt, max_wall_seconds=30)
    assert caught.value.first_reason == "RECEIPT_PATH_CONFLICT"
    assert receipt.read_text() == "preserve"
    assert not output.exists()
