#!/usr/bin/env python3
"""Verify the one-shot admission-only evidence before an E017 final launch."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_admission_only import (  # noqa: E402
    sha256_bytes,
    strict_json,
    validate_authority,
    validate_candidate,
)


RUN_ID = "S09-E017-R001-factorised-head-p0"
SUCCESS = "ADMISSION_ONLY_METADATA_READY__SCIENTIFIC_IDENTITIES_UNVERIFIED"
GUARD_SUCCESS = "ADMISSION_ONLY_PLAN_COMPLETED"
ARCHIVE_SHA256 = "4ece34be786fc85bb9655c076c13c45d276d08dfde405a8fb1367e4b49ffdd22"
ARCHIVE_BYTES = 14_359_316
STAGE1_CANDIDATE_SHA256 = (
    "c6c9bf73e9a2e9172bf9b42ebbe1ea5502c152cdae1dbc4fa197e515dd6babda"
)
STAGE1_PLAN_SHA256 = "7ce0228dd234d3e6f71d4069bfdc98658a0606315911d2995aaaf0b0a615bbc3"
STAGE1_ATTEMPT_ID = "s09e017-admissiononly-20261025-r3"
EXPECTED_ADMISSION_ROOT = (
    ROOT
    / "local_archive/experiments/S09-E017/admission_only_attempts"
    / STAGE1_ATTEMPT_ID
)
ZERO_COUNTERS = {
    "scientific_asset_content_bytes": 0,
    "cuda_initializations": 0,
    "runtime_builds": 0,
    "model_forwards": 0,
    "autograd_collections": 0,
    "optimizer_constructions": 0,
    "optimizer_steps": 0,
}


def _bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load(path: Path) -> tuple[dict, bytes]:
    payload = path.read_bytes()
    return json.loads(payload), payload


def verify_handoff(root: Path) -> dict:
    if root.resolve() != EXPECTED_ADMISSION_ROOT.resolve():
        raise ValueError("Stage 1 evidence root drift")
    guard, _ = _load(root / "guard_receipt.json")
    consumption, _ = _load(root / "authority_consumption_receipt.json")
    authority, authority_bytes = strict_json(root / "admission_only_authority.json")
    candidate_path = (
        ROOT / "docs/research/S09/S09-E017/"
        "s09_e017_admission_only_candidate_20261025_r3.json"
    )
    candidate, candidate_bytes = strict_json(candidate_path)
    validate_candidate(candidate)
    if sha256_bytes(candidate_bytes) != STAGE1_CANDIDATE_SHA256:
        raise ValueError("Stage 1 candidate hash mismatch")
    if authority["candidate_sha256"] != STAGE1_CANDIDATE_SHA256:
        raise ValueError("Stage 1 authority candidate drift")
    if authority["plan_sha256"] != STAGE1_PLAN_SHA256:
        raise ValueError("Stage 1 authority plan drift")
    validate_authority(
        authority,
        candidate,
        candidate_sha256=STAGE1_CANDIDATE_SHA256,
        plan_sha256=STAGE1_PLAN_SHA256,
    )
    if authority["admission_only_attempt_id"] != STAGE1_ATTEMPT_ID:
        raise ValueError("Stage 1 attempt id drift")
    if Path(authority["local_evidence_root"]).resolve() != root.resolve():
        raise ValueError("Stage 1 authority evidence root drift")
    stdout = (root / "stdout.log").read_bytes()
    if guard["terminal_state"] != GUARD_SUCCESS:
        raise ValueError("admission-only guard did not complete")
    if guard["process_returncode"] != 0 or guard["first_reason"] is not None:
        raise ValueError("admission-only process did not exit cleanly")
    if guard["evidence_write_errors"] or not guard["stdout_published"]:
        raise ValueError("admission-only evidence publication incomplete")
    if guard["stdout_sha256"] != _bytes_sha256(stdout):
        raise ValueError("admission-only stdout hash mismatch")
    if guard["retry"] is not False or guard["reconnect"] is not False:
        raise ValueError("admission-only guard permits replay")
    authority_sha256 = _bytes_sha256(authority_bytes)
    expected_shared = {
        "run_id": RUN_ID,
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "candidate_sha256": authority["candidate_sha256"],
        "plan_sha256": authority["plan_sha256"],
        "authority_sha256": authority_sha256,
    }
    for name, receipt in (("guard", guard), ("consumption", consumption)):
        for key, value in expected_shared.items():
            if receipt[key] != value:
                raise ValueError(f"{name} {key} mismatch")
    if consumption["terminal_state"] != "ADMISSION_ONLY_AUTHORITY_CONSUMED_NO_RETRY":
        raise ValueError("Stage 1 consumption state drift")
    if (
        consumption.get("retry") is not False
        or consumption.get("reconnect") is not False
    ):
        raise ValueError("Stage 1 consumption permits replay")
    lines = [line for line in stdout.decode("utf-8").splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("admission-only stdout record count drift")
    remote_precheck = json.loads(lines[0])
    metadata = json.loads(lines[1])
    if metadata["terminal_state"] != SUCCESS:
        raise ValueError("metadata admission success state missing")
    if metadata["run_id"] != RUN_ID:
        raise ValueError("metadata run id mismatch")
    if metadata["admission_only_attempt_id"] != authority["admission_only_attempt_id"]:
        raise ValueError("metadata attempt id mismatch")
    if metadata["authority_sha256"] != authority_sha256:
        raise ValueError("metadata authority hash mismatch")
    if metadata["archive"]["sha256"] != ARCHIVE_SHA256:
        raise ValueError("metadata archive hash mismatch")
    if metadata["archive"]["bytes_read"] != ARCHIVE_BYTES:
        raise ValueError("metadata archive read count mismatch")
    if metadata["execution_authorized"] or metadata["producer_authorized"]:
        raise ValueError("metadata-only receipt opened execution")
    if metadata["counters"] != ZERO_COUNTERS:
        raise ValueError("metadata-only receipt has scientific operations")
    if metadata["retry"] is not False or metadata["reconnect"] is not False:
        raise ValueError("metadata-only receipt permits replay")
    return {
        "schema_version": "s09-e017-admission-to-training-handoff-v1",
        "terminal_state": "ADMISSION_ONLY_EVIDENCE_VERIFIED_FOR_CONDITIONAL_LAUNCH",
        "run_id": RUN_ID,
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "candidate_sha256": authority["candidate_sha256"],
        "plan_sha256": authority["plan_sha256"],
        "authority_sha256": authority_sha256,
        "remote_precheck": remote_precheck,
        "metadata_receipt_sha256": _bytes_sha256(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
        ),
        "scientific_counters": metadata["counters"],
        "retry": False,
        "reconnect": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-evidence-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_handoff(args.admission_evidence_root), sort_keys=True))


if __name__ == "__main__":
    main()
