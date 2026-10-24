"""Read-only, standard-library verification of a downloaded legacy receipt.

The separately reviewed contract is an independent trust input, not something
to derive from the receipt under test. This checker opens only its three named
local inputs, never imports the FEM runner, and writes its report to stdout.
It checks the reviewed runner's evidence, not scientific arrays or equilibrium.
verifier_source_commit identifies the staged remote verifier bundle's source
commit, not a later repository HEAD containing this checker and its contract.
The independently bound controller must report successful process completion
and the downloaded JSONL hash; absent execution fields cannot imply success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import re
import sys


class ReceiptError(ValueError):
    """A missing, malformed or inconsistent receipt is not admissible."""


def require(condition, message):
    if not condition:
        raise ReceiptError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    answer = {}
    for key, value in pairs:
        require(key not in answer, "duplicate JSON key: " + key)
        answer[key] = value
    return answer


def _invalid_constant(value):
    raise ReceiptError("nonfinite JSON constant: " + value)


def _finite_tree(value):
    if isinstance(value, float):
        require(math.isfinite(value), "nonfinite JSON number")
    elif isinstance(value, dict):
        for item in value.values():
            _finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            _finite_tree(item)


def parse_object(data, label):
    try:
        value = json.loads(data, object_pairs_hook=_pairs,
                           parse_constant=_invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptError(label + ": invalid JSON") from exc
    require(type(value) is dict, label + ": expected an object")
    _finite_tree(value)  # json.loads also accepts overflowing exponents such as 1e999.
    return value


def integer(value, label, minimum=0):
    require(type(value) is int and value >= minimum, label + ": invalid integer")
    return value


def number(value, label, minimum=0):
    require(type(value) in (int, float), label + ": invalid number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    require(finite and value >= minimum, label + ": invalid finite number")
    return value


def digest(value, label):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            label + ": invalid SHA256")
    return value


def equal(actual, expected, label):
    """Compare nested values without allowing bool to impersonate an integer."""
    if type(expected) is dict:
        require(type(actual) is dict and actual.keys() == expected.keys(), label + ": fields differ")
        for key in expected:
            equal(actual[key], expected[key], label + "." + key)
    elif type(expected) is list:
        require(type(actual) is list and len(actual) == len(expected), label + ": list differs")
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal(a, b, f"{label}[{i}]")
    elif type(expected) is float:
        require(type(actual) in (float, int) and actual == expected, label + ": value differs")
    else:
        require(type(actual) is type(expected) and actual == expected, label + ": value differs")


def fields(actual, expected, label):
    require(type(actual) is dict, label + ": expected an object")
    for key, value in expected.items():
        require(key in actual, label + ": missing " + key)
        equal(actual[key], value, label + "." + key)


def scope(event):
    fields(event, {"training_started": False, "solver_started": False,
                   "originals_modified": False}, event.get("kind", "scope"))


def windows_path(value):
    require(type(value) is str and bool(value), "invalid Windows path")
    return str(PureWindowsPath(value)).casefold()


def validate_contract(spec):
    require("code_commit" not in spec, "contract: obsolete code_commit field; use verifier_source_commit")
    fields(spec, {"schema": "fixed_weight_legacy_receipt_contract_v1",
                  "verifier_source_commit": "2e5061b0be5deae5098b36461dcdfadd981c60ad",
                  "execution_schema": "fixed_weight_legacy_controller_execution_v1",
                  "controller": {
                      "path": "scripts/run_fixed_weight_legacy_native_remote.py",
                      "bytes": 10680,
                      "sha256": "ff3ab12214c1aa16ac198857cd9e01081a4437544a8755e9e1781cf1fd2505ab"},
                  "receipt_schema": "fixed_weight_legacy_native_admission_receipt_v2",
                  "producer_commit": "53ce560b6d20b336d6ec92ccf56ed2b230e804ce",
                  "rule": "native53ce_recovered_load_source_f_no_negative_energy_v1",
                  "total_event_count": 1376, "event_count_before_complete": 1375,
                  "total_physical_states": 1368, "total_transitions": 1365,
                  "test_conditions": 0}, "contract")
    verifier = spec["verifier"]
    fields(verifier, {"schema": spec["receipt_schema"]}, "expected verifier")
    bundle = {"script": verifier["script"], "source_modules": verifier["source_modules"]}
    require(sha256(canonical(bundle)) == verifier["bundle_sha256"], "contract bundle digest differs")
    items = [bundle["script"], *bundle["source_modules"]]
    require(len(items) == 12 and len({item["path"] for item in items}) == 12,
            "contract must contain the runner and eleven distinct modules")
    for item in items:
        integer(item["bytes"], "code bytes", 1)
        digest(item["sha256"], "code hash")
    equal([a["identity"]["archive"] for a in spec["archives"]],
          ["hard5_u011_stage0b", "hard5_u012_stage0b", "hard5_u013_stage0b"], "contract order")
    for a, cycles in zip(spec["archives"], [125, 86, 62]):
        fields(a["identity"], {"cycles": cycles, "producer_commit": spec["producer_commit"]}, "contract identity")
        fields(a, {"physical_states": 5 * cycles + 1, "transitions": 5 * cycles,
                   "logical_states": 6 * cycles, "aliases": cycles - 1,
                   "repair_points": 0, "negative_H_points": 0, "negative_q_points": 0}, "contract counts")
        require(len(a["schedule"]) == 5 and len(a["csv_tokens"]) == 6, "contract schedule shape")
        changes = sum(float(t) != load for t, load in zip(a["csv_tokens"][1:], a["schedule"])) * cycles
        equal(a["csv_load_differences"], changes, "contract load differences")


def check_invocation(event, spec):
    scope(event)
    identities = [a["identity"] for a in spec["archives"]]
    fields(event, {"kind": "invocation", "receipt_schema": spec["receipt_schema"],
                   "ordered_archive_identities": identities,
                   "archive_order_sha256": sha256(canonical(identities)),
                   "verifier": spec["verifier"], "hostname": spec["runtime"]["hostname"]}, "invocation")
    integer(event["pid"], "producer PID", 1)
    roots = [a["archive_root"] for a in identities]
    equal([windows_path(p) for p in event["root_arguments"]],
          [windows_path(p) for p in roots], "root arguments")
    argv = event["argv"]
    require(type(argv) is list and len(argv) == 4, "invocation argv shape")
    require(PureWindowsPath(argv[0]).name == "validate_fixed_weight_legacy_native_archives.py",
            "wrong runner in argv")
    equal([windows_path(p) for p in argv[1:]], [windows_path(p) for p in roots], "argv roots")
    environment = event["environment"]
    fields(environment["torch_runtime"], {k: spec["runtime"][k] for k in
           ("num_threads", "num_interop_threads", "cuda_version")}, "Torch runtime")
    deps = environment["dependency_fingerprints"]
    equal([d["distribution"] for d in deps], ["torch", "numpy", "h5py"], "dependency order")
    for dep in deps:
        require(type(dep["version"]) is str and bool(dep["version"]), "dependency version missing")
        digest(dep["module_file_sha256"], "dependency module hash")
        for key in ("record_sha256", "metadata_sha256"):
            if dep[key] is not None:
                digest(dep[key], "dependency " + key)
    require(deps[0]["version"].endswith("+cpu"), "expected CPU Torch distribution")
    digest(environment["torch_runtime"]["torch_config_sha256"], "Torch config hash")


def check_binding(event, archive, spec):
    scope(event)
    identity = archive["identity"]
    name = identity["archive"]
    fields(event, {"kind": "binding", "archive": name, "producer_run_id": None,
                   "adapter_trajectory_id": archive["trajectory_id"],
                   **{k: identity[k] for k in ("index_sha256", "manifest_sha256", "config_sha256",
                                               "static_sha256", "reference_inventory_sha256")},
                   "physical_states": archive["physical_states"], "aliases": archive["aliases"],
                   "schedule": archive["schedule"], "rule": spec["rule"],
                   "expected_negative_H_support": 0, "expected_negative_q_support": 0,
                   "declared_source_arithmetic_blobs": spec["declared_source_arithmetic_blobs"],
                   "source_arithmetic_runtime_verified": False,
                   "source_arithmetic_scope": (
                       "declared source-side identifiers only; this adapter does not open a "
                       "producer source checkout or verify arithmetic blobs at runtime"),
                   "run_summary_relative_path": "run_summary.json", "execution_mode": "replay_existing",
                   "logical_state_count": archive["logical_states"],
                   "cycle_count": identity["cycles"]}, "binding " + name)
    integer(event["manifest_members"], "manifest members", 1)
    equal(event["record"], {"trajectory_id": archive["trajectory_id"], "condition_id": name,
          "reference_id": spec["producer_commit"], "mesh_id": spec["mesh_id"], "split": "train",
          "qualification_ref": spec["qualification_ref"], "semantics": spec["semantics"],
          "evidence_domain": "synthetic", "expected_state_count": archive["physical_states"],
          "material_values": spec["material_values"], "boundary_family": spec["boundary_family"]}, "trajectory record")
    provenance = event["producer_provenance"]
    fields(provenance, {"reference_inventory_sha256": identity["reference_inventory_sha256"],
                        "source_after_verified": True}, "producer provenance")
    count = integer(provenance["source_after_file_count"], "source file count", 1)
    equal(provenance["source_after_reference_file_count"], count, "source reference count")
    for key in ("source_receipt_sha256", "source_after_receipt_sha256"):
        equal(digest(event[key], key), digest(provenance[key], key), "repeated " + key)
    summary = event["run_summary_contract"]
    fields(summary, {"run_summary_relative_path": "run_summary.json", "execution_mode": "replay_existing",
                     "logical_state_count": archive["logical_states"], "cycle_count": identity["cycles"],
                     "unique_payload_count": archive["physical_states"], "sealed": True}, "source summary")
    equal(digest(event["run_summary_sha256"], "summary hash"),
          digest(summary["run_summary_sha256"], "summary hash"), "repeated summary hash")
    static = event["static_receipt"]
    fields(static, {"source_static_sha256": identity["static_sha256"], "node_order": "native",
                    "element_order": "native", "gauss_point_order": "native quadrature",
                    "thickness": 1.0, "nodal_weight_shape": [86756], "gp_weight_shape": [86408, 4]}, "static receipt")
    mesh_id = "q4:" + digest(static["node_coordinates_sha256"], "coordinates hash") + ":" + digest(static["cells_0based_sha256"], "cells hash")
    equal(mesh_id, spec["mesh_id"], "static mesh identity")
    for key in ("gauss_weight_sha256", "Nxi_sha256", "dNdxi_sha256", "nodal_weight_sha256", "gp_weight_sha256"):
        digest(static[key], key)


def check_adapted(event, archive, ordinal, spec):
    cycle, substep = (1, 0) if ordinal == 0 else ((ordinal - 1) // 5 + 1, (ordinal - 1) % 5 + 1)
    fields(event, {"kind": "adapted", "archive": archive["identity"]["archive"],
                   "ordinal": ordinal, "key": f"c{cycle:04d}_s{substep:02d}",
                   "initial": ordinal == 0, "rule": spec["rule"],
                   "source_timing": "pre_cycle_committed" if ordinal == 0 else "post_history_commit",
                   "raw_csv_load": archive["csv_tokens"][substep],
                   "canonical_load": 0.0 if substep == 0 else archive["schedule"][substep - 1],
                   "repairs": [], "raw_arrays_preserved": True}, "adapted")
    digest(event["payload_sha256"], "payload hash")
    require(type(event["raw_array_digests"]) is list and len(event["raw_array_digests"]) == 3,
            "expected u/d/history array hashes")
    for h in event["raw_array_digests"]:
        digest(h, "raw array hash")
    source_error = number(event["raw_f_source_max_relative_error"], "source f relative error")
    require(source_error <= 8 * math.ulp(1.0), "source f exceeds the unchanged 8eps threshold")
    number(event["raw_f_stable_max_relative_error"], "stable f relative difference")


def verify_receipt(receipt_bytes, execution, spec):
    """Verify in-memory inputs; this function performs no file or network IO."""
    validate_contract(spec)
    require("code_commit" not in execution,
            "execution receipt: obsolete code_commit field; use verifier_source_commit")
    fields(execution, {"schema": spec["execution_schema"], "exit_code": 0,
                       "verifier_source_commit": spec["verifier_source_commit"],
                       "receipt_sha256": sha256(receipt_bytes),
                       "controller_sha256": spec["controller"]["sha256"],
                       "runner_started": True, "launcher_error": None,
                       "training": False, "solver": False,
                       "originals_modified": False}, "execution receipt")
    require(receipt_bytes.endswith(b"\n"), "truncated receipt: missing final newline")
    lines = receipt_bytes.splitlines()
    require(len(lines) == spec["total_event_count"], "receipt event count differs")
    events = [parse_object(line, f"receipt line {i + 1}") for i, line in enumerate(lines)]
    check_invocation(events[0], spec)
    stream_hash = sha256(b"".join(canonical(event) + b"\n" for event in events[:-1]))
    completion = events[-1]
    identities = [a["identity"] for a in spec["archives"]]
    fields(completion, {"kind": "complete", "receipt_schema": spec["receipt_schema"],
           "archives": 3, "archive_order_sha256": sha256(canonical(identities)),
           "ordered_archive_identities": identities, "conditions": [a["archive"] for a in identities],
           "event_count_before_complete": spec["event_count_before_complete"],
           "event_stream_sha256_before_complete": stream_hash,
           "total_physical_states": spec["total_physical_states"], "total_transitions": spec["total_transitions"],
           "verifier_bundle_sha256": spec["verifier"]["bundle_sha256"],
           "verifier_script_sha256": spec["verifier"]["script"]["sha256"],
           "verifier_bundle_unchanged": True, "test_conditions": 0, "rule": spec["rule"]}, "complete")
    scope(completion)
    number(completion["elapsed_seconds"], "total elapsed time")
    position, reports, summaries = 1, [], []
    for archive in spec["archives"]:
        check_binding(events[position], archive, spec)
        position += 1
        rows = events[position:position + archive["physical_states"]]
        for ordinal, event in enumerate(rows):
            check_adapted(event, archive, ordinal, spec)
        require(len({r["payload_sha256"] for r in rows}) == len(rows), "duplicate physical payload hash")
        position += len(rows)
        admitted = events[position]
        position += 1
        expected = {"archive": archive["identity"]["archive"], "archive_identity": archive["identity"],
                    "expected_physical_states": len(rows), "expected_transitions": len(rows) - 1,
                    "states": len(rows), "transitions": len(rows) - 1,
                    "repair_points": sum(len(r["repairs"]) for r in rows),
                    "csv_load_differences": sum(float(r["raw_csv_load"]) != r["canonical_load"] for r in rows),
                    "negative_H_points": 0, "negative_q_points": 0}
        fields(admitted, {"kind": "admitted", **expected,
                         "qualification_scope": spec["qualification_scope"]}, "admitted")
        for key in ("repair_points", "csv_load_differences", "negative_H_points", "negative_q_points"):
            equal(expected[key], archive[key], "frozen summary " + key)
        scope(admitted)
        elapsed = number(admitted["elapsed_seconds"], "archive elapsed time")
        summaries.append({**expected, "elapsed_seconds": elapsed})
        reports.append({**expected, "source_f_max_relative_error": max(r["raw_f_source_max_relative_error"] for r in rows),
                        "stable_f_max_relative_difference": max(r["raw_f_stable_max_relative_error"] for r in rows)})
    require(position == len(events) - 1, "unexpected trailing receipt events")
    equal(completion["per_archive"], summaries, "complete per-archive summaries")
    require(completion["elapsed_seconds"] >= sum(s["elapsed_seconds"] for s in summaries),
            "total elapsed time is shorter than its archives")
    return {"status": "receipt_verified", "verifier_source_commit": spec["verifier_source_commit"],
            "controller_sha256": spec["controller"]["sha256"],
            "receipt_sha256": sha256(receipt_bytes), "contract_sha256": sha256(canonical(spec)),
            "event_stream_sha256_before_complete": stream_hash,
            "event_count": len(events), "per_archive": reports,
            "total_physical_states": spec["total_physical_states"], "total_transitions": spec["total_transitions"],
            "test_conditions": 0, "rule": spec["rule"], "archive_payloads_opened": False,
            "scientific_arrays_recomputed": False, "training_authorized": False,
            "scope": "Local receipt consistency against an independent frozen contract; development conditions only. Numerical checks and alpha-increment preservation are assertions of the reviewed, completed runner. No teacher or equilibrium qualification."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="downloaded JSONL, including final complete event")
    parser.add_argument("--execution-receipt", type=Path, required=True,
                        help="controller execution JSON: matching schema/controller_sha256, exit_code=0, runner_started=true, launcher_error=null, training/solver/originals_modified=false, verifier_source_commit (staged runner/modules source, not current HEAD), and receipt_sha256 of downloaded JSONL bytes; all are required; obsolete code_commit is rejected")
    parser.add_argument("--contract", type=Path, required=True,
                        help="separately reviewed frozen expected spec, e.g. fem_overlay/fixed_weight_legacy_receipt_contract_20261024.json; never derive it from the tested log")
    args = parser.parse_args(argv)
    try:
        result = verify_receipt(args.receipt.read_bytes(),
            parse_object(args.execution_receipt.read_bytes(), "execution receipt"),
            parse_object(args.contract.read_bytes(), "expected contract"))
    except (OSError, KeyError, TypeError, ReceiptError) as exc:
        print(json.dumps({"status": "receipt_rejected", "reason": str(exc)}, allow_nan=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
