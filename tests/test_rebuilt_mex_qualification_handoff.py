from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "producer_handoffs" / "rebuilt_initial_mex_qualification_20260801"
MANIFEST = HANDOFF / "SOURCE_SHA256SUMS.txt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_entries() -> list[tuple[str, str]]:
    return [
        tuple(line.split("  ", 1))
        for line in MANIFEST.read_text().splitlines()
        if line
    ]


def run_git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_qualification_source_inventory_is_exact_and_hash_valid() -> None:
    entries = manifest_entries()
    paths = [relative for _, relative in entries]
    expected = {
        path.relative_to(ROOT).as_posix()
        for path in HANDOFF.rglob("*")
        if path.is_file()
        and path != MANIFEST
        and path != HANDOFF / "runtime" / "initial.mexw64"
    }
    expected.add(Path(__file__).resolve().relative_to(ROOT).as_posix())
    expected.add((ROOT / "tests/.gitattributes").relative_to(ROOT).as_posix())
    assert paths == sorted(expected)
    assert len(paths) == len({path.casefold() for path in paths})
    for expected_hash, relative in entries:
        assert expected_hash == sha256(ROOT / relative)


def test_qualification_readme_records_q1_pass_and_q2_blocker() -> None:
    text = " ".join((HANDOFF / "README.md").read_text().split())
    for phrase in (
        "EvidenceLockUnsealed",
        "blocked_missing_parent_damage_degradation_field",
        "blocked_missing_parent_active_field",
        "remains intentionally absent",
        "deterministic_internal_force_probe",
        "Q1 passed",
        "stopped before recovery",
        "must not start",
    ):
        assert phrase.lower() in text.lower()
    assert not (HANDOFF / "QUALIFICATION_EVIDENCE_LOCK.json").exists()


def test_qualification_package_locks_text_to_lf() -> None:
    attributes = (HANDOFF / ".gitattributes").read_text()
    assert "* text eol=lf" in attributes
    assert "runtime/*.mexw64 -text" in attributes
    for _, relative in manifest_entries():
        path = ROOT / relative
        if (
            path.name != "LEGACY_CRASH_DUMP.txt"
            and path.suffix.lower() in {".m", ".ps1", ".json", ".md", ".txt", ".py"}
        ):
            assert b"\r\n" not in path.read_bytes()


@pytest.mark.parametrize("autocrlf", ["true", "false"])
def test_qualification_manifest_is_portable_in_fresh_checkout(
    tmp_path: Path, autocrlf: str
) -> None:
    source = tmp_path / "source"
    shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", ".pytest_cache"))
    run_git(source, "init")
    run_git(source, "config", "user.email", "fixture@example.invalid")
    run_git(source, "config", "user.name", "Fixture")
    run_git(source, "config", "core.autocrlf", "false")
    run_git(source, "add", ".")
    run_git(source, "commit", "-m", "portable fixture")

    checkout = tmp_path / f"checkout-{autocrlf}"
    subprocess.run(
        ["git", "-c", f"core.autocrlf={autocrlf}", "clone", str(source), str(checkout)],
        check=True,
        capture_output=True,
        text=True,
    )
    checkout_manifest = checkout / MANIFEST.relative_to(ROOT)
    for expected_hash, relative in (
        line.split("  ", 1)
        for line in checkout_manifest.read_text().splitlines()
        if line
    ):
        assert sha256(checkout / relative) == expected_hash
