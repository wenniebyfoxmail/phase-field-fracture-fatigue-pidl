from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


EXPECTED_T3_SHA = "fbbe2c46ec394f20589e7c150783a08b5fbd79d13e51ce74eef90930def0146c"
EXPECTED_PRODUCER = "d17efe6118ded31d7085d08cd85fdb0d31c09659"


class SealError(RuntimeError):
    pass


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise SealError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(SealError(f"invalid JSON number: {token}")),
        )
    except (OSError, json.JSONDecodeError) as error:
        raise SealError(f"cannot read strict JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise SealError(f"expected one JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_new(path: Path, value: object) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def build_seal(repo_root: Path, p0r_adjudication_path: Path, destination: Path) -> dict[str, object]:
    repo_root = repo_root.resolve()
    destination = destination.resolve()
    contract_path = Path(__file__).resolve().parent / "T3_SIBLING_CONTRACT.json"
    cases_path = repo_root / "producer_handoffs" / "toy_road_p0_repeatability_20260803" / "CASE_PHYSICS_CONTRACTS.json"
    contract = read_json(contract_path)
    adjudication = read_json(p0r_adjudication_path.resolve())
    cases = read_json(cases_path)
    if contract != {
        "schema_version": "toy_road_t3_sibling_contract_v1",
        "predecessor_gate": "P0_P0R_REPEATABILITY_PASS",
        "case_id": "T3_loading_history",
        "changed_axes": ["loading.blocks"],
        "resume_allowed": False,
        "follow_on_authorized": False,
    }:
        raise SealError("T3 sibling contract is invalid")
    required_gate = {
        "schema_version": "toy_road_external_repeatability_adjudication_v1",
        "status": "PASS",
        "predecessor_gate_only": True,
        "production_execution_authorized": False,
        "authorization_capability": "none",
    }
    if any(adjudication.get(key) != expected for key, expected in required_gate.items()):
        raise SealError("P0/P0R adjudication is not a non-authorizing PASS predecessor gate")
    p0 = adjudication.get("p0")
    p0r = adjudication.get("p0r")
    if not isinstance(p0, dict) or not isinstance(p0r, dict):
        raise SealError("P0/P0R evidence is missing")
    if p0.get("physical_input_projection_sha256") != p0r.get("physical_input_projection_sha256"):
        raise SealError("P0/P0R physical projections differ")
    for evidence in (p0, p0r):
        identity = evidence.get("producer_runtime_identity")
        if not isinstance(identity, dict) or identity.get("source_commit") != EXPECTED_PRODUCER:
            raise SealError("P0/P0R producer identity differs from the qualified producer")
    all_cases = cases.get("cases")
    if not isinstance(all_cases, dict):
        raise SealError("case physics contracts are missing")
    p0_case = all_cases.get("P0_parent")
    t3_case = all_cases.get("T3_loading_history")
    if not isinstance(p0_case, dict) or not isinstance(t3_case, dict):
        raise SealError("P0 or T3 physics contract is missing")
    if t3_case.get("changed_axes") != ["loading.blocks"] or t3_case.get("case_physics_contract_sha256") != EXPECTED_T3_SHA:
        raise SealError("T3 changed-axis contract differs from the sealed declaration")
    p0_physics = copy.deepcopy(p0_case.get("physics"))
    t3_physics = copy.deepcopy(t3_case.get("physics"))
    if not isinstance(p0_physics, dict) or not isinstance(t3_physics, dict):
        raise SealError("physics objects are missing")
    p0_blocks = p0_physics.get("loading", {}).pop("blocks", None)
    t3_blocks = t3_physics.get("loading", {}).pop("blocks", None)
    if p0_physics != t3_physics or p0_blocks == t3_blocks:
        raise SealError("T3 does not differ from P0 exclusively in loading.blocks")
    seal = {
        "schema_version": "toy_road_t3_sibling_seal_v1",
        "status": "PASS",
        "predecessor_gate": contract["predecessor_gate"],
        "siblings": ["T1_initial_defect", "T2_material_state", "T3_loading_history"],
        "case_id": contract["case_id"],
        "changed_axes": contract["changed_axes"],
        "resume_allowed": False,
        "follow_on_authorized": False,
        "authorization_capability": "exactly_one_T3_loading_history_execution",
        "qualified_producer_source_commit": EXPECTED_PRODUCER,
        "execution_source_commit": "7c56ff383187cdee2f45e1b15d707f148f386302",
        "case_physics_contract_sha256": EXPECTED_T3_SHA,
        "family_contract_sha256": cases.get("family_contract_sha256"),
        "contract_sha256": sha256(contract_path),
        "case_contracts_sha256": sha256(cases_path),
        "p0r_adjudication_sha256": sha256(p0r_adjudication_path.resolve()),
        "p0_terminal_manifest_sha256": p0.get("terminal_manifest_sha256"),
        "p0r_terminal_manifest_sha256": p0r.get("terminal_manifest_sha256"),
        "p0r_physical_input_projection_sha256": p0r.get("physical_input_projection_sha256"),
        "physics_closure": {
            "only_loading_blocks_differ": True,
            "p0_loading_blocks": p0_blocks,
            "t3_loading_blocks": t3_blocks,
        },
    }
    destination.mkdir(parents=True, exist_ok=False)
    _write_new(destination / "T3_SIBLING_SEAL.json", seal)
    _write_new(destination / "T3_SIBLING_CONTRACT.copy.json", contract)
    return seal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_seal(args.repo_root, args.adjudication, args.destination), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
