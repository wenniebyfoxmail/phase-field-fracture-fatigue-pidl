from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


BASE_SOURCE_COMMIT = "7c56ff383187cdee2f45e1b15d707f148f386302"
BASE_SOURCE_MANIFEST_SHA256 = "61e12721da19ce37c2f065804d2a151b6bd80981196687f6f3fe292dca48b89e"
T3_TERMINAL_MANIFEST_SHA256 = "455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"
T3_ADJUDICATION_SHA256 = "9c0a0783bd6c59d825300538336258350df63c294f38f7febf29dae905c00300"
CASE_ID = "T3_rev_loading_order"
T3_CASE_ID = "T3_loading_history"
EXPECTED_MEX = {
    "AMOR": "e200dbb757172c3927bcd72f4f093c5a6b17dab52fcbd72505e34e0434924b9a",
    "AT1_HISTORY_FATIGUE": "3d9989b7fcc89ea36f1de196cad86cfcef3406c7365ac82bd6c58280a0cc9298",
    "cholmod2": "86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329",
    "initial": "ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db",
}
EXPECTED_THREADS = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_DYNAMIC": "FALSE",
}
EXPECTED_MATLAB = {
    "absolute_path_order": [
        "C:\\q4diag\\toy-road-t3-production-7c56ff3-run1\\.toy-road-runtime-overlay",
        "C:\\q4diag\\phase-field-fracture-fatigue-pidl-toy-road-impl\\producer_handoffs\\toy_road_p0_repeatability_20260803",
        "C:\\q4diag\\griphfith-pf-rebuild-355d4c83\\Sources",
        "C:\\SuiteSparse\\SuiteSparse-dev\\CHOLMOD\\MATLAB",
        "C:\\SuiteSparse\\SuiteSparse-dev\\AMD\\MATLAB",
        "C:\\SuiteSparse\\SuiteSparse-dev\\COLAMD\\MATLAB",
        "C:\\SuiteSparse\\SuiteSparse-dev\\CCOLAMD\\MATLAB",
        "C:\\SuiteSparse\\SuiteSparse-dev\\CAMD\\MATLAB",
    ],
    "release": "R2025b",
    "update": "Update 5",
    "version": "25.2.0.3177638",
    "computer": "PCWIN64",
    "executable_sha256": "322158960d70ea723d7bf6e5bb06f6b058b1489a85624d6c6a2be83be4944c2d",
    "blas": "Intel(R) oneAPI Math Kernel Library Version 2024.1-Product Build 20240215 for Intel(R) 64 architecture applications (CNR branch auto)",
    "lapack": "Intel(R) oneAPI Math Kernel Library Version 2024.1-Product Build 20240215 for Intel(R) 64 architecture applications (CNR branch auto) supporting Linear Algebra PACKage (LAPACK 3.11.0)",
}
EXPECTED_EXECUTION = {
    "case_physics_contract_sha256": "fbbe2c46ec394f20589e7c150783a08b5fbd79d13e51ce74eef90930def0146c",
    "family_contract_sha256": "a53cd26a457801fe87cce9afea19ca1ea21e1009567b06fb3bb813fe7c3279d2",
    "four_binary_sha256": EXPECTED_MEX,
    "matlab": EXPECTED_MATLAB,
    "resume_allowed": False,
    "retry_performed": False,
    "runtime_lock_sha256": "a53a1431b6f7a1b56f44f3faccb410ba11a4b9a6ef4f1a16b30258936bd0f8d7",
    "single_execution": True,
    "source_commit": BASE_SOURCE_COMMIT,
    "source_manifest_sha256": BASE_SOURCE_MANIFEST_SHA256,
    "thread_settings": EXPECTED_THREADS,
    "thread_settings_evidence": {
        "basis": "static_launch_environment_bound_by_committed_launcher",
        "launcher_sha256": "65a317bbaa4242b272e9fd74a54e5a19c0d33c493ac423b79244386dcd443417",
    },
}


class SealError(RuntimeError):
    """Raised when the immutable evidence cannot authorize the single T3-rev case."""


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise SealError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise SealError(f"non-finite JSON number: {value}")


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SealError(f"cannot read strict JSON {path}: {error}") from error
    if not isinstance(value, dict) or not _finite_json(value):
        raise SealError(f"expected finite JSON object: {path}")
    return value


