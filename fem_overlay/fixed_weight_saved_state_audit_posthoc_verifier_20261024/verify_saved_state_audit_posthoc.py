#!/usr/bin/env python3
"""Read-only posthoc contract verifier for the fixed-weight saved-state audit.

The verifier reads an already-produced MATLAB JSON receipt and transition CSV.
It does not open FEM archives or MAT payloads, start MATLAB, run a solver,
train a model, or write any file.  A successful result means only that the
two output files satisfy the frozen evidence contract below; it never turns
the audit into a numerical-admission or physical-benchmark conclusion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


AUDIT_SCHEMA = "fixed_weight_saved_state_numerical_audit_v1"
AUDIT_STATUS = "completed_saved_state_audit"
AUDIT_SCOPE = (
    "post-clip saved-state residual/KKT/history reassembly; "
    "not a solver-inner convergence qualification"
)
SOURCE_COMMIT = "862992a60edc7f59335365beacb5c71fc8592a7a"
INITIAL_SEMANTICS = "post_clip_zero_load_recovery_pre_cycle_committed"
PACKAGE_MANIFEST_SHA256 = "aef7e321aa4dbd587376cccc54ad09ca600c91b24cbd21dbf16d9b5a97e608be"

HEX_64 = re.compile(r"[0-9a-f]{64}")
HEX_40 = re.compile(r"[0-9a-f]{40}")
INTEGER = re.compile(r"(?:0|[1-9][0-9]*)")
WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")

PACKAGE_MEMBERS = (
    "README.md",
    "SOURCE_INTERFACE_BINDING.md",
    "fw_saved_state_audit.m",
    "make_fixed_weight_saved_state_audit_config.m",
    "preflight_fixed_weight_saved_state_archives.py",
    "run_fixed_weight_saved_state_audit.m",
)

NOT_PROVED = (
    "Newton iteration residual history",
    "staggered fixed-point convergence",
    "staggered delta-d convergence",
    "source-to-MEX build equivalence",
    "a physical benchmark or independent-test claim",
)

SOURCE_INTERFACE_BLOBS = (
    (
        "Sources/+phase_field/+mex/Modules/fem/assembly/equilibrium/amor.f90",
        "6a30c52161b2999889b7bc1b57a17cbd6e4c6db5",
    ),
    (
        "Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90",
        "d3d03cdd2ee1d894893f1cbb584a7e94947ec6b7",
    ),
    (
        "Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m",
        "e74c95ac7b4a439bbc7815561ff45c071428c065",
    ),
    ("Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.f90", None),
    ("Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_PENALTY_FATIGUE.f90", None),
    ("Sources/+phase_field/System.m", None),
    ("Sources/+phase_field/+fem/+solver/+step/params.m", None),
    ("Scripts/fatigue_fracture/solve_fatigue_fracture.m", None),
)

LOCKS: dict[str, dict[str, Any]] = {
    "hard5_u0115_stage0b": {
        "run_id": "hard5_u0115_stage0b_c23cede2bec94515a393aa291c3d6d92",
        "cycles": 103,
        "u_max": 0.115,
        "manifest_sha256": "50fd30872436b4d71800a4a38548d63b9b807cc12fbe9435d23d6963055d9cff",
        "index_sha256": "eb1cbacb52252891cb1039ec8df3bcb5cb4ce7ea2fe451476e0e241def10855a",
        "static_sha256": "a7edb0e430ae84669e3326f777360e7d73488fa41fad8fa09a038e6bbd26985e",
        "config_sha256": "0075cb117676aeb334e185b4149ea7ceefc5799e01b68d0303a56533e86ea7b5",
        "source_receipt_sha256": "b4552a7b48726fcd7596d5cb73ea59ed5362366e479eba450893a70622971b29",
        "run_summary_sha256": "7f88c2cb494b47fd7c443b84e192f98a64c74b4da75dd622422d51a96ba2072f",
    },
    "hard5_u0125_stage0b": {
        "run_id": "hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae",
        "cycles": 73,
        "u_max": 0.125,
        "manifest_sha256": "51baa00bbb8d3d33443812e3d05a48ca85d39d4f26d58654e8061a595d5df742",
        "index_sha256": "3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
        "static_sha256": "b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e",
        "config_sha256": "c4ee5a79831c7a2a327eec976d36a7ae96945ad1cbf67071e38b8d98ddd511de",
        "source_receipt_sha256": "273610cf49baae708a0be0006111c90b5ff70dc06d39f465bf88eb1fb3a39cfc",
        "run_summary_sha256": "e454fb5c46482f9a60e82ee4fb3f2988440b34544c5f03498ac9a55607e37eb2",
    },
}

METRIC_COLUMNS = (
    "archive",
    "run_id",
    "previous_state_key",
    "target_state_key",
    "cycle",
    "substep",
    "initial_semantics",
    "mechanics_free_l2",
    "mechanics_free_linf",
    "mechanics_full_l2",
    "phase_free_l2_postclip",
    "phase_free_linf_postclip",
    "phase_full_l2_postclip",
    "projected_kkt_l2_postclip",
    "projected_kkt_linf_postclip",
    "kkt_lower_active_count",
    "kkt_interior_count",
    "kkt_upper_active_count",
    "kkt_lower_primal_violation",
    "kkt_upper_primal_violation",
    "history_exact",
    "history_max_abs",
    "history_H_max_abs",
    "history_alpha_max_abs",
    "history_q_max_abs",
    "history_f_max_abs",
    "recomputed_psi_exact",
    "recomputed_psi_vs_payload_max_abs",
    "raw_H_vs_psi_max_abs",
    "raw_q_vs_payload_degraded_max_abs",
    "raw_H_min",
    "raw_q_min",
    "raw_H_negative_count",
    "raw_q_negative_count",
    "staggered_delta_d_claimed",
    "staggered_fixed_point_claimed",
)

METRIC_FLOAT_COLUMNS = (
    "mechanics_free_l2",
    "mechanics_free_linf",
    "mechanics_full_l2",
    "phase_free_l2_postclip",
    "phase_free_linf_postclip",
    "phase_full_l2_postclip",
    "projected_kkt_l2_postclip",
    "projected_kkt_linf_postclip",
    "kkt_lower_primal_violation",
    "kkt_upper_primal_violation",
    "history_max_abs",
    "history_H_max_abs",
    "history_alpha_max_abs",
    "history_q_max_abs",
    "history_f_max_abs",
    "recomputed_psi_vs_payload_max_abs",
    "raw_H_vs_psi_max_abs",
    "raw_q_vs_payload_degraded_max_abs",
    "raw_H_min",
    "raw_q_min",
)

METRIC_COUNT_COLUMNS = (
    "kkt_lower_active_count",
    "kkt_interior_count",
    "kkt_upper_active_count",
    "raw_H_negative_count",
    "raw_q_negative_count",
)


class VerificationError(ValueError):
    """The supplied evidence does not satisfy this fixed, posthoc contract."""


def fail(message: str) -> None:
    raise VerificationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Construct one JSON object while refusing ambiguous duplicate members."""
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            fail(f"JSON object repeats the key {key!r}")
        value[key] = member
    return value


