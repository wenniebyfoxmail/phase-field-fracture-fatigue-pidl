"""Synthetic-only tests for the read-only saved-state posthoc verifier."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

import verify_saved_state_audit_posthoc as verifier


TEST_LAUNCHER_PATH = r"C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe"
TEST_LAUNCHER_SHA256 = "e52553f941ceb9e715d239e7a211501ce5d6096eeeb90fb161b7bfedf6a61dab"


def archive_root(name: str) -> str:
    return rf"C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\{name}"


def admission(name: str) -> dict[str, object]:
    lock = verifier.LOCKS[name]
    cycles = int(lock["cycles"])
    payloads = 1 + cycles * 5
    return {
        "archive_name": name,
        "archive_root": archive_root(name),
        "manifest_sha256": lock["manifest_sha256"],
        "manifest_member_count": 12,
        "provenance": {
            "source_commit": verifier.SOURCE_COMMIT,
            "source_dirty": False,
            "run_id": lock["run_id"],
            "sealed": True,
            "unique_payload_count": payloads,
            "source_receipt_sha256": lock["source_receipt_sha256"],
            "run_summary_sha256": lock["run_summary_sha256"],
        },
        "logical_state_count": cycles * 6,
        "payload_inventory": {
            "unique_payload_count": payloads,
            "state_directory_membership_verified": True,
            "manifest_payload_binding_verified": True,
        },
        "matlab_authoritative": True,
        "payloads_decoded": False,
    }


def initial_contract() -> dict[str, bool]:
    return {
        "u_exact_zero": True,
        "H_alpha_q_exact_zero": True,
        "f_exact_one": True,
        "d_within_unit_interval": True,
        "undamaged_and_degraded_energy_exact_zero": True,
        "zero_load_metadata_exact": True,
    }


def source_record() -> dict[str, object]:
    blobs = []
    for relative, expected in verifier.SOURCE_INTERFACE_BLOBS:
        blobs.append(
            {
                "relative_path": relative,
                "git_blob": expected or "a" * 40,
                "expected_git_blob": expected or "",
            }
        )
    binaries = []
    for name in (
        "phase_field.mex.fem.assembly.equilibrium.AMOR",
        "phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE",
    ):
        binaries.append(
            {"qualified_name": name, "path": rf"C:\producer\{name}.mexw64", "sha256": "b" * 64}
        )
    return {
        "root": r"C:\producer",
        "commit": verifier.SOURCE_COMMIT,
        "equilibrium_assembler": "phase_field.mex.fem.assembly.equilibrium.AMOR",
        "phase_assembler": "phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE",
        "interface_blobs": blobs,
        "runtime_binaries": binaries,
        "runtime_binary_source_equivalence_proved": False,
    }


def interpreter() -> dict[str, object]:
    return {
        "implementation": "cpython",
        "version": [3, 11, 9],
        "executable": r"C:\Python311\python.exe",
        "dont_write_bytecode": True,
        "no_user_site": True,
        "safe_path": True,
    }


def preflight_record(admissions: list[dict[str, object]]) -> dict[str, object]:
    reports = []
    for admitted in admissions:
        name = str(admitted["archive_name"])
        lock = verifier.LOCKS[name]
        cycles = int(lock["cycles"])
        payloads = 1 + cycles * 5
        reports.append(
            {
                "archive_name": name,
                "archive_root": admitted["archive_root"],
                "run_id": lock["run_id"],
                "producer_commit": verifier.SOURCE_COMMIT,
                "u_max": lock["u_max"],
                "logical_rows": cycles * 6,
                "unique_physical_states": payloads,
                "physical_transitions": cycles * 5,
                "identity_hashes": {
                    "manifest": lock["manifest_sha256"],
                    "state_index": lock["index_sha256"],
                    "static": lock["static_sha256"],
                    "config": lock["config_sha256"],
                    "source_receipt": lock["source_receipt_sha256"],
                    "run_summary": lock["run_summary_sha256"],
                },
                "manifest": {"files": 12, "bytes": 4096},
                "payloads": {"unique_payloads": payloads, "payload_bytes": 8192},
            }
        )
    return {
        "schema": "fixed_weight_saved_state_preflight_v1",
        "status": "verified",
        "scope": "supplemental byte/topology cross-check only; no MAT/HDF5 scientific decode",
        "archive_admission_authoritative": False,
        "interpreter": interpreter(),
        "producer_commit": verifier.SOURCE_COMMIT,
        "archives": reports,
        "total_physical_transitions": 880,
        "raw_archives_modified": False,
        "matlab_started": False,
        "fem_solver_started": False,
        "training_started": False,
    }


def receipt_record(admissions: list[dict[str, object]]) -> dict[str, object]:
    archive_receipts = []
    for admitted in admissions:
        name = str(admitted["archive_name"])
        lock = verifier.LOCKS[name]
        archive_receipts.append(
            {
                "archive_root": admitted["archive_root"],
                "run_id": lock["run_id"],
                "source_commit": verifier.SOURCE_COMMIT,
                "matlab_archive_admission": copy.deepcopy(admitted),
                "physical_transitions": int(lock["cycles"]) * 5,
                "initial_semantics": verifier.INITIAL_SEMANTICS,
                "initial_contract": initial_contract(),
                "history_input_rule": (
                    "target d/psi with immediately previous physical d/history; "
                    "target committed history is never fed back as history_prev"
                ),
                "mechanics_external_load": "zero after verified absence of Neumann DOFs/traction faces",
                "raw_archive_write_attempted": False,
                "fem_solver_started": False,
                "not_a_staggered_convergence_test": True,
            }
        )
    return {
        "schema": verifier.AUDIT_SCHEMA,
        "status": verifier.AUDIT_STATUS,
        "scope": verifier.AUDIT_SCOPE,
        "package": {
            "root": r"C:\q4runs\fixed_weight_saved_state_numerical_audit_20261024",
            "manifest_sha256": verifier.PACKAGE_MANIFEST_SHA256,
            "members_verified": 6,
        },
        "source": source_record(),
        "matlab_archive_admission": copy.deepcopy(admissions),
        "supplemental_python_preflight": {
            "path": r"C:\q4runs\audit_out\preflight.json",
            "schema": "fixed_weight_saved_state_preflight_v1",
            "status": "verified",
            "physical_transition_count": 880,
            "interpreter": interpreter(),
            "archive_admission_authoritative": False,
        },
        "python_launcher": {
            "path": TEST_LAUNCHER_PATH,
            "configured_path": TEST_LAUNCHER_PATH,
            "sha256": TEST_LAUNCHER_SHA256,
            "absolute_path_required": True,
            "archive_admission_authoritative": False,
        },
        "archive_receipts": archive_receipts,
        "physical_transition_count": 880,
        "metric_csv": r"C:\q4runs\audit_out\saved_state_transition_metrics.csv",
        "raw_archives_modified": False,
        "fem_solver_started": False,
        "native_assembler_calls_used": True,
        "training_started": False,
        "runtime_binary_source_equivalence_proved": False,
        "numerical_admission_decision": "not_evaluated",
        "not_proved": list(verifier.NOT_PROVED),
    }


def metric_row(name: str, cycle: int, substep: int, *, raw_min: str = "0") -> dict[str, str]:
    lock = verifier.LOCKS[name]
    row = {column: "0" for column in verifier.METRIC_COLUMNS}
    row.update(
        {
            "archive": name,
            "run_id": str(lock["run_id"]),
            "previous_state_key": verifier.expected_previous_state(cycle, substep),
            "target_state_key": f"c{cycle:04d}_s{substep:02d}",
            "cycle": str(cycle),
            "substep": str(substep),
            "initial_semantics": verifier.INITIAL_SEMANTICS,
            "history_exact": "1",
            "recomputed_psi_exact": "1",
            "recomputed_psi_vs_payload_max_abs": "0",
            "raw_H_min": raw_min,
            "raw_q_min": raw_min,
            "staggered_delta_d_claimed": "0",
            "staggered_fixed_point_claimed": "0",
        }
    )
    if float(raw_min) < 0:
        row["raw_H_negative_count"] = "1"
        row["raw_q_negative_count"] = "1"
    return row


class PosthocVerifierSyntheticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.admissions = [admission(name) for name in verifier.LOCKS]
        self.receipt_path = self.root / "saved_state_audit_receipt.json"
        self.metrics_path = self.root / "saved_state_transition_metrics.csv"
        self.preflight_path = self.root / "preflight.json"
        self.write_bundle()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_bundle(self, receipt: dict[str, object] | None = None,
                     preflight: dict[str, object] | None = None) -> None:
        receipt = receipt or receipt_record(self.admissions)
        preflight = preflight or preflight_record(self.admissions)
        self.receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        self.preflight_path.write_text(json.dumps(preflight, indent=2) + "\n", encoding="utf-8")
        with self.metrics_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=verifier.METRIC_COLUMNS)
            writer.writeheader()
            for name, lock in verifier.LOCKS.items():
                for cycle in range(1, int(lock["cycles"]) + 1):
                    for substep in range(1, 6):
                        # Tiny raw negative H/q values are observations, not a rejection condition.
                        raw_min = "-1e-16" if name == "hard5_u0115_stage0b" and cycle == 1 and substep == 1 else "0"
                        writer.writerow(metric_row(name, cycle, substep, raw_min=raw_min))

    def custody_kwargs(self) -> dict[str, object]:
        return {
            "relocated_evidence": True,
            "receipt_sha256": verifier.sha256_file(self.receipt_path),
            "metrics_sha256": verifier.sha256_file(self.metrics_path),
            "preflight_sha256": verifier.sha256_file(self.preflight_path),
        }

    def verify(self) -> dict[str, object]:
        return verifier.verify(
            self.receipt_path,
            self.metrics_path,
            self.preflight_path,
            **self.custody_kwargs(),
        )

    def test_valid_two_archive_bundle_is_contract_consistent(self) -> None:
        report = verifier.verify(
            self.receipt_path,
            self.metrics_path,
            self.preflight_path,
            launcher_path=TEST_LAUNCHER_PATH,
            launcher_sha256=TEST_LAUNCHER_SHA256,
            **self.custody_kwargs(),
        )
        self.assertEqual(report["status"], "verified_posthoc_contract_only")
        self.assertEqual(report["physical_transition_count"], 880)
        self.assertEqual(report["numerical_admission_decision"], "not_evaluated")
        self.assertEqual(report["physical_conclusion"], "not_established")
        self.assertEqual(report["launcher_evidence"]["mode"], "external-custody-checked")

    def test_optionally_rehashes_the_reviewed_runtime_package(self) -> None:
        package_root = Path(__file__).resolve().parent.parent / "fixed_weight_saved_state_numerical_audit_20261024"
        report = verifier.verify(
            self.receipt_path,
            self.metrics_path,
            self.preflight_path,
            package_root=package_root,
            **self.custody_kwargs(),
        )
        self.assertEqual(report["package_evidence"]["mode"], "package-bytes-checked")

    def test_rejects_admission_or_execution_claim(self) -> None:
        receipt = receipt_record(self.admissions)
        receipt["numerical_admission_decision"] = "admitted"
        self.write_bundle(receipt=receipt)
        with self.assertRaisesRegex(verifier.VerificationError, "numerical_admission_decision"):
            self.verify()

    def test_rejects_broken_cross_cycle_predecessor(self) -> None:
        with self.metrics_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            if row["archive"] == "hard5_u0115_stage0b" and row["cycle"] == "2" and row["substep"] == "1":
                row["previous_state_key"] = "c0002_s00"
                break
        with self.metrics_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=verifier.METRIC_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(verifier.VerificationError, "predecessor chain"):
            self.verify()

    def test_rejects_preflight_identity_hash_mismatch(self) -> None:
        preflight = preflight_record(self.admissions)
        preflight["archives"][0]["identity_hashes"]["config"] = "0" * 64
        self.write_bundle(preflight=preflight)
        with self.assertRaisesRegex(verifier.VerificationError, "identity_hashes.config"):
            self.verify()

    def test_rejects_python_major_four_even_though_it_is_newer(self) -> None:
        receipt = receipt_record(self.admissions)
        receipt["supplemental_python_preflight"]["interpreter"]["version"] = [4, 0, 0]
        self.write_bundle(receipt=receipt)
        with self.assertRaisesRegex(verifier.VerificationError, "CPython 3.11"):
            self.verify()

    def test_rejects_nested_admission_drift(self) -> None:
        receipt = receipt_record(self.admissions)
        receipt["archive_receipts"][0]["matlab_archive_admission"]["manifest_member_count"] = 13
        self.write_bundle(receipt=receipt)
        with self.assertRaisesRegex(verifier.VerificationError, "differs from the top-level admission"):
            self.verify()

    def test_rejects_unreviewed_receipt_claim_field(self) -> None:
        receipt = receipt_record(self.admissions)
        receipt["physical_benchmark_passed"] = True
        self.write_bundle(receipt=receipt)
        with self.assertRaisesRegex(verifier.VerificationError, "key set mismatch"):
            self.verify()

    def test_rejects_nonfinite_json_constant(self) -> None:
        self.receipt_path.write_text('{"schema": NaN}\n', encoding="utf-8")
        with self.assertRaisesRegex(verifier.VerificationError, "non-finite constant"):
            self.verify()

    def test_relocation_requires_all_three_custody_hashes(self) -> None:
        with self.assertRaisesRegex(verifier.VerificationError, "relocated evidence requires"):
            verifier.verify(
                self.receipt_path,
                self.metrics_path,
                self.preflight_path,
                relocated_evidence=True,
            )

    def test_launcher_custody_path_and_hash_are_paired(self) -> None:
        with self.assertRaisesRegex(verifier.VerificationError, "launcher-path and --launcher-sha256"):
            verifier.verify(
                self.receipt_path,
                self.metrics_path,
                self.preflight_path,
                launcher_path=TEST_LAUNCHER_PATH,
                **self.custody_kwargs(),
            )


if __name__ == "__main__":
    unittest.main()
