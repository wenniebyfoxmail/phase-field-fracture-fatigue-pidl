#!/usr/bin/env python3
"""Collect genuine D3 case shards; metadata-only checks or producer GPU scoring."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from window_inputs import CASES, PARTITION_SCHEMA, SCHEMA, bound_file, read_json, sha256, validate_budget, validate_case_partition

SCORER = HERE / "score_paired_windows.py"
SLOTS = tuple(f"{case}/s{step}" for case, (_, steps) in CASES.items() for step in steps)
TIGHT_SLOTS = {f"c{cycle}/s{step}" for cycle in (1, 83) for step in (2, 4)}
IDENTITY_FILES = {
    "collector_sha256": Path(__file__), "scorer_sha256": SCORER,
    "diagnostics_sha256": HERE / "native_q4_diagnostics.py",
    "q4_geometry_sha256": ROOT / "tools/s04_e011_analysis/run_multicycle_cross_replay.py",
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def same(first, second, label):
    require(json.dumps(first, sort_keys=True, allow_nan=False) ==
            json.dumps(second, sort_keys=True, allow_nan=False), label)


def read_collection(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate collection key/case: {key}")
            result[key] = value
        return result
    def reject(value):
        raise ValueError(f"nonfinite collection value: {value}")
    return json.loads(Path(path).read_text(), object_pairs_hook=unique, parse_constant=reject)


def resolved_ref(spec, root):
    path = bound_file(spec, root)
    return dict(path=str(path), sha256=spec["sha256"])


def target_ref(spec, root):
    if spec is None:
        return None
    require(isinstance(spec, dict) and set(spec) == {"snapshot", "admission"}, "target needs actual snapshot/admission or null")
    return {name: resolved_ref(ref, root) for name, ref in spec.items()}


def prepare_collection(path):
    """File/schema/hash checks only; no torch, field evaluation or assembly."""
    path = Path(path).resolve()
    collection = read_collection(path)
    require(set(collection) == {"schema", "case_runs", "targets_catalog", *IDENTITY_FILES}, "collection keys differ")
    require(collection["schema"] == "s04_e036_case_run_collection_v1", "wrong collection schema")
    require(isinstance(collection["case_runs"], dict) and set(collection["case_runs"]) == set(CASES), "declare exactly four case records, using null when absent")
    for name, source in IDENTITY_FILES.items():
        require(collection[name] == sha256(source), f"current postprocessing identity differs: {name}")
    catalog_path = bound_file(collection["targets_catalog"], path.parent)
    catalog = read_json(catalog_path)
    require(catalog.get("schema") == "s04_e036_d3_targets_catalog_v1", "wrong fixed F1 catalog schema")
    require(set(catalog) <= {"schema", "targets", "reference_tightening", "training_manifest", "status"}
            and set(catalog.get("targets", {})) == set(SLOTS), "F1 catalog must preserve all twelve slots, unavailable targets null")
    targets = {slot: target_ref(spec, catalog_path.parent) for slot, spec in catalog["targets"].items()}
    require(isinstance(catalog.get("reference_tightening"), dict)
            and set(catalog["reference_tightening"]) == TIGHT_SLOTS, "declare the four reference sensitivities, unavailable values null")
    sensitivities = {}
    for slot, spec in catalog["reference_tightening"].items():
        if spec is None:
            sensitivities[slot] = None
            continue
        require(isinstance(spec, dict) and set(spec) == {"state_slot", "target", "standard_policy", "tightened_policy"}
                and spec["state_slot"] == slot and spec["target"] is not None, "invalid actual tightening reference")
        sensitivities[slot] = dict(spec, target=target_ref(spec["target"], catalog_path.parent))
    # A legacy catalog's single manifest is provenance only. Actual per-case
    # manifests below remain authoritative; never pretend their hashes match.
    if catalog.get("training_manifest") is not None:
        bound_file(catalog["training_manifest"], catalog_path.parent)
    cases, shared, seen_receipts = {}, None, set()
    for case in CASES:
        spec = collection["case_runs"][case]
        if spec is None:
            cases[case] = None
            continue
        require(isinstance(spec, dict) and set(spec) == {"training_manifest", "run_receipt", "callback_lock", "producer_scorer"}, "case needs four genuine manifest/receipt/lock/producer-source references")
        refs = {name: resolved_ref(ref, path.parent) for name, ref in spec.items()}
        paths = {name: Path(ref["path"]) for name, ref in refs.items()}
        require(paths["run_receipt"].name == "run_receipt.json", "run root derives from its real run_receipt.json")
        require(str(paths["run_receipt"]) not in seen_receipts, "one real receipt cannot represent multiple case attempts")
        seen_receipts.add(str(paths["run_receipt"]))
        receipt, manifest, lock = [read_json(paths[name]) for name in ("run_receipt", "training_manifest", "callback_lock")]
        require(receipt.get("schema") == "s04_e036_paired_run_v1" and receipt.get("manifest_sha256") == refs["training_manifest"]["sha256"], "receipt does not bind this case manifest")
        require(receipt.get("requested_case") == case and receipt.get("execution_cases") == [case]
                and receipt.get("declared_cases") == list(CASES), "receipt does not record the requested single case")
        authority = receipt["authority"]
        require(authority.get("approved") is True and authority.get("requested_case") == case
                and authority.get("manifest_sha256") == refs["training_manifest"]["sha256"], "authority differs from this actual case")
        require(authority["implementation_lock"]["sha256"] == refs["callback_lock"]["sha256"], "producer implementation lock differs")
        require(manifest.get("schema") in {SCHEMA, PARTITION_SCHEMA}
                and set(manifest) == {"schema", "trajectory", "mesh", "common_problem", "cases", "budget"}, "training manifest is not the target-free D3 schema")
        require(isinstance(manifest["trajectory"], str) and manifest["trajectory"], "explicit trajectory required")
        validate_budget(manifest["budget"])
        validate_case_partition(manifest, paths["training_manifest"].parent, case)
        same(receipt["budget"], manifest["budget"], "receipt budget differs")
        mesh = resolved_ref(manifest["mesh"], paths["training_manifest"].parent)
        common = resolved_ref(manifest["common_problem"], paths["training_manifest"].parent)
        require(lock.get("schema") == "s04_e036_implementation_lock_v1" and isinstance(lock.get("files"), dict), "wrong actual producer lock")
        require(lock["files"].get("tools/s04_e036/score_paired_windows.py") == refs["producer_scorer"]["sha256"], "original scorer bytes are not bound by the producer lock")
        identity = dict(trajectory=manifest["trajectory"], mesh_sha256=mesh["sha256"],
                        common_problem_sha256=common["sha256"], budget=manifest["budget"],
                        initial_network_sha256={name: manifest["cases"][name]["network"]["sha256"] for name in CASES},
                        production_files={name: digest for name, digest in lock["files"].items()
                                          if name != "tools/s04_e036/score_paired_windows.py"})
        if shared is None:
            shared = identity
        else:
            same(identity, shared, "case shards differ in original networks, common problem, work policy or production implementation")
        cases[case] = dict(refs=refs, run_root=str(paths["run_receipt"].parent))
    return dict(collection_path=str(path), collection_sha256=sha256(path),
                targets_catalog_sha256=sha256(catalog_path), targets=targets,
                reference_tightening=sensitivities, cases=cases, shared_identity=shared,
                implementation={name: collection[name] for name in IDENTITY_FILES})


def collect(path, device):
    prepared = prepare_collection(path)
    require(platform.system() != "Darwin" and device in {"cuda", "cuda:0"}, "native scoring/replay belongs on the CUDA producer")
    require(os.environ.get("CUDA_VISIBLE_DEVICES") and "," not in os.environ["CUDA_VISIBLE_DEVICES"], "select one producer GPU explicitly")
    from score_paired_windows import score_bound_run
    results, rows = {}, []
    configured = False
    for case, (_, steps) in CASES.items():
        spec = prepared["cases"][case]
        if spec is None:
            results[case] = None
            rows.extend(dict(case=case, state_slot=f"{case}/s{step}", status="case_run_unavailable",
                             target_available=prepared["targets"][f"{case}/s{step}"] is not None,
                             accepted_endpoints={}) for step in steps)
            continue
        scoring = dict(schema="s04_e036_scoring_v1", **{name: spec["refs"][name] for name in
                       ("training_manifest", "run_receipt", "callback_lock")},
                       **{name: prepared["implementation"][name] for name in
                       ("scorer_sha256", "diagnostics_sha256", "q4_geometry_sha256")},
                       targets=prepared["targets"], reference_tightening=prepared["reference_tightening"])
        # This is an in-memory argument binding to genuine files, not a generated
        # receipt or rewritten training manifest. Every result keeps its sources.
        result = score_bound_run(spec["run_root"], scoring, Path(prepared["collection_path"]).parent, device,
            target_manifest_sha256=prepared["targets_catalog_sha256"], requested_case=case,
            configure_runtime=not configured, producer_scorer=spec["refs"]["producer_scorer"])
        configured = True
        results[case] = dict(sources=spec["refs"], result=result)
        rows.extend(dict(row, state_slot=f"{case}/s{row['state_key']['substep']}") for row in result["states"])
    require({row["state_slot"] for row in rows} == set(SLOTS) and len(rows) == 12, "collector lost or duplicated a declared physical slot")
    for row in rows:
        # A metric exception may leave a partial per-arm diagnostic dictionary.
        # Such a row never qualifies merely because its earlier status is set.
        endpoints = row.get("accepted_endpoints", {})
        row["collector_pair_eligible"] = bool(row["status"] == "both_endpoints_verified"
            and not row.get("endpoint_errors") and set(endpoints) == {"P1", "P2"}
            and all("physical" in endpoints[arm] and "optimizer_work" in endpoints[arm] for arm in ("P1", "P2")))
    verified = [row for row in rows if row["collector_pair_eligible"]]
    aggregate = None
    if len(verified) == 12 and all(results.values()) and all(prepared["targets"].values()):
        first, second = [sum(row["accepted_endpoints"][arm]["J"] for row in verified) / 12. for arm in ("P1", "P2")]
        aggregate = dict(mean_J_P1=first, mean_J_P2=second,
                         improvement=None if first == 0 else 1. - second / first,
                         weighting="equal weight for all twelve declared states",
                         interpretation="accepted endpoints; not an equal-work estimate")
    return dict(schema="s04_e036_case_collection_result_v1", collection_sha256=prepared["collection_sha256"],
                targets_catalog_sha256=prepared["targets_catalog_sha256"], implementation=prepared["implementation"],
                shared_identity=prepared["shared_identity"], declared_cases=list(CASES),
                case_results=results, states=rows, declared_states=12,
                verified_endpoint_pairs=len(verified), fixed_design_aggregate=aggregate,
                missing_case_runs=[case for case, result in results.items() if result is None],
                unavailable_target_slots=[slot for slot, spec in prepared["targets"].items() if spec is None],
                claim_boundary="Actual conditional cases only; absent/failed F1 states are not manufactured; no overall aggregate with missing or unverified pairs.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device")
    parser.add_argument("--check-inputs-only", action="store_true", help="I/O schema/hash checks only; no project solver import")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("fresh output file required")
    if args.check_inputs_only:
        prepared = prepare_collection(args.collection)
        result = dict(schema="s04_e036_case_collection_input_check_v1", status="metadata_only",
                      collection_sha256=prepared["collection_sha256"],
                      available_cases=[name for name, spec in prepared["cases"].items() if spec is not None],
                      unavailable_target_slots=[slot for slot, spec in prepared["targets"].items() if spec is None],
                      scientific_replay_performed=False, fixed_design_aggregate=None,
                      protected_scoring_ast="checked before scientific scoring; not a claim of numerical replay")
    else:
        result = collect(args.collection, args.device)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(output=str(args.output), sha256=sha256(args.output),
                         schema=result["schema"], scientific_replay_performed=not args.check_inputs_only)))


if __name__ == "__main__":
    main()
