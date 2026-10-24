#!/usr/bin/env python3
"""Supplemental byte/topology cross-check for the two fixed-weight archives.

This is deliberately an identity check only. It hashes the sealed manifests
and their members, validates the complete chronological index, and writes a
small receipt outside the archives. It never opens a MAT/HDF5 payload,
starts MATLAB, trains a model, or changes a FEM archive. MATLAB independently
repeats archive admission before it opens any MAT payload; this Python receipt
is never authoritative for admission.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any


SOURCE_COMMIT = "862992a60edc7f59335365beacb5c71fc8592a7a"
STATE_KEY = re.compile(r"c(\d{4})_s(\d{2})")
MANIFEST_LINE = re.compile(r"([0-9a-fA-F]{64})\s+\*?(.+)")
SOURCE_SCHEDULE_TOLERANCE = 1e-14
SOLVER_LOADFUN = (1e-6, 0.25, 0.5, 0.75, 1.0, 1e-6)
NOMINAL_LOAD_FACTOR = (0.0, 0.25, 0.5, 0.75, 1.0, 0.0)
EFFECTIVE_LOAD_FACTOR = (0.0,) + tuple(value - SOLVER_LOADFUN[0] for value in SOLVER_LOADFUN[1:])

LOCKS: dict[str, dict[str, Any]] = {
    "hard5_u0115_stage0b": {
        "run_id": "hard5_u0115_stage0b_c23cede2bec94515a393aa291c3d6d92",
        "cycles": 103,
        "u_max": 0.115,
        "index_sha256": "eb1cbacb52252891cb1039ec8df3bcb5cb4ce7ea2fe451476e0e241def10855a",
        "static_sha256": "a7edb0e430ae84669e3326f777360e7d73488fa41fad8fa09a038e6bbd26985e",
        "config_sha256": "0075cb117676aeb334e185b4149ea7ceefc5799e01b68d0303a56533e86ea7b5",
        "manifest_sha256": "50fd30872436b4d71800a4a38548d63b9b807cc12fbe9435d23d6963055d9cff",
        "source_receipt_sha256": "b4552a7b48726fcd7596d5cb73ea59ed5362366e479eba450893a70622971b29",
        "summary_sha256": "7f88c2cb494b47fd7c443b84e192f98a64c74b4da75dd622422d51a96ba2072f",
    },
    "hard5_u0125_stage0b": {
        "run_id": "hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae",
        "cycles": 73,
        "u_max": 0.125,
        "index_sha256": "3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
        "static_sha256": "b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e",
        "config_sha256": "c4ee5a79831c7a2a327eec976d36a7ae96945ad1cbf67071e38b8d98ddd511de",
        "manifest_sha256": "51baa00bbb8d3d33443812e3d05a48ca85d39d4f26d58654e8061a595d5df742",
        "source_receipt_sha256": "273610cf49baae708a0be0006111c90b5ff70dc06d39f465bf88eb1fb3a39cfc",
        "summary_sha256": "e454fb5c46482f9a60e82ee4fb3f2988440b34544c5f03498ac9a55607e37eb2",
    },
}


def fail(message: str) -> None:
    raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_regular_child(root: Path, relative: str) -> Path:
    candidate = root / relative.replace("\\", "/")
    if candidate.is_symlink() or not candidate.is_file():
        fail(f"manifest member is not a regular file: {relative}")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"manifest member escapes archive root: {relative}") from exc
    return candidate


def parse_manifest(root: Path, expected_digest: str) -> list[tuple[str, str]]:
    manifest = root / "SHA256SUMS.txt"
    if sha256_file(manifest) != expected_digest:
        fail("SHA256SUMS.txt digest does not match the immutable archive lock")
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        match = MANIFEST_LINE.fullmatch(line)
        if match is None:
            fail("unrecognised SHA256SUMS.txt line")
        digest, relative = match.group(1).lower(), match.group(2).replace("\\", "/")
        if relative in seen or relative in ("", ".", ".."):
            fail(f"duplicate or invalid manifest member: {relative!r}")
        seen.add(relative)
        entries.append((relative, digest))
    if not entries:
        fail("empty archive manifest")
    return entries


def hash_manifest_members(root: Path, entries: list[tuple[str, str]]) -> tuple[dict[str, int], dict[str, str]]:
    bytes_checked = 0
    digests: dict[str, str] = {}
    for relative, expected in entries:
        path = require_regular_child(root, relative)
        if sha256_file(path) != expected:
            fail(f"manifest hash mismatch: {relative}")
        bytes_checked += path.stat().st_size
        digests[relative] = expected
    return {"files": len(entries), "bytes": bytes_checked}, digests


def check_identity_files(root: Path, lock: dict[str, Any]) -> None:
    expected = {
        "state_index.csv": lock["index_sha256"],
        "static/native_q4_mesh_dofs_quadrature.mat": lock["static_sha256"],
        "provenance/config_receipt.mat": lock["config_sha256"],
        "provenance/source_receipt.json": lock["source_receipt_sha256"],
        "run_summary.json": lock["summary_sha256"],
    }
    for relative, digest in expected.items():
        path = require_regular_child(root, relative)
        if sha256_file(path) != digest:
            fail(f"identity file hash mismatch: {relative}")

    source = json.loads((root / "provenance" / "source_receipt.json").read_text())
    summary = json.loads((root / "run_summary.json").read_text())
    if source.get("source_commit") != SOURCE_COMMIT or source.get("source_dirty") is not False:
        fail("archive does not bind the required clean producer source commit")
    provenance = summary.get("provenance", {})
    if provenance.get("run_id") != lock["run_id"] or summary.get("sealed") is not True:
        fail("run summary identity/sealed state mismatch")


def load_index(root: Path, lock: dict[str, Any]) -> list[dict[str, str]]:
    with (root / "state_index.csv").open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {
            "state_key", "cycle", "substep", "timing", "is_alias", "source_state_key",
            "payload_file", "payload_sha256", "nominal_load_factor", "effective_load_factor",
            "imposed_displacement", "converged",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            fail("state_index.csv schema mismatch")
        rows = list(reader)
    cycles = int(lock["cycles"])
    if len(rows) != cycles * 6:
        fail("unexpected logical state count")
    expected_keys = [f"c{cycle:04d}_s{substep:02d}"
                     for cycle in range(1, cycles + 1) for substep in range(6)]
    if [row["state_key"] for row in rows] != expected_keys:
        fail("state index chronological coverage mismatch")
    by_key = {row["state_key"]: row for row in rows}
    if len(by_key) != len(rows):
        fail("duplicate state key")
    imposed = tuple(float(lock["u_max"]) * value for value in EFFECTIVE_LOAD_FACTOR)
    for row in rows:
        match = STATE_KEY.fullmatch(row["state_key"])
        if match is None:
            fail("noncanonical state key")
        cycle, substep = int(match.group(1)), int(match.group(2))
        if int(row["cycle"]) != cycle or int(row["substep"]) != substep:
            fail(f"cycle/substep mismatch at {row['state_key']}")
        if row["timing"] != ("pre_cycle_committed" if substep == 0 else "post_history_commit"):
            fail(f"timing mismatch at {row['state_key']}")
        try:
            nominal = float(row["nominal_load_factor"])
            effective = float(row["effective_load_factor"])
            displacement = float(row["imposed_displacement"])
        except ValueError as exc:
            raise ValueError(f"non-numeric load metadata at {row['state_key']}") from exc
        if (row["converged"] != "1"
                or abs(nominal - NOMINAL_LOAD_FACTOR[substep]) > SOURCE_SCHEDULE_TOLERANCE
                or abs(effective - EFFECTIVE_LOAD_FACTOR[substep]) > SOURCE_SCHEDULE_TOLERANCE
                or abs(displacement - imposed[substep]) > SOURCE_SCHEDULE_TOLERANCE):
            fail(f"convergence/load mismatch at {row['state_key']}")
        if substep == 0 and cycle > 1:
            prior = by_key[f"c{cycle - 1:04d}_s05"]
            if not (row["is_alias"] == "1" and row["source_state_key"] == prior["state_key"]
                    and row["payload_file"] == prior["payload_file"]
                    and row["payload_sha256"] == prior["payload_sha256"]):
                fail(f"s05-to-s00 alias mismatch at cycle {cycle}")
        elif not (row["is_alias"] == "0" and row["source_state_key"] == row["state_key"]):
            fail(f"native state identity mismatch at {row['state_key']}")
    return rows


def check_payload_inventory(root: Path, rows: list[dict[str, str]], cycles: int,
                            manifest_digests: dict[str, str]) -> dict[str, int]:
    expected: dict[str, str] = {}
    for row in rows:
        relative = row["payload_file"].replace("\\", "/")
        if Path(relative).parts != ("states", Path(relative).name):
            fail(f"invalid payload path: {relative}")
        old = expected.setdefault(relative, row["payload_sha256"].lower())
        if old != row["payload_sha256"].lower():
            fail(f"conflicting payload hashes: {relative}")
    if len(expected) != 1 + cycles * 5:
        fail("unexpected unique physical state count")
    actual = {path.name for path in (root / "states").iterdir() if path.is_file() and not path.is_symlink()}
    if actual != {Path(relative).name for relative in expected}:
        fail("states directory/index membership mismatch")
    bytes_checked = 0
    for relative, digest in expected.items():
        path = require_regular_child(root, relative)
        if manifest_digests.get(relative) != digest:
            fail(f"payload index/manifest hash mismatch: {relative}")
        bytes_checked += path.stat().st_size
    return {"unique_payloads": len(expected), "payload_bytes": bytes_checked}


def preflight_one(root: Path) -> dict[str, Any]:
    if root.is_symlink():
        fail("archive root must not be a symbolic link")
    root = root.resolve(strict=True)
    lock = LOCKS.get(root.name)
    if lock is None:
        fail(f"unsupported archive root name: {root.name}")
    if not root.is_dir():
        fail("archive root must be a real directory")
    manifest = parse_manifest(root, str(lock["manifest_sha256"]))
    manifest_stats, manifest_digests = hash_manifest_members(root, manifest)
    check_identity_files(root, lock)
    rows = load_index(root, lock)
    payload_stats = check_payload_inventory(root, rows, int(lock["cycles"]), manifest_digests)
    return {
        "archive_name": root.name,
        "archive_root": str(root),
        "run_id": lock["run_id"],
        "producer_commit": SOURCE_COMMIT,
        "u_max": lock["u_max"],
        "logical_rows": len(rows),
        "unique_physical_states": payload_stats["unique_payloads"],
        "physical_transitions": int(lock["cycles"]) * 5,
        "identity_hashes": {
            "manifest": lock["manifest_sha256"],
            "state_index": lock["index_sha256"],
            "static": lock["static_sha256"],
            "config": lock["config_sha256"],
            "source_receipt": lock["source_receipt_sha256"],
            "run_summary": lock["summary_sha256"],
        },
        "manifest": manifest_stats,
        "payloads": payload_stats,
    }


def safe_output(path: Path, roots: list[Path]) -> Path:
    path = path.resolve(strict=False)
    if path.exists():
        fail(f"refusing to overwrite preflight receipt: {path}")
    for root in roots:
        try:
            path.relative_to(root.resolve(strict=True))
        except ValueError:
            continue
        fail("preflight receipt must be outside every FEM archive root")
    if not path.parent.is_dir():
        fail(f"output parent does not exist: {path.parent}")
    return path


def interpreter_record() -> dict[str, Any]:
    """Record the constrained interpreter that performed this supplemental check."""
    if (sys.implementation.name != "cpython" or sys.version_info < (3, 11)
            or not sys.dont_write_bytecode or not sys.flags.no_user_site
            or not getattr(sys.flags, "safe_path", False)):
        fail("preflight requires CPython 3.11+ invoked with -B -s -P")
    executable = Path(sys.executable).resolve(strict=True)
    return {
        "implementation": sys.implementation.name,
        "version": [sys.version_info.major, sys.version_info.minor, sys.version_info.micro],
        "executable": str(executable),
        "dont_write_bytecode": bool(sys.dont_write_bytecode),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", False)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs=2, type=Path,
                        help="exact U0.115 and U0.125 archive roots, in either order")
    parser.add_argument("--output", required=True, type=Path,
                        help="new JSON receipt outside both archives")
    args = parser.parse_args()
    if len({path.name for path in args.archives}) != 2 or set(path.name for path in args.archives) != set(LOCKS):
        fail("exactly the U0.115 and U0.125 archive roots are required")
    output = safe_output(args.output, args.archives)
    reports = [preflight_one(path) for path in sorted(args.archives, key=lambda p: p.name)]
    receipt = {
        "schema": "fixed_weight_saved_state_preflight_v1",
        "status": "verified",
        "scope": "supplemental byte/topology cross-check only; no MAT/HDF5 scientific decode",
        "archive_admission_authoritative": False,
        "interpreter": interpreter_record(),
        "producer_commit": SOURCE_COMMIT,
        "archives": reports,
        "total_physical_transitions": sum(int(report["physical_transitions"]) for report in reports),
        "raw_archives_modified": False,
        "matlab_started": False,
        "fem_solver_started": False,
        "training_started": False,
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                     prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(output)
    print(json.dumps({"status": receipt["status"], "output": str(output),
                      "physical_transitions": receipt["total_physical_transitions"]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # Fail closed without a partial receipt.
        print(f"preflight failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