def _finite_json(value: object) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_finite_json(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_json(item) for key, item in value.items())
    return False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _exact_json_equal(actual: object, expected: object) -> bool:
    """Compare finite JSON values without bool/int or int/float coercion."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_json_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_json_equal(item, expected_item)
            for item, expected_item in zip(actual, expected)
        )
    return actual == expected


def _load_verifier() -> Any:
    path = Path(__file__).with_name("verify_extension_diff.py")
    spec = importlib.util.spec_from_file_location("t3_rev_seal_verifier", path)
    if spec is None or spec.loader is None:
        raise SealError("cannot load extension verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _require_clean_commit(repo_root: Path, extension_manifest: Mapping[str, object]) -> str:
    try:
        head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"], check=True,
            capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise SealError("repository commit cannot be resolved") from error
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise SealError("repository HEAD is not a full lowercase commit")
    if status:
        raise SealError("repository must be clean before sealing a production execution")
    if extension_manifest.get("repo_commit") != head:
        raise SealError("extension repo commit is not the clean committed repository revision")
    return head


def _require_review_non_authorizing(receipt: Path) -> None:
    try:
        text = receipt.read_text(encoding="utf-8")
    except OSError as error:
        raise SealError(f"cannot read review receipt: {error}") from error
    required = (
        "Verdict: PASS, with one provenance-layer discrepancy disclosed.",
        "Terminal manifest SHA-256 matches `455b149b...344bb01`.",
        "No FEM, T3-rev or T2-CONT computation was launched. This receipt is non-authorizing.",
    )
    if any(item not in text for item in required):
        raise SealError("review receipt is non-authorizing evidence only")
    if "authoriz" in text.lower().replace("non-authorizing", ""):
        raise SealError("review receipt is non-authorizing evidence only")


def _require_registry(registry: Mapping[str, object]) -> None:
    if registry.get("schema_version") != "toy_road_qualified_trajectory_registry_v1" \
            or registry.get("status") != "PASS" \
            or registry.get("authorization_capability") is not None:
        raise SealError("trajectory registry is not the accepted non-authorizing predecessor")
    trajectories = registry.get("trajectories")
    if not isinstance(trajectories, dict):
        raise SealError("trajectory registry has no trajectories")
    expected = {
        "P0_parent": "QUALIFIED",
        "T1_initial_defect": "QUALIFIED",
        "T2_material_state": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4",
        T3_CASE_ID: "QUALIFIED",
    }
    if set(trajectories) != set(expected) or any(
            not isinstance(trajectories.get(case), dict)
            or trajectories[case].get("status") != status
            for case, status in expected.items()):
        raise SealError("trajectory registry statuses differ from the accepted predecessor")
    if trajectories[T3_CASE_ID].get("terminal_manifest_sha256") != T3_TERMINAL_MANIFEST_SHA256:
        raise SealError("trajectory registry does not bind the T3 terminal manifest")


def _require_t3_adjudication(adjudication: Mapping[str, object], terminal: Mapping[str, object]) -> dict[str, object]:
    if adjudication.get("schema_version") != "toy_road_t3_sibling_terminal_adjudication_v1" \
            or adjudication.get("status") != "PASS" \
            or adjudication.get("classification") != "PASS_T3_LOADING_HISTORY_SIBLING_TERMINAL_PACKAGE" \
            or adjudication.get("case_id") != T3_CASE_ID \
            or adjudication.get("authorization_capability") is not None \
            or adjudication.get("follow_on_authorized") is not False:
        raise SealError("T3 adjudication is not the required non-authorizing terminal PASS")
    evidence = adjudication.get("evidence_sha256")
    execution = adjudication.get("execution")
    if not isinstance(evidence, dict) or evidence.get("terminal_manifest") != T3_TERMINAL_MANIFEST_SHA256:
        raise SealError("T3 adjudication does not bind the expected terminal manifest")
    if not isinstance(execution, dict) or execution.get("source_commit") != BASE_SOURCE_COMMIT \
            or execution.get("source_manifest_sha256") != BASE_SOURCE_MANIFEST_SHA256 \
            or execution.get("resume_allowed") is not False \
            or execution.get("retry_performed") is not False \
            or execution.get("single_execution") is not True:
        raise SealError("T3 execution identity is invalid")
    if terminal.get("case_id") != T3_CASE_ID or terminal.get("source_commit") != BASE_SOURCE_COMMIT \
            or terminal.get("runtime_lock_sha256") != execution.get("runtime_lock_sha256"):
        raise SealError("T3 terminal manifest does not validate the adjudication claims")
    if not _exact_json_equal(execution, EXPECTED_EXECUTION):
        raise SealError("T3 runtime identity is not the exact qualified mapping")
    return execution


def _loading_histogram(blocks: object) -> dict[str, int]:
    if not isinstance(blocks, list):
        raise SealError("loading blocks are malformed")
    histogram: dict[str, int] = {}
    expected_start = 1
    for item in blocks:
        if not isinstance(item, list) or len(item) != 3:
            raise SealError("loading block is malformed")
        start, end, amplitude = item
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) \
                or not isinstance(end, int) or isinstance(amplitude, bool) \
                or not isinstance(amplitude, (int, float)) or not math.isfinite(float(amplitude)) \
                or start != expected_start or end < start:
            raise SealError("loading block is malformed")
        expected_start = end + 1
        key = format(float(amplitude), ".17g")
        histogram[key] = histogram.get(key, 0) + end - start + 1
    return histogram


def _require_physics(extension_root: Path) -> dict[str, object]:
    contract_path = Path(__file__).with_name("T3_REV_CONTRACT.json")
    builder_path = Path(__file__).with_name("build_t3_rev_extension.py")
    spec = importlib.util.spec_from_file_location("t3_rev_seal_contract", builder_path)
    if spec is None or spec.loader is None:
        raise SealError("cannot load T3-rev contract validator")
    builder = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = builder
    try:
        spec.loader.exec_module(builder)
        contract = builder.read_strict_contract(contract_path)
    except Exception as error:
        raise SealError(f"T3-rev contract is invalid: {error}") from error
    finally:
        sys.modules.pop(spec.name, None)
    expected_contract = {
        "schema_version": "toy_road_t3_rev_contract_v1",
        "base_source_commit": BASE_SOURCE_COMMIT,
        "base_source_manifest_sha256": BASE_SOURCE_MANIFEST_SHA256,
        "case_id": CASE_ID,
        "changed_axes": ["loading.blocks"],
        "loading_blocks": [[1, 30, 0.126], [31, 60, 0.108], [61, 150, 0.12]],
        "authorization_capability": None,
        "resume_allowed": False,
        "follow_on_authorized": False,
    }
    if contract != expected_contract:
        raise SealError("T3-rev contract is not the exact non-authorizing case definition")
    cases_path = extension_root / "CASE_PHYSICS_CONTRACTS.json"
    cases = read_json(cases_path)
    all_cases = cases.get("cases")
    if not isinstance(all_cases, dict):
        raise SealError("extension case physics are missing")
    t3 = all_cases.get(T3_CASE_ID)
    rev = all_cases.get(CASE_ID)
    if not isinstance(t3, dict) or not isinstance(rev, dict) \
            or t3.get("changed_axes") != ["loading.blocks"] \
            or rev.get("changed_axes") != ["loading.blocks"]:
        raise SealError("T3/T3-rev changed-axis contract is invalid")
    t3_physics = t3.get("physics")
    rev_physics = rev.get("physics")
    if not isinstance(t3_physics, dict) or not isinstance(rev_physics, dict):
        raise SealError("T3/T3-rev physics are missing")
    t3_without_blocks = copy.deepcopy(t3_physics)
    rev_without_blocks = copy.deepcopy(rev_physics)
    try:
        t3_blocks = t3_without_blocks["loading"].pop("blocks")
        rev_blocks = rev_without_blocks["loading"].pop("blocks")
    except (KeyError, AttributeError) as error:
        raise SealError("T3/T3-rev loading blocks are missing") from error
    if t3_without_blocks != rev_without_blocks or rev_blocks != expected_contract["loading_blocks"] \
            or t3_blocks == rev_blocks:
        raise SealError("T3-rev physics do not differ from T3 exclusively in loading.blocks")
    t3_first_60 = _loading_histogram([block for block in t3_blocks if block[1] <= 60])
    rev_first_60 = _loading_histogram([block for block in rev_blocks if block[1] <= 60])
    if t3_first_60 != rev_first_60 or t3_blocks[2:] != rev_blocks[2:]:
        raise SealError("T3-rev does not retain the exact first-60 histogram and later loading")
    return {
        "only_loading_blocks_differ": True,
        "first_60_histogram_equal_to_t3": True,
        "t3_first_60_histogram": t3_first_60,
        "t3_loading_blocks": t3_blocks,
        "t3_rev_loading_blocks": rev_blocks,
        "extension_case_contracts_sha256": sha256(cases_path),
    }


def _write_new(path: Path, value: Mapping[str, object]) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def build_seal(
        repo_root: Path, extension_root: Path, t3_adjudication: Path,
        review_receipt: Path, registry: Path, destination: Path) -> dict[str, object]:
    """Create the one-case T3-rev seal only from fully revalidated evidence."""
    repo_root, extension_root, destination = Path(repo_root).resolve(), Path(extension_root).resolve(), Path(destination).resolve()
    if destination.exists():
        raise SealError("seal destination already exists and will not be clobbered")
    base_root = repo_root / "producer_handoffs" / "toy_road_p0_repeatability_20260803"
    terminal_path = repo_root / "analysis" / "toy_road_t3_mechanism_20260819" / "evidence" / "TERMINAL_MANIFEST.json"
    manifest_path = extension_root / "EXTENSION_SOURCE_MANIFEST.json"
    inventory_path = extension_root / "SOURCE_DIFF_INVENTORY.json"
    contract_path = Path(__file__).with_name("T3_REV_CONTRACT.json")
    manifest = read_json(manifest_path)
    repo_commit = _require_clean_commit(repo_root, manifest)
    verifier = _load_verifier()
    try:
        verification = verifier.verify_extension_diff(base_root, extension_root)
    except Exception as error:
        raise SealError(f"extension verification failed: {error}") from error
    if verification.get("status") != "PASS":
        raise SealError("extension verification did not PASS")
    _require_review_non_authorizing(Path(review_receipt))
    registry_value = read_json(Path(registry))
    _require_registry(registry_value)
    terminal = read_json(terminal_path)
    if sha256(terminal_path) != T3_TERMINAL_MANIFEST_SHA256:
        raise SealError("T3 terminal manifest content hash differs from the accepted predecessor")
    t3_adjudication = Path(t3_adjudication)
    if sha256(t3_adjudication) != T3_ADJUDICATION_SHA256:
        raise SealError("published T3 adjudication hash differs from the evidence inventory")
    adjudication = read_json(t3_adjudication)
    execution = _require_t3_adjudication(adjudication, terminal)
    physics = _require_physics(extension_root)
    extension_identity = {
        "composite_producer": "sealed_T3_base_plus_T3_rev_case_definition_extension",
        "repository_commit": repo_commit,
        "base_source_commit": manifest["base_source_commit"],
        "base_source_manifest_sha256": manifest["base_source_manifest_sha256"],
        "extension_source_manifest_sha256": sha256(manifest_path),
        "extension_contract_sha256": sha256(contract_path),
        "source_diff_inventory_sha256": sha256(inventory_path),
        "extension_family_contract_sha256": sha256(extension_root / "FAMILY_CONTRACT.json"),
        "verification": verification,
    }
    predecessor_evidence = {
        "t3_terminal_adjudication_sha256": T3_ADJUDICATION_SHA256,
        "t3_terminal_manifest_sha256": sha256(terminal_path),
        "independent_review_receipt_sha256": sha256(Path(review_receipt)),
        "qualified_trajectory_registry_sha256": sha256(Path(registry)),
    }
    runtime_identity = copy.deepcopy(EXPECTED_EXECUTION)
    seal: dict[str, object] = {
        "schema_version": "toy_road_t3_rev_seal_v1",
        "status": "PASS",
        "case_id": CASE_ID,
        "authorization_capability": "exactly_one_T3_rev_loading_order_execution",
        "resume_allowed": False,
        "follow_on_authorized": False,
        "extension_identity": extension_identity,
        "predecessor_evidence": predecessor_evidence,
        "physics_closure": physics,
        "runtime_identity": runtime_identity,
    }
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise SealError("seal destination already exists and will not be clobbered") from error
    _write_new(destination / "T3_REV_SEAL.json", seal)
    return seal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--extension-root", type=Path, required=True)
    parser.add_argument("--t3-adjudication", type=Path, required=True)
    parser.add_argument("--review-receipt", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_seal(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
