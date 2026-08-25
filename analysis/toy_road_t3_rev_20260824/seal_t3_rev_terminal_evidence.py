"""Create-once external evidence package for the sealed T3-rev pre-c1 exit."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


PRODUCER_COMMIT = "b66e08be94ff552b7f467ac2e7b693034cef01f5"
RECOVERY_CLASSIFICATION = "FAIL_RECOVERY_NEWTON_NONCONVERGENCE_BEFORE_C1"


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _strict_json(path: Path) -> dict[str, object]:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8") + b"\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_once(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _write_json_once(path: Path, value: Mapping[str, object]) -> None:
    _write_once(path, _canonical_json_bytes(value))


def _repo_identity(repo_root: Path, require_clean: bool) -> str:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("adjudicator repository HEAD is not a full commit")
    if require_clean:
        status = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repo_root, text=True,
        )
        if status:
            raise ValueError("adjudicator repository must be clean before evidence sealing")
    return commit


def _normalise_raw_inventory(
        raw: Mapping[str, object], current: Mapping[str, object]) -> dict[str, object]:
    if raw.get("schema_version") == "toy_road_t3_rev_raw_run_tree_inventory_v1":
        normalised = dict(raw)
    else:
        required = {
            "run_root", "entry_count", "directory_count", "file_count", "entries",
        }
        if not required.issubset(raw):
            raise ValueError("raw pre-offline inventory schema is incomplete")
        normalised = {
            "schema_version": "toy_road_t3_rev_raw_run_tree_inventory_v1",
            **{field: raw[field] for field in required},
        }
    scalar_fields = {
        "schema_version", "run_root", "entry_count", "directory_count", "file_count",
    }
    entries = normalised.get("entries")
    current_entries = current.get("entries")
    if not isinstance(entries, list) or not isinstance(current_entries, list) \
            or any(not isinstance(item, dict) for item in (*entries, *current_entries)):
        raise ValueError("raw pre-offline inventory entries are malformed")
    by_path = {item.get("relative_path"): item for item in entries}
    current_by_path = {item.get("relative_path"): item for item in current_entries}
    if len(by_path) != len(entries) or len(current_by_path) != len(current_entries) \
            or any(normalised.get(field) != current.get(field) for field in scalar_fields) \
            or by_path != current_by_path:
        raise ValueError("raw pre-offline inventory differs from the current sealed run")
    return dict(current)


def _file_inventory(root: Path) -> dict[str, object]:
    files = [{
        "relative_path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    } for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
        if path.is_file()]
    return {
        "schema_version": "toy_road_t3_rev_offline_file_inventory_v1",
        "root_role": root.name,
        "file_count": len(files),
        "files": files,
    }


def _seal_terminal_evidence(
        *, run_root: Path, sealed_base_root: Path, extension_root: Path,
        seal_path: Path, raw_pre_inventory_path: Path, destination: Path,
        require_clean_repository: bool = True,
) -> dict[str, object]:
    """Seal validation and two deterministic analyses without writing to the run."""
    run_root = Path(run_root).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"terminal evidence destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"terminal evidence parent does not exist: {destination.parent}")
    module_root = Path(__file__).resolve().parent
    repo_root = module_root.parents[1]
    adjudicator_commit = _repo_identity(repo_root, require_clean_repository)
    validator_path = module_root / "validate_t3_rev_terminal.py"
    analyzer_path = module_root / "analyze_t3_rev.py"
    validator = _load(validator_path, "t3_rev_external_evidence_validator")
    analyzer = _load(analyzer_path, "t3_rev_external_evidence_analyzer")
    current_inventory = validator.inventory_run_tree(run_root)
    raw_path = Path(raw_pre_inventory_path).resolve()
    raw_bytes = raw_path.read_bytes()
    raw = _strict_json(raw_path)
    retained_inventory = _normalise_raw_inventory(raw, current_inventory)
    launch = _strict_json(run_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json")
    if launch.get("launcher_repository_commit") != PRODUCER_COMMIT:
        raise ValueError("sealed run is not bound to the required producer commit")

    destination.mkdir(exist_ok=False)
    _write_once(destination / "RAW_RUN_TREE_INVENTORY.pre.json", raw_bytes)
    source_manifest = {
        "schema_version": "toy_road_t3_rev_adjudicator_source_manifest_v1",
        "producer_commit": PRODUCER_COMMIT,
        "adjudicator_commit": adjudicator_commit,
        "source_sha256": {
            "validate_t3_rev_terminal.py": _sha256(validator_path),
            "analyze_t3_rev.py": _sha256(analyzer_path),
            "seal_t3_rev_terminal_evidence.py": _sha256(Path(__file__).resolve()),
        },
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    _write_json_once(destination / "ADJUDICATOR_SOURCE_MANIFEST.json", source_manifest)
    adjudication_path = destination / "T3_REV_TERMINAL_ADJUDICATION.json"
    adjudication = validator.validate_terminal(
        run_root / "output",
        sealed_base_root=Path(sealed_base_root),
        extension_root=Path(extension_root),
        seal_path=Path(seal_path),
        run_root=run_root,
        destination=adjudication_path,
        preserve_run=True,
        expected_run_inventory=retained_inventory,
    )
    if adjudication.get("adjudicator_commit") != adjudicator_commit \
            or adjudication.get("adjudicator_source_sha256") != \
            source_manifest["source_sha256"]["validate_t3_rev_terminal.py"]:
        raise ValueError("validator adjudication source identity differs")
    first = destination / "analysis-run-1"
    second = destination / "analysis-run-2"
    first_summary = analyzer.analyze_nontrajectory(adjudication_path, first)
    second_summary = analyzer.analyze_nontrajectory(adjudication_path, second)
    first_inventory = _file_inventory(first)
    second_inventory = _file_inventory(second)
    _write_json_once(destination / "ANALYSIS_RUN_1_INVENTORY.json", first_inventory)
    _write_json_once(destination / "ANALYSIS_RUN_2_INVENTORY.json", second_inventory)
    first_paths = [item["relative_path"] for item in first_inventory["files"]]
    second_paths = [item["relative_path"] for item in second_inventory["files"]]
    comparisons: list[dict[str, object]] = []
    if first_paths == second_paths:
        for relative in first_paths:
            left = first / relative
            right = second / relative
            comparisons.append({
                "relative_path": relative,
                "analysis_run_1_sha256": _sha256(left),
                "analysis_run_2_sha256": _sha256(right),
                "bytes_identical": left.read_bytes() == right.read_bytes(),
            })
    comparison = {
        "schema_version": "toy_road_t3_rev_analysis_determinism_comparison_v1",
        "file_sets_identical": first_paths == second_paths,
        "all_csv_json_bytes_identical": first_paths == second_paths
        and all(item["bytes_identical"] for item in comparisons),
        "files": comparisons,
        "png_policy": "NO_PNG_CREATED_NOT_APPLICABLE_NO_FATIGUE_TRAJECTORY",
        "png_metadata_exclusion": "NOT_APPLICABLE_NO_PNG_FILES",
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    if not comparison["all_csv_json_bytes_identical"]:
        raise ValueError("offline analysis CSV/JSON bytes are not deterministic")
    _write_json_once(destination / "ANALYSIS_DETERMINISM_COMPARISON.json", comparison)
    final_inventory = validator.inventory_run_tree(run_root)
    if final_inventory != retained_inventory:
        raise ValueError("sealed run changed during external offline evidence production")
    _write_json_once(destination / "RUN_TREE_INVENTORY.post-offline.json", final_inventory)
    final_receipt = {
        "schema_version": "toy_road_t3_rev_final_non_authorizing_terminal_receipt_v1",
        "status": "INCOMPLETE_OFFLINE_ANALYSIS",
        "classification": RECOVERY_CLASSIFICATION,
        "order_effect_classification": "UNAVAILABLE_NO_FATIGUE_TRAJECTORY",
        "producer_commit": PRODUCER_COMMIT,
        "adjudicator_commit": adjudicator_commit,
        "adjudicator_source_manifest_sha256": _sha256(
            destination / "ADJUDICATOR_SOURCE_MANIFEST.json"),
        "raw_pre_offline_inventory_sha256": _sha256(
            destination / "RAW_RUN_TREE_INVENTORY.pre.json"),
        "post_offline_inventory_sha256": _sha256(
            destination / "RUN_TREE_INVENTORY.post-offline.json"),
        "run_inventory_unchanged": True,
        "validator_adjudication_sha256": _sha256(adjudication_path),
        "analysis_run_1_inventory_sha256": _sha256(
            destination / "ANALYSIS_RUN_1_INVENTORY.json"),
        "analysis_run_2_inventory_sha256": _sha256(
            destination / "ANALYSIS_RUN_2_INVENTORY.json"),
        "analysis_determinism_comparison_sha256": _sha256(
            destination / "ANALYSIS_DETERMINISM_COMPARISON.json"),
        "analysis_summary_sha256": _sha256(first / "mechanism_summary.json"),
        "analysis_summaries_identical": first_summary == second_summary,
        "figure_policy": "NOT_APPLICABLE_NO_FATIGUE_TRAJECTORY",
        "mechanism_claim_available": False,
        "retry_or_resume_authorized": False,
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    _write_json_once(
        destination / "FINAL_NONAUTHORIZING_TERMINAL_RECEIPT.json", final_receipt,
    )
    payload_inventory = _file_inventory(destination)
    manifest = {
        "schema_version": "toy_road_t3_rev_terminal_evidence_package_manifest_v1",
        "status": "SEALED_NON_AUTHORIZING_TERMINAL_EVIDENCE",
        "producer_commit": PRODUCER_COMMIT,
        "adjudicator_commit": adjudicator_commit,
        "adjudicator_source_manifest_sha256": final_receipt[
            "adjudicator_source_manifest_sha256"],
        "artifact_file_count": payload_inventory["file_count"],
        "artifacts": payload_inventory["files"],
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    _write_json_once(destination / "PACKAGE_MANIFEST.json", manifest)
    checksum_paths = sorted(
        (path for path in destination.rglob("*") if path.is_file()
         and path.name != "SHA256SUMS.txt"),
        key=lambda path: path.relative_to(destination).as_posix(),
    )
    sums = "".join(
        f"{_sha256(path)}  {path.relative_to(destination).as_posix()}\n"
        for path in checksum_paths
    ).encode("ascii")
    _write_once(destination / "SHA256SUMS.txt", sums)
    return final_receipt


def seal_terminal_evidence(**kwargs: Any) -> dict[str, object]:
    return _seal_terminal_evidence(**kwargs, require_clean_repository=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--sealed-base-root", type=Path, required=True)
    parser.add_argument("--extension-root", type=Path, required=True)
    parser.add_argument("--seal", dest="seal_path", type=Path, required=True)
    parser.add_argument("--raw-pre-inventory", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    result = seal_terminal_evidence(
        run_root=args.run_root,
        sealed_base_root=args.sealed_base_root,
        extension_root=args.extension_root,
        seal_path=args.seal_path,
        raw_pre_inventory_path=args.raw_pre_inventory,
        destination=args.destination,
    )
    sys.stdout.buffer.write(_canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
