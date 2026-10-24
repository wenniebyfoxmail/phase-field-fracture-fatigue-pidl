"""Synthetic receipt tests; standard library only, no archive or producer IO."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/verify_fixed_weight_legacy_receipt.py"
SPEC = ROOT / "fem_overlay/fixed_weight_legacy_receipt_contract_20261024.json"
loader = importlib.util.spec_from_file_location("receipt_checker", MODULE)
checker = importlib.util.module_from_spec(loader)
loader.loader.exec_module(checker)


def encode(events, newline=b"\n"):
    events = copy.deepcopy(events)
    events[-1]["event_stream_sha256_before_complete"] = checker.sha256(
        b"".join(checker.canonical(e) + b"\n" for e in events[:-1]))
    return newline.join(checker.canonical(e) for e in events) + newline


def bound_execution(data, execution):
    return {**execution, "receipt_sha256": checker.sha256(data)}


def verify(data, execution, spec):
    return checker.verify_receipt(data, bound_execution(data, execution), spec)


def fixture():
    spec = json.loads(SPEC.read_text())
    scope = {"training_started": False, "solver_started": False, "originals_modified": False}
    identities = [a["identity"] for a in spec["archives"]]
    roots = [a["archive_root"] for a in identities]
    h = "a" * 64
    deps = [{"distribution": name, "version": version, "module_file_sha256": h,
             "record_sha256": h, "metadata_sha256": h}
            for name, version in (("torch", "2.4.1+cpu"), ("numpy", "2.4.4"), ("h5py", "3.16.0"))]
    invocation = {"kind": "invocation", **scope, "receipt_schema": spec["receipt_schema"],
                  "ordered_archive_identities": identities,
                  "archive_order_sha256": checker.sha256(checker.canonical(identities)),
                  "verifier": copy.deepcopy(spec["verifier"]), "hostname": "CITPC12", "pid": 1234,
                  "root_arguments": roots,
                  "argv": [r"C:\bundle\scripts\validate_fixed_weight_legacy_native_archives.py", *roots],
                  "environment": {"dependency_fingerprints": deps,
                                  "torch_runtime": {"num_threads": 2, "num_interop_threads": 2,
                                                    "cuda_version": None, "torch_config_sha256": h}}}
    events, summaries = [invocation], []
    for archive in spec["archives"]:
        identity = archive["identity"]
        name = identity["archive"]
        provenance = {"source_receipt_sha256": h, "source_after_receipt_sha256": h,
                      "reference_inventory_sha256": identity["reference_inventory_sha256"],
                      "source_after_verified": True, "source_after_file_count": 10,
                      "source_after_reference_file_count": 10}
        summary = {"run_summary_relative_path": "run_summary.json", "run_summary_sha256": h,
                   "execution_mode": "replay_existing", "logical_state_count": archive["logical_states"],
                   "cycle_count": identity["cycles"], "unique_payload_count": archive["physical_states"], "sealed": True}
        coordinates, cells = spec["mesh_id"].split(":")[1:]
        static = {"source_static_sha256": identity["static_sha256"], "node_order": "native",
                  "element_order": "native", "gauss_point_order": "native quadrature", "thickness": 1.0,
                  "nodal_weight_shape": [86756], "gp_weight_shape": [86408, 4],
                  "node_coordinates_sha256": coordinates, "cells_0based_sha256": cells,
                  **{k: h for k in ("gauss_weight_sha256", "Nxi_sha256", "dNdxi_sha256", "nodal_weight_sha256", "gp_weight_sha256")}}
        binding = {"kind": "binding", **scope, "archive": name, "producer_run_id": None,
                   "adapter_trajectory_id": archive["trajectory_id"],
                   **{k: identity[k] for k in ("index_sha256", "manifest_sha256", "config_sha256", "static_sha256", "reference_inventory_sha256")},
                   "physical_states": archive["physical_states"], "aliases": archive["aliases"],
                   "manifest_members": 2000, "schedule": archive["schedule"], "rule": spec["rule"],
                   "expected_negative_H_support": 0, "expected_negative_q_support": 0,
                   "declared_source_arithmetic_blobs": spec["declared_source_arithmetic_blobs"],
                   "source_arithmetic_runtime_verified": False,
                   "source_arithmetic_scope": (
                       "declared source-side identifiers only; this adapter does not open a "
                       "producer source checkout or verify arithmetic blobs at runtime"),
                   "producer_provenance": provenance, "run_summary_contract": summary,
                   "source_receipt_sha256": h, "source_after_receipt_sha256": h,
                   **{k: summary[k] for k in ("run_summary_relative_path", "run_summary_sha256", "execution_mode", "logical_state_count", "cycle_count")},
                   "static_receipt": static,
                   "record": {"trajectory_id": archive["trajectory_id"], "condition_id": name,
                              "reference_id": spec["producer_commit"], "mesh_id": spec["mesh_id"], "split": "train",
                              "qualification_ref": spec["qualification_ref"], "semantics": spec["semantics"],
                              "evidence_domain": "synthetic", "expected_state_count": archive["physical_states"],
                              "material_values": spec["material_values"], "boundary_family": spec["boundary_family"]}}
        events.append(binding)
        for ordinal in range(archive["physical_states"]):
            c, s = (1, 0) if ordinal == 0 else ((ordinal - 1) // 5 + 1, (ordinal - 1) % 5 + 1)
            events.append({"kind": "adapted", "archive": name, "ordinal": ordinal,
                           "key": f"c{c:04d}_s{s:02d}", "initial": ordinal == 0, "rule": spec["rule"],
                           "source_timing": "pre_cycle_committed" if ordinal == 0 else "post_history_commit",
                           "raw_csv_load": archive["csv_tokens"][s],
                           "canonical_load": 0.0 if s == 0 else archive["schedule"][s - 1],
                           "repairs": [], "raw_arrays_preserved": True,
                           "payload_sha256": checker.sha256(f"{name}:{ordinal}".encode()),
                           "raw_array_digests": [h, h, h], "raw_f_source_max_relative_error": 1e-16,
                           "raw_f_stable_max_relative_error": 4e-15})
        completion = {"archive": name, "archive_identity": identity,
                      "expected_physical_states": archive["physical_states"], "expected_transitions": archive["transitions"],
                      "states": archive["physical_states"], "transitions": archive["transitions"],
                      **{k: archive[k] for k in ("repair_points", "csv_load_differences", "negative_H_points", "negative_q_points")},
                      "elapsed_seconds": 10.0}
        events.append({"kind": "admitted", **completion, **scope, "qualification_scope": spec["qualification_scope"]})
        summaries.append(completion)
    events.append({"kind": "complete", **scope, "receipt_schema": spec["receipt_schema"], "archives": 3,
                   "archive_order_sha256": invocation["archive_order_sha256"], "ordered_archive_identities": identities,
                   "conditions": [a["archive"] for a in identities], "per_archive": summaries,
                   "total_physical_states": 1368, "total_transitions": 1365, "elapsed_seconds": 31.0,
                   "verifier_bundle_sha256": spec["verifier"]["bundle_sha256"],
                   "verifier_script_sha256": spec["verifier"]["script"]["sha256"],
                   "verifier_bundle_unchanged": True, "test_conditions": 0, "rule": spec["rule"],
                   "event_count_before_complete": 1375, "event_stream_sha256_before_complete": ""})
    execution = {"schema": spec["execution_schema"], "exit_code": 0,
                 "verifier_source_commit": spec["verifier_source_commit"],
                 "controller_sha256": spec["controller"]["sha256"],
                 "runner_started": True, "launcher_error": None,
                 "training": False, "solver": False, "originals_modified": False}
    return events, execution, spec


class ReceiptTests(unittest.TestCase):
    def test_independent_contract_matches_the_frozen_code_manifest(self):
        spec = json.loads(SPEC.read_text())
        checker.validate_contract(spec)
        manifest = (ROOT / spec["bundle_manifest_path"]).read_bytes()
        self.assertEqual(checker.sha256(manifest), spec["bundle_manifest_sha256"])
        listed = dict((path, digest) for digest, path in
                      (line.split() for line in manifest.decode().splitlines()))
        verifier = spec["verifier"]
        items = [verifier["script"], *verifier["source_modules"]]
        self.assertEqual({item["path"]: item["sha256"] for item in items}, listed)
        for item in [*items, spec["controller"]]:
            code = (ROOT / item["path"]).read_bytes()
            self.assertEqual(len(code), item["bytes"])
            self.assertEqual(checker.sha256(code), item["sha256"])

    def test_complete_lf_and_crlf_receipts_pass_without_mutating_inputs(self):
        events, execution, spec = fixture()
        original = copy.deepcopy((events, execution, spec))
        for newline in (b"\n", b"\r\n"):
            result = verify(encode(events, newline), execution, spec)
            self.assertEqual(result["total_physical_states"], 1368)
            self.assertEqual(result["total_transitions"], 1365)
            self.assertFalse(result["scientific_arrays_recomputed"])
            self.assertEqual(result["controller_sha256"], spec["controller"]["sha256"])
        self.assertEqual((events, execution, spec), original)

    def test_tampering_fails_even_after_a_self_consistent_stream_rehash(self):
        mutations = {
            "wrong ordinal": lambda e: e[3].update(ordinal=2),
            "missing initial": lambda e: e[2].update(key="c0001_s01"),
            "wrong timing": lambda e: e[2].update(source_timing="post_history_commit"),
            "load precision": lambda e: e[5].update(canonical_load=float(e[5]["raw_csv_load"])),
            "scope expansion": lambda e: e[1].update(source_arithmetic_runtime_verified=True),
            "invented run": lambda e: e[1].update(producer_run_id="new-run"),
            "bool ordinal": lambda e: e[2].update(ordinal=False),
            "raw mutation": lambda e: e[2].update(raw_arrays_preserved=False),
            "repair": lambda e: e[2].update(repairs=[{}]),
            "fatigue failure": lambda e: e[2].update(raw_f_source_max_relative_error=2e-15),
            "summary": lambda e: e[-1]["per_archive"][0].update(transitions=624),
            "source inventory": lambda e: e[1]["producer_provenance"].update(reference_inventory_sha256="b" * 64),
            "wrong schema": lambda e: e[0].update(receipt_schema="v3"),
            "test claim": lambda e: e[-1].update(test_conditions=1),
            "wrong roots": lambda e: e[0]["root_arguments"].reverse(),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                events, execution, spec = fixture()
                mutate(events)
                with self.assertRaises(checker.ReceiptError):
                    verify(encode(events), execution, spec)

    def test_self_consistent_wrong_code_bundle_does_not_replace_external_contract(self):
        events, execution, spec = fixture()
        verifier = events[0]["verifier"]
        verifier["script"]["sha256"] = "b" * 64
        verifier["bundle_sha256"] = checker.sha256(checker.canonical(
            {k: verifier[k] for k in ("script", "source_modules")}))
        events[-1]["verifier_bundle_sha256"] = verifier["bundle_sha256"]
        events[-1]["verifier_script_sha256"] = verifier["script"]["sha256"]
        with self.assertRaisesRegex(checker.ReceiptError, "verifier"):
            verify(encode(events), execution, spec)

    def test_truncated_missing_duplicated_or_reordered_events_fail(self):
        events, execution, spec = fixture()
        valid = encode(events)
        cases = [valid[:-1], valid + valid.splitlines(keepends=True)[-1],
                 b"\n".join(valid.splitlines()[1:]) + b"\n"]
        swapped = copy.deepcopy(events)
        swapped[2], swapped[3] = swapped[3], swapped[2]
        cases.append(encode(swapped))
        tampered = valid.replace(b'"raw_f_stable_max_relative_error":4e-15',
                                 b'"raw_f_stable_max_relative_error":5e-15', 1)
        cases.append(tampered)
        for data in cases:
            with self.subTest(size=len(data)), self.assertRaises(checker.ReceiptError):
                verify(data, execution, spec)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}'):
            with self.subTest(data=data), self.assertRaises(checker.ReceiptError):
                checker.parse_object(data, "test")

    def test_external_execution_failure_or_wrong_commit_fails(self):
        events, execution, spec = fixture()
        for change in ({"exit_code": 1}, {"exit_code": False}, {"verifier_source_commit": "b" * 40}):
            with self.subTest(change=change), self.assertRaises(checker.ReceiptError):
                verify(encode(events), {**execution, **change}, spec)

    def test_all_execution_fields_are_required_and_strict(self):
        events, execution, spec = fixture()
        data = encode(events)
        execution = bound_execution(data, execution)
        invalid = {"schema": "unknown", "exit_code": False,
                   "verifier_source_commit": "b" * 40, "receipt_sha256": "b" * 64,
                   "controller_sha256": "b" * 64, "runner_started": 1,
                   "launcher_error": {}, "training": 0, "solver": 0,
                   "originals_modified": 0}
        for field, bad_value in invalid.items():
            for absent in (False, True):
                with self.subTest(field=field, absent=absent):
                    changed = dict(execution)
                    if absent:
                        del changed[field]
                    else:
                        changed[field] = bad_value
                    with self.assertRaisesRegex(checker.ReceiptError, field):
                        checker.verify_receipt(data, changed, spec)
        # Diagnostic metadata is allowed but cannot replace required fields.
        result = checker.verify_receipt(data, {**execution, "hostname": "CITPC12",
                                              "wall_seconds": 42.0}, spec)
        self.assertEqual(result["status"], "receipt_verified")

    def test_controller_contract_cannot_be_replaced_by_execution_claims(self):
        events, execution, spec = fixture()
        data = encode(events)
        for field, bad_value in (("path", "scripts/other_controller.py"),
                                 ("bytes", 1), ("sha256", "b" * 64)):
            with self.subTest(field=field):
                changed = copy.deepcopy(spec)
                changed["controller"][field] = bad_value
                altered_execution = {**execution, "controller_sha256": changed["controller"]["sha256"]}
                with self.assertRaisesRegex(checker.ReceiptError, "controller"):
                    verify(data, altered_execution, changed)

    def test_obsolete_commit_field_and_wrong_contract_source_are_rejected(self):
        for target in ("execution", "contract"):
            for retain_new in (False, True):
                with self.subTest(target=target, retain_new=retain_new):
                    events, execution, spec = fixture()
                    changed = execution if target == "execution" else spec
                    changed["code_commit"] = changed["verifier_source_commit"]
                    if not retain_new:
                        del changed["verifier_source_commit"]
                    with self.assertRaisesRegex(checker.ReceiptError, "obsolete code_commit"):
                        verify(encode(events), execution, spec)
        events, execution, spec = fixture()
        spec["verifier_source_commit"] = execution["verifier_source_commit"] = "b" * 40
        with self.assertRaisesRegex(checker.ReceiptError, "verifier_source_commit"):
            verify(encode(events), execution, spec)

    def test_successful_execution_receipt_cannot_be_reused_for_another_log(self):
        events, execution, spec = fixture()
        original = encode(events)
        stale = bound_execution(original, execution)
        events[0]["pid"] += 1
        other_run = encode(events)
        with self.assertRaisesRegex(checker.ReceiptError, "receipt_sha256"):
            checker.verify_receipt(other_run, stale, spec)
        with self.assertRaisesRegex(checker.ReceiptError, "receipt_sha256"):
            checker.verify_receipt(original, execution, spec)

    def test_cli_reads_only_named_local_inputs_and_reports_to_stdout(self):
        events, execution, spec = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = encode(events, b"\r\n")
            files = {root / "receipt.jsonl": data,
                     root / "execution.json": checker.canonical(bound_execution(data, execution)),
                     root / "contract.json": checker.canonical(spec)}
            for path, data in files.items():
                path.write_bytes(data)
            result = subprocess.run([sys.executable, "-I", "-B", str(MODULE), str(root / "receipt.jsonl"),
                                     "--execution-receipt", str(root / "execution.json"),
                                     "--contract", str(root / "contract.json")],
                                    cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "receipt_verified")
            self.assertEqual({p: p.read_bytes() for p in root.iterdir()}, files)


if __name__ == "__main__":
    unittest.main()