def reject_nonfinite_json_constant(value: str) -> None:
    fail(f"JSON must not use the non-finite constant {value}")


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
            parse_constant=reject_nonfinite_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise VerificationError(f"{label} is not valid JSON: {exc}") from exc
    return require_object(value, label)


def require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{context} must be a JSON object")
    return value


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"{context} must be a JSON array")
    return value


def require_field(value: dict[str, Any], name: str, context: str) -> Any:
    if name not in value:
        fail(f"{context}.{name} is missing")
    return value[name]


def require_exact_keys(value: dict[str, Any], expected: tuple[str, ...], context: str) -> None:
    """Reject both omitted fields and unreviewed extra claims."""
    if len(set(expected)) != len(expected):
        raise RuntimeError(f"internal duplicate expected key in {context}")
    actual_keys = set(value)
    expected_keys = set(expected)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if unexpected:
            detail.append("unexpected=" + ",".join(unexpected))
        fail(f"{context} key set mismatch ({'; '.join(detail)})")


def require_string(value: Any, context: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        fail(f"{context} must be a nonempty string")
    return value


def require_bool(value: Any, context: str) -> bool:
    if type(value) is not bool:
        fail(f"{context} must be a JSON boolean")
    return value


def require_integral(value: Any, context: str, *, minimum: int | None = None) -> int:
    if type(value) is bool or not isinstance(value, (int, float)):
        fail(f"{context} must be an integer JSON number")
    try:
        numeric = float(value)
    except (OverflowError, ValueError) as exc:
        raise VerificationError(f"{context} must be a finite integer") from exc
    if not math.isfinite(numeric):
        fail(f"{context} must be a finite integer")
    number = int(value)
    if number != value:
        fail(f"{context} must be a finite integer")
    if minimum is not None and number < minimum:
        fail(f"{context} must be at least {minimum}")
    return number


def require_hex(value: Any, length: int, context: str) -> str:
    text = require_string(value, context).lower()
    matcher = HEX_64 if length == 64 else HEX_40
    if matcher.fullmatch(text) is None:
        fail(f"{context} must be a lowercase {length}-hex digest")
    return text


def require_finite_number(value: str, context: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{context} must be numeric") from exc
    if not math.isfinite(number):
        fail(f"{context} must be finite")
    return number


def require_csv_nonnegative_integer(value: str, context: str) -> int:
    if INTEGER.fullmatch(value) is None:
        fail(f"{context} must be a nonnegative integer")
    return int(value)


def require_csv_bool(value: str, context: str) -> bool:
    if value in ("1", "true", "True"):
        return True
    if value in ("0", "false", "False"):
        return False
    fail(f"{context} must encode a boolean as 0/1 or true/false")


def normalized_path_literal(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").casefold()


def basename_literal(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def parent_literal(value: str) -> str:
    normal = value.replace("\\", "/").rstrip("/")
    if "/" not in normal:
        fail("receipt output path must include a parent directory")
    return normal.rsplit("/", 1)[0].casefold()


def require_windows_absolute_path(value: str, context: str) -> str:
    if '"' in value or WINDOWS_ABSOLUTE.match(value) is None:
        fail(f"{context} must be an explicit Windows drive-absolute path")
    return value


def expected_previous_state(cycle: int, substep: int) -> str:
    if substep > 1:
        return f"c{cycle:04d}_s{substep - 1:02d}"
    if cycle == 1:
        return "c0001_s00"
    return f"c{cycle - 1:04d}_s05"


def verify_self_runtime() -> dict[str, Any]:
    """Require the same interpreter isolation that the receipt records.

    This is intentionally checked only for the command-line entry point: the
    module remains importable by the synthetic fixture tests without claiming
    that those test imports are production verification executions.
    """
    implementation = sys.implementation.name
    version = tuple(sys.version_info[:3])
    if implementation != "cpython" or version[0] != 3 or version[1] < 11:
        fail("posthoc verifier itself must run under CPython 3.11+")
    flags = {
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", 0)),
    }
    if tuple(flags.values()) != (True, True, True):
        fail("posthoc verifier itself must be invoked with -B -s -P")
    return {
        "implementation": implementation,
        "version": list(version),
        "executable": sys.executable,
        **flags,
    }


def verify_package_record(receipt: dict[str, Any], package_root: Path | None) -> dict[str, Any]:
    package = require_object(require_field(receipt, "package", "receipt"), "receipt.package")
    require_exact_keys(package, ("root", "manifest_sha256", "members_verified"), "receipt.package")
    require_string(require_field(package, "root", "receipt.package"), "receipt.package.root")
    manifest_digest = require_hex(
        require_field(package, "manifest_sha256", "receipt.package"),
        64,
        "receipt.package.manifest_sha256",
    )
    if manifest_digest != PACKAGE_MANIFEST_SHA256:
        fail("receipt.package.manifest_sha256 does not match the frozen audit package")
    if require_integral(
        require_field(package, "members_verified", "receipt.package"),
        "receipt.package.members_verified",
        minimum=0,
    ) != len(PACKAGE_MEMBERS):
        fail("receipt.package.members_verified is not the required six")

    report: dict[str, Any] = {
        "mode": "receipt-lock-only",
        "manifest_sha256": manifest_digest,
        "members_verified": len(PACKAGE_MEMBERS),
    }
    if package_root is None:
        return report

    if package_root.is_symlink():
        fail("--package-root must not be a symbolic link")
    root = package_root.resolve(strict=True)
    if not root.is_dir():
        fail("--package-root must be a real package directory")
    manifest = root / "PACKAGE_SHA256SUMS.txt"
    if manifest.is_symlink() or not manifest.is_file():
        fail("--package-root/PACKAGE_SHA256SUMS.txt is missing or not a regular file")
    if sha256_file(manifest) != manifest_digest:
        fail("package manifest bytes do not match receipt.package.manifest_sha256")
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if len(lines) != len(PACKAGE_MEMBERS):
        fail("package manifest must contain exactly the six reviewed members")
    for index, name in enumerate(PACKAGE_MEMBERS):
        line = lines[index]
        if len(line) != 66 + len(name) or line[64:66] != "  " or line[66:] != name:
            fail(f"package manifest line {index + 1} does not bind {name}")
        expected = require_hex(line[:64], 64, f"package manifest hash for {name}")
        member = root / name
        if member.is_symlink() or not member.is_file():
            fail(f"reviewed package member is missing or not regular: {name}")
        try:
            member.resolve(strict=True).relative_to(root)
        except ValueError as exc:
            raise VerificationError(f"reviewed package member escapes package root: {name}") from exc
        if sha256_file(member) != expected:
            fail(f"reviewed package member hash mismatch: {name}")
    report["mode"] = "package-bytes-checked"
    report["root"] = str(root)
    return report


def verify_source(receipt: dict[str, Any]) -> None:
    source = require_object(require_field(receipt, "source", "receipt"), "receipt.source")
    require_exact_keys(
        source,
        (
            "root",
            "commit",
            "equilibrium_assembler",
            "phase_assembler",
            "interface_blobs",
            "runtime_binaries",
            "runtime_binary_source_equivalence_proved",
        ),
        "receipt.source",
    )
    require_string(require_field(source, "root", "receipt.source"), "receipt.source.root")
    if require_string(require_field(source, "commit", "receipt.source"), "receipt.source.commit") != SOURCE_COMMIT:
        fail("receipt.source.commit does not match the frozen producer commit")
    if require_string(
        require_field(source, "equilibrium_assembler", "receipt.source"),
        "receipt.source.equilibrium_assembler",
    ) != "phase_field.mex.fem.assembly.equilibrium.AMOR":
        fail("receipt source equilibrium assembler is not the native AMOR entry point")
    if require_string(
        require_field(source, "phase_assembler", "receipt.source"),
        "receipt.source.phase_assembler",
    ) != "phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE":
        fail("receipt source phase assembler is not the native AT1 entry point")
    if require_bool(
        require_field(source, "runtime_binary_source_equivalence_proved", "receipt.source"),
        "receipt.source.runtime_binary_source_equivalence_proved",
    ):
        fail("receipt must not claim source-to-MEX binary equivalence")

    blobs = require_list(require_field(source, "interface_blobs", "receipt.source"), "receipt.source.interface_blobs")
    if len(blobs) != len(SOURCE_INTERFACE_BLOBS):
        fail("receipt.source.interface_blobs has the wrong member count")
    for index, (relative, locked_blob) in enumerate(SOURCE_INTERFACE_BLOBS):
        item = require_object(blobs[index], f"receipt.source.interface_blobs[{index}]")
        require_exact_keys(item, ("relative_path", "git_blob", "expected_git_blob"), f"receipt.source.interface_blobs[{index}]")
        if require_string(require_field(item, "relative_path", "interface blob"), "interface blob.relative_path") != relative:
            fail(f"receipt source interface path {index + 1} is not frozen")
        actual = require_hex(require_field(item, "git_blob", "interface blob"), 40, "interface blob.git_blob")
        expected = require_string(
            require_field(item, "expected_git_blob", "interface blob"),
            "interface blob.expected_git_blob",
            nonempty=False,
        ).lower()
        if locked_blob is not None and (actual != locked_blob or expected != locked_blob):
            fail(f"receipt source interface blob {relative} does not match its semantic lock")
        if locked_blob is None and expected != "":
            fail(f"receipt source interface blob {relative} must remain commit-bound only")

    binaries = require_list(require_field(source, "runtime_binaries", "receipt.source"), "receipt.source.runtime_binaries")
    expected_names = (
        "phase_field.mex.fem.assembly.equilibrium.AMOR",
        "phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE",
    )
    if len(binaries) != len(expected_names):
        fail("receipt.source.runtime_binaries has the wrong member count")
    for index, name in enumerate(expected_names):
        binary = require_object(binaries[index], f"receipt.source.runtime_binaries[{index}]")
        require_exact_keys(binary, ("qualified_name", "path", "sha256"), f"receipt.source.runtime_binaries[{index}]")
        if require_string(require_field(binary, "qualified_name", "runtime binary"), "runtime binary.qualified_name") != name:
            fail("receipt runtime binary name is not the native audited assembler")
        require_string(require_field(binary, "path", "runtime binary"), "runtime binary.path")
        require_hex(require_field(binary, "sha256", "runtime binary"), 64, "runtime binary.sha256")


def verify_admission(admission_value: Any, context: str) -> dict[str, Any]:
    admission = require_object(admission_value, context)
    require_exact_keys(
        admission,
        (
            "archive_name",
            "archive_root",
            "manifest_sha256",
            "manifest_member_count",
            "provenance",
            "logical_state_count",
            "payload_inventory",
            "matlab_authoritative",
            "payloads_decoded",
        ),
        context,
    )
    name = require_string(require_field(admission, "archive_name", context), f"{context}.archive_name")
    lock = LOCKS.get(name)
    if lock is None:
        fail(f"{context}.archive_name is not an admitted fixed archive")
    require_string(require_field(admission, "archive_root", context), f"{context}.archive_root")
    if require_hex(require_field(admission, "manifest_sha256", context), 64, f"{context}.manifest_sha256") != lock["manifest_sha256"]:
        fail(f"{context}.manifest_sha256 does not match {name}")
    if require_integral(require_field(admission, "manifest_member_count", context), f"{context}.manifest_member_count", minimum=1) < 1:
        fail(f"{context}.manifest_member_count is invalid")
    if require_integral(require_field(admission, "logical_state_count", context), f"{context}.logical_state_count", minimum=0) != lock["cycles"] * 6:
        fail(f"{context}.logical_state_count does not match {name}")
    if not require_bool(require_field(admission, "matlab_authoritative", context), f"{context}.matlab_authoritative"):
        fail(f"{context} must record MATLAB as the authoritative archive admission")
    if require_bool(require_field(admission, "payloads_decoded", context), f"{context}.payloads_decoded"):
        fail(f"{context} must record pre-decode archive admission")

    provenance = require_object(require_field(admission, "provenance", context), f"{context}.provenance")
    require_exact_keys(
        provenance,
        (
            "source_commit",
            "source_dirty",
            "run_id",
            "sealed",
            "unique_payload_count",
            "source_receipt_sha256",
            "run_summary_sha256",
        ),
        f"{context}.provenance",
    )
    if require_string(require_field(provenance, "source_commit", f"{context}.provenance"), f"{context}.provenance.source_commit") != SOURCE_COMMIT:
        fail(f"{context}.provenance.source_commit does not match the frozen producer commit")
    if require_bool(require_field(provenance, "source_dirty", f"{context}.provenance"), f"{context}.provenance.source_dirty"):
        fail(f"{context}.provenance.source_dirty must be false")
    if require_string(require_field(provenance, "run_id", f"{context}.provenance"), f"{context}.provenance.run_id") != lock["run_id"]:
        fail(f"{context}.provenance.run_id does not match {name}")
    if not require_bool(require_field(provenance, "sealed", f"{context}.provenance"), f"{context}.provenance.sealed"):
        fail(f"{context}.provenance.sealed must be true")
    expected_payloads = 1 + lock["cycles"] * 5
    if require_integral(require_field(provenance, "unique_payload_count", f"{context}.provenance"), f"{context}.provenance.unique_payload_count", minimum=0) != expected_payloads:
        fail(f"{context}.provenance.unique_payload_count does not match {name}")
    for key in ("source_receipt_sha256", "run_summary_sha256"):
        if require_hex(require_field(provenance, key, f"{context}.provenance"), 64, f"{context}.provenance.{key}") != lock[key]:
            fail(f"{context}.provenance.{key} does not match {name}")

    inventory = require_object(require_field(admission, "payload_inventory", context), f"{context}.payload_inventory")
    require_exact_keys(
        inventory,
        (
            "unique_payload_count",
            "state_directory_membership_verified",
            "manifest_payload_binding_verified",
        ),
        f"{context}.payload_inventory",
    )
    if require_integral(require_field(inventory, "unique_payload_count", f"{context}.payload_inventory"), f"{context}.payload_inventory.unique_payload_count", minimum=0) != expected_payloads:
        fail(f"{context}.payload_inventory.unique_payload_count does not match {name}")
    for key in ("state_directory_membership_verified", "manifest_payload_binding_verified"):
        if not require_bool(require_field(inventory, key, f"{context}.payload_inventory"), f"{context}.payload_inventory.{key}"):
            fail(f"{context}.payload_inventory.{key} must be true")
    return {
        "name": name,
        "root": normalized_path_literal(require_string(admission["archive_root"], f"{context}.archive_root")),
        "manifest_sha256": require_hex(admission["manifest_sha256"], 64, f"{context}.manifest_sha256"),
        "manifest_member_count": require_integral(admission["manifest_member_count"], f"{context}.manifest_member_count", minimum=1),
        "logical_state_count": require_integral(admission["logical_state_count"], f"{context}.logical_state_count", minimum=0),
        "matlab_authoritative": require_bool(admission["matlab_authoritative"], f"{context}.matlab_authoritative"),
        "payloads_decoded": require_bool(admission["payloads_decoded"], f"{context}.payloads_decoded"),
        "provenance": {
            "source_commit": require_string(provenance["source_commit"], f"{context}.provenance.source_commit"),
            "source_dirty": require_bool(provenance["source_dirty"], f"{context}.provenance.source_dirty"),
            "run_id": require_string(provenance["run_id"], f"{context}.provenance.run_id"),
            "sealed": require_bool(provenance["sealed"], f"{context}.provenance.sealed"),
            "unique_payload_count": require_integral(provenance["unique_payload_count"], f"{context}.provenance.unique_payload_count", minimum=0),
            "source_receipt_sha256": require_hex(provenance["source_receipt_sha256"], 64, f"{context}.provenance.source_receipt_sha256"),
            "run_summary_sha256": require_hex(provenance["run_summary_sha256"], 64, f"{context}.provenance.run_summary_sha256"),
        },
        "payload_inventory": {
            "unique_payload_count": require_integral(inventory["unique_payload_count"], f"{context}.payload_inventory.unique_payload_count", minimum=0),
            "state_directory_membership_verified": require_bool(inventory["state_directory_membership_verified"], f"{context}.payload_inventory.state_directory_membership_verified"),
            "manifest_payload_binding_verified": require_bool(inventory["manifest_payload_binding_verified"], f"{context}.payload_inventory.manifest_payload_binding_verified"),
        },
    }


def verify_admissions(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    admissions = require_list(
        require_field(receipt, "matlab_archive_admission", "receipt"),
        "receipt.matlab_archive_admission",
    )
    if len(admissions) != len(LOCKS):
        fail("receipt.matlab_archive_admission must contain exactly two archives")
    parsed: dict[str, dict[str, Any]] = {}
    for index, admission in enumerate(admissions):
        item = verify_admission(admission, f"receipt.matlab_archive_admission[{index}]")
        if item["name"] in parsed:
            fail("receipt.matlab_archive_admission duplicates an archive")
        parsed[item["name"]] = item
    if set(parsed) != set(LOCKS):
        fail("receipt.matlab_archive_admission does not cover both fixed archives")
    return parsed


def verify_archive_receipts(receipt: dict[str, Any], admissions: dict[str, dict[str, Any]]) -> None:
    entries = require_list(require_field(receipt, "archive_receipts", "receipt"), "receipt.archive_receipts")
    if len(entries) != len(LOCKS):
        fail("receipt.archive_receipts must contain exactly two archives")
    seen: set[str] = set()
    history_rule = (
        "target d/psi with immediately previous physical d/history; "
        "target committed history is never fed back as history_prev"
    )
    for index, value in enumerate(entries):
        context = f"receipt.archive_receipts[{index}]"
        item = require_object(value, context)
        require_exact_keys(
            item,
            (
                "archive_root",
                "run_id",
                "source_commit",
                "matlab_archive_admission",
                "physical_transitions",
                "initial_semantics",
                "initial_contract",
                "history_input_rule",
                "mechanics_external_load",
                "raw_archive_write_attempted",
                "fem_solver_started",
                "not_a_staggered_convergence_test",
            ),
            context,
        )
        nested = verify_admission(require_field(item, "matlab_archive_admission", context), f"{context}.matlab_archive_admission")
        name = nested["name"]
        if name in seen:
            fail("receipt.archive_receipts duplicates an archive")
        seen.add(name)
        lock = LOCKS[name]
        if nested != admissions[name]:
            fail(f"{context}.matlab_archive_admission differs from the top-level admission")
        root = require_string(require_field(item, "archive_root", context), f"{context}.archive_root")
        if normalized_path_literal(root) != normalized_path_literal(admissions[name]["root"]):
            fail(f"{context}.archive_root does not match the top-level MATLAB admission")
        if normalized_path_literal(root) != normalized_path_literal(nested["root"]):
            fail(f"{context}.archive_root does not match the nested MATLAB admission")
        if require_string(require_field(item, "run_id", context), f"{context}.run_id") != lock["run_id"]:
            fail(f"{context}.run_id does not match {name}")
        if require_string(require_field(item, "source_commit", context), f"{context}.source_commit") != SOURCE_COMMIT:
            fail(f"{context}.source_commit does not match the frozen producer commit")
        if require_integral(require_field(item, "physical_transitions", context), f"{context}.physical_transitions", minimum=0) != lock["cycles"] * 5:
            fail(f"{context}.physical_transitions does not match {name}")
        if require_string(require_field(item, "initial_semantics", context), f"{context}.initial_semantics") != INITIAL_SEMANTICS:
            fail(f"{context}.initial_semantics is not the recovered initial-state label")
        initial_contract = require_object(
            require_field(item, "initial_contract", context),
            f"{context}.initial_contract",
        )
        require_exact_keys(
            initial_contract,
            (
                "u_exact_zero",
                "H_alpha_q_exact_zero",
                "f_exact_one",
                "d_within_unit_interval",
                "undamaged_and_degraded_energy_exact_zero",
                "zero_load_metadata_exact",
            ),
            f"{context}.initial_contract",
        )
        for key in (
            "u_exact_zero",
            "H_alpha_q_exact_zero",
            "f_exact_one",
            "d_within_unit_interval",
            "undamaged_and_degraded_energy_exact_zero",
            "zero_load_metadata_exact",
        ):
            if not require_bool(
                require_field(initial_contract, key, f"{context}.initial_contract"),
                f"{context}.initial_contract.{key}",
            ):
                fail(f"{context}.initial_contract.{key} must be true")
        if require_string(require_field(item, "history_input_rule", context), f"{context}.history_input_rule") != history_rule:
            fail(f"{context}.history_input_rule is not the fixed causal history rule")
        if require_string(require_field(item, "mechanics_external_load", context), f"{context}.mechanics_external_load") != "zero after verified absence of Neumann DOFs/traction faces":
            fail(f"{context}.mechanics_external_load is not the fixed zero-traction declaration")
        if require_bool(require_field(item, "raw_archive_write_attempted", context), f"{context}.raw_archive_write_attempted"):
            fail(f"{context}.raw_archive_write_attempted must be false")
        if require_bool(require_field(item, "fem_solver_started", context), f"{context}.fem_solver_started"):
            fail(f"{context}.fem_solver_started must be false")
        if not require_bool(require_field(item, "not_a_staggered_convergence_test", context), f"{context}.not_a_staggered_convergence_test"):
            fail(f"{context}.not_a_staggered_convergence_test must be true")
    if seen != set(LOCKS):
        fail("receipt.archive_receipts does not cover both fixed archives")


def verify_interpreter(value: Any, context: str) -> tuple[str, tuple[int, int, int], str, bool, bool, bool]:
    interpreter = require_object(value, context)
    require_exact_keys(
        interpreter,
        ("implementation", "version", "executable", "dont_write_bytecode", "no_user_site", "safe_path"),
        context,
    )
    implementation = require_string(
        require_field(interpreter, "implementation", context),
        f"{context}.implementation",
    )
    if implementation != "cpython":
        fail(f"{context}.implementation must be cpython")
    version = require_list(require_field(interpreter, "version", context), f"{context}.version")
    if len(version) != 3:
        fail(f"{context}.version must have three entries")
    version_tuple = tuple(
        require_integral(part, f"{context}.version[{index}]", minimum=0)
        for index, part in enumerate(version)
    )
    if version_tuple[0] != 3 or version_tuple[1] < 11:
        fail(f"{context} did not record CPython 3.11+")
    executable = require_string(
        require_field(interpreter, "executable", context),
        f"{context}.executable",
    )
    flags = tuple(
        require_bool(require_field(interpreter, key, context), f"{context}.{key}")
        for key in ("dont_write_bytecode", "no_user_site", "safe_path")
    )
    if flags != (True, True, True):
        fail(f"{context} must record -B -s -P isolation flags")
    return implementation, version_tuple, normalized_path_literal(executable), *flags


def verify_preflight_summary(receipt: dict[str, Any]) -> tuple[str, tuple[int, int, int], str, bool, bool, bool]:
    preflight = require_object(
        require_field(receipt, "supplemental_python_preflight", "receipt"),
        "receipt.supplemental_python_preflight",
    )
    require_exact_keys(
        preflight,
        (
            "path",
            "schema",
            "status",
            "physical_transition_count",
            "interpreter",
            "archive_admission_authoritative",
        ),
        "receipt.supplemental_python_preflight",
    )
    preflight_path = require_string(
        require_field(preflight, "path", "receipt.supplemental_python_preflight"),
        "receipt.supplemental_python_preflight.path",
    )
    if basename_literal(preflight_path) != "preflight.json":
        fail("receipt.supplemental_python_preflight.path does not name preflight.json")
    if require_string(require_field(preflight, "schema", "receipt.supplemental_python_preflight"), "receipt.supplemental_python_preflight.schema") != "fixed_weight_saved_state_preflight_v1":
        fail("supplemental Python receipt schema mismatch")
    if require_string(require_field(preflight, "status", "receipt.supplemental_python_preflight"), "receipt.supplemental_python_preflight.status") != "verified":
        fail("supplemental Python receipt status mismatch")
    if require_integral(require_field(preflight, "physical_transition_count", "receipt.supplemental_python_preflight"), "receipt.supplemental_python_preflight.physical_transition_count", minimum=0) != 880:
        fail("supplemental Python receipt does not cover 880 transitions")
    if require_bool(require_field(preflight, "archive_admission_authoritative", "receipt.supplemental_python_preflight"), "receipt.supplemental_python_preflight.archive_admission_authoritative"):
        fail("supplemental Python preflight must remain non-authoritative")
    return verify_interpreter(
        require_field(preflight, "interpreter", "receipt.supplemental_python_preflight"),
        "receipt.supplemental_python_preflight.interpreter",
    )


def verify_preflight_evidence(
    path: Path,
    admissions: dict[str, dict[str, Any]],
    summary_interpreter: tuple[str, tuple[int, int, int], str, bool, bool, bool],
) -> None:
    preflight = read_json_object(path, "preflight evidence")
    require_exact_keys(
        preflight,
        (
            "schema",
            "status",
            "scope",
            "archive_admission_authoritative",
            "interpreter",
            "producer_commit",
            "archives",
            "total_physical_transitions",
            "raw_archives_modified",
            "matlab_started",
            "fem_solver_started",
            "training_started",
        ),
        "preflight evidence",
    )
    if require_string(require_field(preflight, "schema", "preflight evidence"), "preflight evidence.schema") != "fixed_weight_saved_state_preflight_v1":
        fail("preflight evidence schema mismatch")
    if require_string(require_field(preflight, "status", "preflight evidence"), "preflight evidence.status") != "verified":
        fail("preflight evidence status mismatch")
    if require_string(require_field(preflight, "scope", "preflight evidence"), "preflight evidence.scope") != "supplemental byte/topology cross-check only; no MAT/HDF5 scientific decode":
        fail("preflight evidence scope mismatch")
    if require_bool(require_field(preflight, "archive_admission_authoritative", "preflight evidence"), "preflight evidence.archive_admission_authoritative"):
        fail("preflight evidence must remain non-authoritative")
    if require_string(require_field(preflight, "producer_commit", "preflight evidence"), "preflight evidence.producer_commit") != SOURCE_COMMIT:
        fail("preflight evidence producer commit mismatch")
    if require_integral(require_field(preflight, "total_physical_transitions", "preflight evidence"), "preflight evidence.total_physical_transitions", minimum=0) != 880:
        fail("preflight evidence does not cover 880 transitions")
    for key in ("raw_archives_modified", "matlab_started", "fem_solver_started", "training_started"):
        if require_bool(require_field(preflight, key, "preflight evidence"), f"preflight evidence.{key}"):
            fail(f"preflight evidence.{key} must be false")
    if verify_interpreter(
        require_field(preflight, "interpreter", "preflight evidence"),
        "preflight evidence.interpreter",
    ) != summary_interpreter:
        fail("preflight interpreter does not match the receipt's summarized interpreter")

    archives = require_list(require_field(preflight, "archives", "preflight evidence"), "preflight evidence.archives")
    if len(archives) != len(LOCKS):
        fail("preflight evidence must contain exactly two archive reports")
    seen: set[str] = set()
    for index, value in enumerate(archives):
        context = f"preflight evidence.archives[{index}]"
        report = require_object(value, context)
        require_exact_keys(
            report,
            (
                "archive_name",
                "archive_root",
                "run_id",
                "producer_commit",
                "u_max",
                "logical_rows",
                "unique_physical_states",
                "physical_transitions",
                "identity_hashes",
                "manifest",
                "payloads",
            ),
            context,
        )
        name = require_string(require_field(report, "archive_name", context), f"{context}.archive_name")
        lock = LOCKS.get(name)
        if lock is None or name in seen:
            fail(f"{context}.archive_name is not one unique fixed archive")
        seen.add(name)
        root = require_string(require_field(report, "archive_root", context), f"{context}.archive_root")
        if normalized_path_literal(root) != normalized_path_literal(admissions[name]["root"]):
            fail(f"{context}.archive_root does not match MATLAB admission")
        if require_string(require_field(report, "run_id", context), f"{context}.run_id") != lock["run_id"]:
            fail(f"{context}.run_id does not match {name}")
        if require_string(require_field(report, "producer_commit", context), f"{context}.producer_commit") != SOURCE_COMMIT:
            fail(f"{context}.producer_commit mismatch")
        u_max = require_finite_number(str(require_field(report, "u_max", context)), f"{context}.u_max")
        if u_max != lock["u_max"]:
            fail(f"{context}.u_max does not match {name}")
        if require_integral(require_field(report, "logical_rows", context), f"{context}.logical_rows", minimum=0) != lock["cycles"] * 6:
            fail(f"{context}.logical_rows does not match {name}")
        expected_payloads = 1 + lock["cycles"] * 5
        if require_integral(require_field(report, "unique_physical_states", context), f"{context}.unique_physical_states", minimum=0) != expected_payloads:
            fail(f"{context}.unique_physical_states does not match {name}")
        if require_integral(require_field(report, "physical_transitions", context), f"{context}.physical_transitions", minimum=0) != lock["cycles"] * 5:
            fail(f"{context}.physical_transitions does not match {name}")
        hashes = require_object(require_field(report, "identity_hashes", context), f"{context}.identity_hashes")
        require_exact_keys(
            hashes,
            ("manifest", "state_index", "static", "config", "source_receipt", "run_summary"),
            f"{context}.identity_hashes",
        )
        expected_hashes = {
            "manifest": lock["manifest_sha256"],
            "state_index": lock["index_sha256"],
            "static": lock["static_sha256"],
            "config": lock["config_sha256"],
            "source_receipt": lock["source_receipt_sha256"],
            "run_summary": lock["run_summary_sha256"],
        }
        for key, expected in expected_hashes.items():
            if require_hex(require_field(hashes, key, f"{context}.identity_hashes"), 64, f"{context}.identity_hashes.{key}") != expected:
                fail(f"{context}.identity_hashes.{key} does not match {name}")
        manifest = require_object(require_field(report, "manifest", context), f"{context}.manifest")
        require_exact_keys(manifest, ("files", "bytes"), f"{context}.manifest")
        manifest_files = require_integral(require_field(manifest, "files", f"{context}.manifest"), f"{context}.manifest.files", minimum=1)
        if manifest_files != admissions[name]["manifest_member_count"]:
            fail(f"{context}.manifest.files does not match MATLAB admission manifest_member_count")
        require_integral(require_field(manifest, "bytes", f"{context}.manifest"), f"{context}.manifest.bytes", minimum=1)
        payloads = require_object(require_field(report, "payloads", context), f"{context}.payloads")
        require_exact_keys(payloads, ("unique_payloads", "payload_bytes"), f"{context}.payloads")
        if require_integral(require_field(payloads, "unique_payloads", f"{context}.payloads"), f"{context}.payloads.unique_payloads", minimum=0) != expected_payloads:
            fail(f"{context}.payloads.unique_payloads does not match {name}")
        require_integral(require_field(payloads, "payload_bytes", f"{context}.payloads"), f"{context}.payloads.payload_bytes", minimum=1)
    if seen != set(LOCKS):
        fail("preflight evidence does not cover both fixed archives")


def verify_python_launcher(
    receipt: dict[str, Any],
    expected_path: str | None,
    expected_sha256: str | None,
) -> dict[str, Any]:
    launcher = require_object(require_field(receipt, "python_launcher", "receipt"), "receipt.python_launcher")
    require_exact_keys(
        launcher,
        (
            "path",
            "sha256",
            "configured_path",
            "absolute_path_required",
            "archive_admission_authoritative",
        ),
        "receipt.python_launcher",
    )
    if (expected_path is None) != (expected_sha256 is None):
        fail("--launcher-path and --launcher-sha256 must be supplied together")
    path = require_windows_absolute_path(
        require_string(require_field(launcher, "path", "receipt.python_launcher"), "receipt.python_launcher.path"),
        "receipt.python_launcher.path",
    )
    configured = require_windows_absolute_path(
        require_string(
            require_field(launcher, "configured_path", "receipt.python_launcher"),
            "receipt.python_launcher.configured_path",
        ),
        "receipt.python_launcher.configured_path",
    )
    if normalized_path_literal(path) != normalized_path_literal(configured):
        fail("receipt.python_launcher.path and configured_path do not bind the same launcher")
    digest = require_hex(
        require_field(launcher, "sha256", "receipt.python_launcher"),
        64,
        "receipt.python_launcher.sha256",
    )
    if not require_bool(require_field(launcher, "absolute_path_required", "receipt.python_launcher"), "receipt.python_launcher.absolute_path_required"):
        fail("receipt.python_launcher.absolute_path_required must be true")
    if require_bool(require_field(launcher, "archive_admission_authoritative", "receipt.python_launcher"), "receipt.python_launcher.archive_admission_authoritative"):
        fail("Python launcher must not claim archive-admission authority")
    if expected_path is not None:
        require_windows_absolute_path(expected_path, "--launcher-path")
        if normalized_path_literal(path) != normalized_path_literal(expected_path):
            fail("receipt Python launcher path does not match --launcher-path custody evidence")
        if digest != require_hex(expected_sha256, 64, "--launcher-sha256"):
            fail("receipt Python launcher hash does not match --launcher-sha256 custody evidence")
    return {
        "mode": "external-custody-checked" if expected_path is not None else "receipt-record-only",
        "path": path,
        "sha256": digest,
    }


def verify_metrics(path: Path) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != METRIC_COLUMNS:
            fail("metrics CSV header does not match the frozen 36-column schema")
        rows = list(reader)
    if len(rows) != 880:
        fail(f"metrics CSV must contain 880 transitions, found {len(rows)}")

    expected_keys = {
        (archive, cycle, substep)
        for archive, lock in LOCKS.items()
        for cycle in range(1, lock["cycles"] + 1)
        for substep in range(1, 6)
    }
    seen: set[tuple[str, int, int]] = set()
    totals = {archive: 0 for archive in LOCKS}
    for index, row in enumerate(rows, start=2):
        context = f"metrics CSV row {index}"
        if None in row or any(value is None for value in row.values()):
            fail(f"{context} has an unexpected column count")
        archive = row["archive"]
        lock = LOCKS.get(archive)
        if lock is None:
            fail(f"{context}.archive is not one of the two fixed archives")
        if row["run_id"] != lock["run_id"]:
            fail(f"{context}.run_id does not match {archive}")
        cycle = require_csv_nonnegative_integer(row["cycle"], f"{context}.cycle")
        substep = require_csv_nonnegative_integer(row["substep"], f"{context}.substep")
        if not 1 <= cycle <= lock["cycles"] or not 1 <= substep <= 5:
            fail(f"{context} is outside {archive}'s physical trajectory range")
        key = (archive, cycle, substep)
        if key in seen:
            fail(f"{context} duplicates an earlier physical transition")
        seen.add(key)
        totals[archive] += 1
        target = f"c{cycle:04d}_s{substep:02d}"
        if row["target_state_key"] != target:
            fail(f"{context}.target_state_key breaks chronological coverage")
        if row["previous_state_key"] != expected_previous_state(cycle, substep):
            fail(f"{context}.previous_state_key breaks the physical predecessor chain")
        if row["initial_semantics"] != INITIAL_SEMANTICS:
            fail(f"{context}.initial_semantics does not preserve the recovered-state label")
        numbers: dict[str, float] = {}
        for name in METRIC_FLOAT_COLUMNS:
            number = require_finite_number(row[name], f"{context}.{name}")
            numbers[name] = number
            if name not in ("raw_H_min", "raw_q_min") and number < 0:
                fail(f"{context}.{name} must be nonnegative")
        counts: dict[str, int] = {}
        for name in METRIC_COUNT_COLUMNS:
            counts[name] = require_csv_nonnegative_integer(row[name], f"{context}.{name}")
        history_exact = require_csv_bool(row["history_exact"], f"{context}.history_exact")
        history_channels = (
            "history_H_max_abs",
            "history_alpha_max_abs",
            "history_q_max_abs",
            "history_f_max_abs",
        )
        maximum_channel_delta = max(numbers[name] for name in history_channels)
        if numbers["history_max_abs"] < maximum_channel_delta:
            fail(f"{context}.history_max_abs is smaller than a channel maximum")
        if history_exact != (maximum_channel_delta == 0.0):
            fail(f"{context}.history_exact does not agree with the reported channel deltas")
        if not require_csv_bool(row["recomputed_psi_exact"], f"{context}.recomputed_psi_exact"):
            fail(f"{context}.recomputed_psi_exact must be true")
        if numbers["recomputed_psi_vs_payload_max_abs"] != 0.0:
            fail(f"{context}.recomputed_psi_vs_payload_max_abs must be exactly zero")
        for raw_name, count_name in (
            ("raw_H_min", "raw_H_negative_count"),
            ("raw_q_min", "raw_q_negative_count"),
        ):
            if counts[count_name] == 0 and numbers[raw_name] < 0:
                fail(f"{context}.{count_name} is zero despite a negative {raw_name}")
            if counts[count_name] > 0 and numbers[raw_name] >= 0:
                fail(f"{context}.{count_name} is positive but {raw_name} is not negative")
        for name in ("staggered_delta_d_claimed", "staggered_fixed_point_claimed"):
            if require_csv_bool(row[name], f"{context}.{name}"):
                fail(f"{context}.{name} must remain false")
    if seen != expected_keys:
        missing = len(expected_keys - seen)
        unexpected = len(seen - expected_keys)
        fail(f"metrics CSV trajectory coverage mismatch (missing={missing}, unexpected={unexpected})")
    for archive, lock in LOCKS.items():
        if totals[archive] != lock["cycles"] * 5:
            fail(f"metrics CSV has the wrong transition count for {archive}")
    return totals


def read_receipt(path: Path) -> dict[str, Any]:
    return read_json_object(path, "receipt")


def verify_receipt(
    receipt: dict[str, Any],
    package_root: Path | None,
    receipt_path: Path,
    metrics_path: Path,
    preflight_path: Path,
    expected_launcher_path: str | None,
    expected_launcher_sha256: str | None,
    relocated_evidence: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_exact_keys(
        receipt,
        (
            "schema",
            "status",
            "scope",
            "package",
            "source",
            "matlab_archive_admission",
            "supplemental_python_preflight",
            "python_launcher",
            "archive_receipts",
            "physical_transition_count",
            "metric_csv",
            "raw_archives_modified",
            "fem_solver_started",
            "native_assembler_calls_used",
            "training_started",
            "runtime_binary_source_equivalence_proved",
            "numerical_admission_decision",
            "not_proved",
        ),
        "receipt",
    )
    if require_string(require_field(receipt, "schema", "receipt"), "receipt.schema") != AUDIT_SCHEMA:
        fail("receipt.schema does not match the frozen saved-state audit")
    if require_string(require_field(receipt, "status", "receipt"), "receipt.status") != AUDIT_STATUS:
        fail("receipt.status is not completed_saved_state_audit")
    if require_string(require_field(receipt, "scope", "receipt"), "receipt.scope") != AUDIT_SCOPE:
        fail("receipt.scope does not preserve the post-clip/non-solver boundary")
    if require_integral(require_field(receipt, "physical_transition_count", "receipt"), "receipt.physical_transition_count", minimum=0) != 880:
        fail("receipt.physical_transition_count must be 880")
    metric_csv = require_string(require_field(receipt, "metric_csv", "receipt"), "receipt.metric_csv")
    if basename_literal(metric_csv) != "saved_state_transition_metrics.csv":
        fail("receipt.metric_csv does not name the fixed metrics CSV")
    preflight_summary = require_object(
        require_field(receipt, "supplemental_python_preflight", "receipt"),
        "receipt.supplemental_python_preflight",
    )
    declared_preflight = require_string(
        require_field(preflight_summary, "path", "receipt.supplemental_python_preflight"),
        "receipt.supplemental_python_preflight.path",
    )
    if parent_literal(metric_csv) != parent_literal(declared_preflight):
        fail("receipt declares metrics and preflight from different output directories")
    if not relocated_evidence:
        declared_directory = parent_literal(metric_csv)
        if normalized_path_literal(str(receipt_path.resolve(strict=True).parent)) != declared_directory:
            fail("--receipt is not in the receipt-declared output directory; use explicit relocation mode only with custody hashes")
        if normalized_path_literal(str(metrics_path.resolve(strict=True))) != normalized_path_literal(metric_csv):
            fail("--metrics does not match receipt.metric_csv; use explicit relocation mode only with custody hashes")
        if normalized_path_literal(str(preflight_path.resolve(strict=True))) != normalized_path_literal(declared_preflight):
            fail("--preflight does not match the receipt-declared preflight path; use explicit relocation mode only with custody hashes")
    for key in ("raw_archives_modified", "fem_solver_started", "training_started"):
        if require_bool(require_field(receipt, key, "receipt"), f"receipt.{key}"):
            fail(f"receipt.{key} must be false")
    if not require_bool(require_field(receipt, "native_assembler_calls_used", "receipt"), "receipt.native_assembler_calls_used"):
        fail("receipt.native_assembler_calls_used must be true")
    if require_bool(
        require_field(receipt, "runtime_binary_source_equivalence_proved", "receipt"),
        "receipt.runtime_binary_source_equivalence_proved",
    ):
        fail("receipt must not claim runtime source-to-MEX equivalence")
    if require_string(
        require_field(receipt, "numerical_admission_decision", "receipt"),
        "receipt.numerical_admission_decision",
    ) != "not_evaluated":
        fail("receipt.numerical_admission_decision must remain not_evaluated")
    not_proved = require_list(require_field(receipt, "not_proved", "receipt"), "receipt.not_proved")
    if tuple(not_proved) != NOT_PROVED:
        fail("receipt.not_proved does not preserve the fixed non-conclusion boundary")

    package_report = verify_package_record(receipt, package_root)
    verify_source(receipt)
    admissions = verify_admissions(receipt)
    verify_archive_receipts(receipt, admissions)
    preflight_interpreter = verify_preflight_summary(receipt)
    verify_preflight_evidence(preflight_path, admissions, preflight_interpreter)
    launcher_report = verify_python_launcher(
        receipt,
        expected_launcher_path,
        expected_launcher_sha256,
    )
    return package_report, launcher_report


def check_optional_hash(path: Path, expected: str | None, label: str) -> str:
    actual = sha256_file(path)
    if expected is not None:
        configured = require_hex(expected, 64, f"--{label}-sha256")
        if actual != configured:
            fail(f"{label} SHA-256 does not match the supplied custody value")
    return actual


def verify(
    receipt_path: Path,
    metrics_path: Path,
    preflight_path: Path,
    *,
    package_root: Path | None = None,
    receipt_sha256: str | None = None,
    metrics_sha256: str | None = None,
    preflight_sha256: str | None = None,
    launcher_path: str | None = None,
    launcher_sha256: str | None = None,
    relocated_evidence: bool = False,
) -> dict[str, Any]:
    if receipt_path.is_symlink() or not receipt_path.is_file():
        fail("--receipt must name a regular JSON file")
    if metrics_path.is_symlink() or not metrics_path.is_file():
        fail("--metrics must name a regular CSV file")
    if preflight_path.is_symlink() or not preflight_path.is_file():
        fail("--preflight must name a regular JSON file")
    if receipt_path.name != "saved_state_audit_receipt.json":
        fail("--receipt must use the fixed saved_state_audit_receipt.json filename")
    if metrics_path.name != "saved_state_transition_metrics.csv":
        fail("--metrics must use the fixed saved_state_transition_metrics.csv filename")
    if preflight_path.name != "preflight.json":
        fail("--preflight must use the fixed preflight.json filename")
    parents = {
        receipt_path.resolve(strict=True).parent,
        metrics_path.resolve(strict=True).parent,
        preflight_path.resolve(strict=True).parent,
    }
    if len(parents) != 1:
        fail("--receipt, --metrics, and --preflight must be co-located in one evidence directory")
    if relocated_evidence and any(
        value is None for value in (receipt_sha256, metrics_sha256, preflight_sha256)
    ):
        fail("relocated evidence requires independently recorded receipt, metrics, and preflight SHA-256 values")
    receipt_digest = check_optional_hash(receipt_path, receipt_sha256, "receipt")
    metrics_digest = check_optional_hash(metrics_path, metrics_sha256, "metrics")
    preflight_digest = check_optional_hash(preflight_path, preflight_sha256, "preflight")
    receipt = read_receipt(receipt_path)
    package_report, launcher_report = verify_receipt(
        receipt,
        package_root,
        receipt_path,
        metrics_path,
        preflight_path,
        launcher_path,
        launcher_sha256,
        relocated_evidence,
    )
    totals = verify_metrics(metrics_path)
    return {
        "schema": "fixed_weight_saved_state_posthoc_verifier_v1",
        "status": "verified_posthoc_contract_only",
        "receipt_sha256": receipt_digest,
        "metrics_sha256": metrics_digest,
        "preflight_sha256": preflight_digest,
        "package_evidence": package_report,
        "launcher_evidence": launcher_report,
        "input_location_binding": (
            "relocated-with-external-custody" if relocated_evidence else "receipt-output-path-checked"
        ),
        "archives": totals,
        "physical_transition_count": sum(totals.values()),
        "numerical_admission_decision": "not_evaluated",
        "physical_conclusion": "not_established",
        "conclusions_not_established": list(NOT_PROVED),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path,
                        help="saved_state_audit_receipt.json to inspect")
    parser.add_argument("--metrics", required=True, type=Path,
                        help="saved_state_transition_metrics.csv to inspect")
    parser.add_argument("--preflight", required=True, type=Path,
                        help="preflight.json from the same completed audit")
    parser.add_argument("--package-root", type=Path,
                        help="optional staged numerical-audit package to hash-check")
    parser.add_argument("--receipt-sha256",
                        help="optional independently recorded SHA-256 for --receipt")
    parser.add_argument("--metrics-sha256",
                        help="optional independently recorded SHA-256 for --metrics")
    parser.add_argument("--preflight-sha256",
                        help="optional independently recorded SHA-256 for --preflight")
    parser.add_argument("--relocated-evidence", action="store_true",
                        help="allow a relocated co-located evidence bundle only with all three input SHA-256 values")
    parser.add_argument("--launcher-path",
                        help="optional externally recorded explicit launcher path")
    parser.add_argument("--launcher-sha256",
                        help="optional externally recorded SHA-256 for that launcher")
    args = parser.parse_args(argv)
    runtime = verify_self_runtime()
    report = verify(
        args.receipt,
        args.metrics,
        args.preflight,
        package_root=args.package_root,
        receipt_sha256=args.receipt_sha256,
        metrics_sha256=args.metrics_sha256,
        preflight_sha256=args.preflight_sha256,
        launcher_path=args.launcher_path,
        launcher_sha256=args.launcher_sha256,
        relocated_evidence=args.relocated_evidence,
    )
    report["verifier_runtime"] = runtime
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, VerificationError, csv.Error) as exc:
        print(f"posthoc verification failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
