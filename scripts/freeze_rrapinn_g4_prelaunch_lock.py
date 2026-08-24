#!/usr/bin/env python3
"""Freeze the complete exact-input, analysis and launch-code closure for G4."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FreezeError(ValueError):
    """Raised when a prelaunch input cannot be frozen safely."""


EXPECTED_LOCKED_CODE = {
    "scripts/analyze_rrapinn_g4_blind.py",
    "scripts/freeze_rrapinn_g4_prelaunch_lock.py",
    "scripts/run_rrapinn_g4_arm.py",
    "scripts/seal_rrapinn_g4_metrics.py",
    "scripts/unblind_rrapinn_g4.py",
    "scripts/validate_rrapinn_g4_exact_fem.py",
    "scripts/validate_rrapinn_g4_packet.py",
    "scripts/validate_rrapinn_g4_producer_evidence.py",
    "source/rrapinn_g4_blind_contract.py",
    "source/rrapinn_g4_field_analysis.py",
    "source/rrapinn_g4_launch_contract.py",
}
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_code_hash(code_root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    digest.update(b"rrapinn-g4-locked-code/v2\0")
    records: list[tuple[str, Path]] = []
    for path in files:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FreezeError(f"locked code file is missing: {resolved}")
        try:
            relative = resolved.relative_to(code_root.resolve()).as_posix()
        except ValueError as exc:
            raise FreezeError(f"locked code must be beneath code root: {resolved}") from exc
        records.append((relative, resolved))
    names = [name for name, _ in records]
    if len(names) != len(set(names)) or set(names) != EXPECTED_LOCKED_CODE:
        raise FreezeError("locked code set does not exactly match the frozen G4 closure")
    for relative, path in sorted(records):
        name = relative.encode("utf-8")
        content = path.read_bytes()
        digest.update(struct.pack("<Q", len(name)))
        digest.update(name)
        digest.update(struct.pack("<Q", len(content)))
        digest.update(content)
    return digest.hexdigest()


def _sha256sum_entries(path: Path) -> list[dict[str, str]]:
    records = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        digest, name = raw.split(maxsplit=1)
        name = name.lstrip(" *")
        if len(digest) != 64 or not name:
            raise FreezeError("invalid SHA256SUMS record")
        records.append({"path": name, "sha256": digest})
    if len(records) != 20 or len({row["path"] for row in records}) != 20:
        raise FreezeError("exact FEM package must contain 20 unique SHA256SUMS records")
    return records


def _runtime_lock() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
        "h5py": importlib.metadata.version("h5py"),
    }


def build_lock(
    *, packet: Path, fem_manifest: Path, fem_validation_receipt: Path,
    projector: Path, projector_builder_manifest: Path,
    projector_analysis_manifest: Path, mapping_source: Path,
    mapping_source_manifest: Path, code_root: Path, analysis_code: list[Path],
    integration_commit: str,
) -> dict:
    required = {
        "packet": packet,
        "fem_manifest": fem_manifest,
        "fem_validation_receipt": fem_validation_receipt,
        "projector": projector,
        "projector_builder_manifest": projector_builder_manifest,
        "projector_analysis_manifest": projector_analysis_manifest,
        "mapping_source": mapping_source,
        "mapping_source_manifest": mapping_source_manifest,
    }
    for label, path in required.items():
        if not path.is_file():
            raise FreezeError(f"{label} is missing: {path}")
    if not _COMMIT_RE.fullmatch(integration_commit):
        raise FreezeError("integration commit must be a full 40-character Git SHA")
    packet_payload = json.loads(packet.read_text(encoding="utf-8"))
    if (
        packet_payload.get("schema") != "rrapinn-g4-u012-preregistration-v1"
        or packet_payload.get("development_case") != "U0.12"
        or packet_payload.get("training_authorized") is not False
        or packet_payload.get("qualification_snapshot", {}).get(
            "current_external_input_blockers"
        ) != []
    ):
        raise FreezeError("packet is not the exact-input-qualified unauthorized U0.12 design")
    from scripts.validate_rrapinn_g4_packet import validate as validate_packet
    if validate_packet(packet_payload)["status"] != (
        "pass_ready_for_prelaunch_lock_training_unauthorized"
    ):
        raise FreezeError("packet fails its frozen canonical validator")
    receipt = json.loads(fem_validation_receipt.read_text(encoding="utf-8"))
    if (
        receipt.get("status") != "PASS_G4_U012_EXACT_PEAK_FEM_INPUT"
        or receipt.get("first_detect", {}).get("truth_cycle") != 83
        or receipt.get("first_detect", {}).get("confirmation_used_as_truth") is not False
        or receipt.get("first_detect", {}).get("selected_cycle_counts") != [0, 0, 22]
    ):
        raise FreezeError("FEM receipt does not preserve c83 first-detect truth")
    package_root = Path(receipt["package"]["path"])
    fem_sha256s = package_root / "SHA256SUMS"
    if (
        not fem_sha256s.is_file()
        or sha256_file(fem_sha256s) != receipt["package"]["sha256s_sha256"]
        or sha256_file(fem_manifest) != receipt["package"]["manifest_sha256"]
    ):
        raise FreezeError("FEM manifest/SHA256SUMS identity mismatch")
    fem_entries = _sha256sum_entries(fem_sha256s)
    for record in fem_entries:
        artifact = package_root / record["path"]
        if not artifact.is_file() or sha256_file(artifact) != record["sha256"]:
            raise FreezeError(f"FEM package artifact mismatch: {record['path']}")
    builder = json.loads(projector_builder_manifest.read_text(encoding="utf-8"))
    analysis = json.loads(projector_analysis_manifest.read_text(encoding="utf-8"))
    if (
        builder.get("headline_policy") != "mapping_contained_true_only"
        or builder.get("projector", {}).get("n_headline_rows") != 85113
        or builder.get("projector", {}).get("fallback_rows_in_headline") != 0
        or builder.get("projector", {}).get("deterministic_sha256")
        != "2782085ab78cbfd82a04b485422d642fb0b81275d56b695673fc5f43aa6612e7"
        or analysis.get("schema_version") != "rrapinn-g4-contained-projector-v2"
        or analysis.get("deterministic_sha256")
        != "be764b01573109a9585eaf1f1e596ca1ca1ed15878acdcb4c1e5afc1e105d422"
        or analysis.get("artifact", {}).get("sha256") != sha256_file(projector)
    ):
        raise FreezeError("projector manifests violate the exact v2 headline contract")
    code_root = code_root.resolve()
    code_records = []
    for path in sorted((item.resolve() for item in analysis_code), key=lambda item: str(item)):
        code_records.append({
            "path": path.relative_to(code_root).as_posix(),
            "sha256": sha256_file(path),
        })
    return {
        "schema": "rrapinn-g4-prelaunch-lock-v2",
        "status": "READY_FOR_INDEPENDENT_GATE_TRAINING_UNAUTHORIZED",
        "development_case": "U0.12",
        "training_authorized": False,
        "integration_commit": integration_commit,
        "first_detect_truth_cycle": 83,
        "first_detect_provenance_class": "historical_reference_receipt",
        "selected_cycle_first_detect_counts": [0, 0, 22],
        "confirmation_cycle": 86,
        "confirmation_used_as_truth": False,
        "fem_sha256sum_entries": fem_entries,
        "artifacts": {
            **{
                label: {"path": str(path.resolve()), "sha256": sha256_file(path)}
                for label, path in required.items()
            },
            "fem_sha256s": {
                "path": str(fem_sha256s.resolve()), "sha256": sha256_file(fem_sha256s),
            },
        },
        "locked_code": {
            "code_root": str(code_root),
            "deterministic_sha256": deterministic_code_hash(code_root, analysis_code),
            "files": code_records,
        },
        "metric_contract": {
            "log10_floor": 1e-12,
            "cvar_tail_policy": "exact_area_fraction_with_fractional_boundary_mass",
            "headline_mask": "mapping_contained_true_only",
            "residual_mask": "interior_free_nodes",
            "mirror_grid": "64x64_fixed_square_-0.5_to_0.5",
            "mirror_min_paired_area_coverage": 0.5,
        },
        "runtime": _runtime_lock(),
        "claim_boundary": (
            "Ready only for a fresh independent launch gate. Training still requires "
            "a separate exact user-authorization receipt bound to this lock and commit."
        ),
    }


def exclusive_write(path: Path, payload: dict) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite prelaunch lock: {path}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--fem-manifest", type=Path, required=True)
    parser.add_argument("--fem-validation-receipt", type=Path, required=True)
    parser.add_argument("--projector", type=Path, required=True)
    parser.add_argument("--projector-builder-manifest", type=Path, required=True)
    parser.add_argument("--projector-analysis-manifest", type=Path, required=True)
    parser.add_argument("--mapping-source", type=Path, required=True)
    parser.add_argument("--mapping-source-manifest", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--analysis-code", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.code_root.resolve()
    if subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"], text=True,
    ).strip():
        raise FreezeError("integration checkout must be clean before freezing")
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
    ).strip()
    payload = build_lock(
        packet=args.packet, fem_manifest=args.fem_manifest,
        fem_validation_receipt=args.fem_validation_receipt,
        projector=args.projector,
        projector_builder_manifest=args.projector_builder_manifest,
        projector_analysis_manifest=args.projector_analysis_manifest,
        mapping_source=args.mapping_source,
        mapping_source_manifest=args.mapping_source_manifest,
        code_root=repo, analysis_code=args.analysis_code,
        integration_commit=head,
    )
    lock_sha256 = exclusive_write(args.output, payload)
    print(json.dumps({**payload, "lock_sha256": lock_sha256}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
