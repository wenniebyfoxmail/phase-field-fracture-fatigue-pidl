"""One bounded, read-only Torch admission for three explicit 53ce archives.

The archives remain source-distinct from the existing 862992 development pair.
This script binds only the named remote roots, verifies their immutable identity
files, and streams every physical state.  It writes JSONL to stdout only: no
FEM solve, training, archive mutation, or manifest update is possible here.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import io
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import socket
import sys
import time

import h5py
import numpy as np
import torch

from fixed_weight_contract import (
    Material, Mesh, RecoveredInitialKey, SplitManifest, StateKey,
    TrajectoryRecord, RECOVERED_INITIAL_SEMANTICS, _require, iter_trajectory,
)
from fixed_weight_native_adapter import (
    LEGACY_PRODUCER, LEGACY_RULE, adapt_native, precision_bound_row,
)
from s09_stage0a_capability import (
    S09_E008_CONTEXT, _mat_numeric, decode_native_static, load_state_index,
)
from s09_stage0a_packet import _reject_external_hdf5_storage, decode_payload


MESH_ID = (
    "q4:88b282890356b6bb7a12071d11abb8ca54645522f68ccfcbfb629a97fd4dd75d:"
    "14fe4eda15312fae2ef54142e3dc16cd5710464378728bd8d0f8a9f60b1a4ef2"
)
ROOT = r"C:\q4runs\hard5_native_q4_existing_u011_u012_u013_20260827_v1"
ARCHIVE_ORDER = (
    "hard5_u011_stage0b",
    "hard5_u012_stage0b",
    "hard5_u013_stage0b",
)
ARCHIVES = {
    "hard5_u011_stage0b": {
        "cycles": 125, "amplitude": .11,
        "index": "49655f5aa9fbe50cfdad90058326358adcb4b770114de79ea7fcfbd3d365a302",
        "manifest": "9bd9930c56c42da6cf1fd05fba68fd3b93258539eaf6deb669dd8071f9ccd464",
        "config": "4e412a4e409c92fb6feb35498370a117163d057483547ad8d5cca6c51e01c353",
        "static": "6e86088a0f6dbb764bb3acb14c59846f8786ead431500fe3e1c1903e004723fb",
        "reference_inventory_sha256": "dcc72933940d385b13e74225557467f7a58b500a204cbc4748c44dfdbd5e6bd2",
    },
    "hard5_u012_stage0b": {
        "cycles": 86, "amplitude": .12,
        "index": "330036eef1ab2d4eb45cce2515607e05abc24e07034c18ab5f339c2cd6a3ea8e",
        "manifest": "6504a91f72dcfeda0117ff5c4e3a2777ee0306e7899141b66a047c0de2732166",
        "config": "88489aa23be3067f151812be36cfde047a53912739de18d9f897def220dc438b",
        "static": "4ccf97c4b5521211c5a115729de523cfbf51131363e5dfdac91812fe2e1dd6a3",
        "reference_inventory_sha256": "99c88fd293a225d5282d1178d98c9bbeed76b285f7fe313c44dbfc401336060d",
    },
    "hard5_u013_stage0b": {
        "cycles": 62, "amplitude": .13,
        "index": "4b83d4e77b1e992f2a8c17d009716186a5cd9d42d7d44ab25fec5a6a7e083825",
        "manifest": "cd94587bb98ba51ae0504716ec280093fb752dd9379c2c211f216809884c9d4b",
        "config": "6827a98fa5301955e040afd805566b3c21c3c26e70c0b3e4ac926f945c182558",
        "static": "4bb7d261f09b53dd55c197782fa2ee0476199e379dea726d7f83c791b53b14b9",
        "reference_inventory_sha256": "ea8ca34009ac1f2319dae6404cc5778d1f28686f5808efe37dd84b874ea51cda",
    },
}
MATERIAL = (1., .3, .01, .01, .5, 2., 0., 1.)
# Retained source-side identifiers for traceability only.  The Python adapter
# does not open a producer checkout or verify these arithmetic blobs at runtime.
DECLARED_SOURCE_ARITHMETIC_BLOBS = {
    "Sources/+phase_field/+mex/Modules/fem/assembly/equilibrium/amor.f90":
        "6a30c52161b2999889b7bc1b57a17cbd6e4c6db5",
    "Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90":
        "d3d03cdd2ee1d894893f1cbb584a7e94947ec6b7",
    "Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m":
        "e74c95ac7b4a439bbc7815561ff45c071428c065",
}
RECEIPT_SCHEMA = "fixed_weight_legacy_native_admission_receipt_v2"
BUNDLE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = BUNDLE_ROOT / "source"
REQUIRED_VERIFIER_MODULES = (
    "fixed_weight_contract",
    "fixed_weight_native_adapter",
    "fixed_weight_roundoff",
    "s09_equilibrium_operator",
    "s09_fem_physics",
    "s09_operator",
    "s09_q4_quadrature",
    "s09_stage0a_capability",
    "s09_stage0a_p1_freeze",
    "s09_stage0a_packet",
    "s09_stage0a_transition",
)
RECEIPT_ENVIRONMENT_KEYS = (
    "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONHASHSEED",
    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "CUDA_VISIBLE_DEVICES",
)
_EVENT_DIGEST = hashlib.sha256()
_EVENT_COUNT = 0


def emit(kind: str, **values) -> None:
    """Write one canonically hashed JSONL receipt event to stdout only."""
    global _EVENT_COUNT
    encoded = json.dumps({"kind": kind, **values}, allow_nan=False,
                         ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    _EVENT_DIGEST.update(encoded.encode("utf-8") + b"\n")
    _EVENT_COUNT += 1
    print(encoded, flush=True)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: object) -> str:
    return sha256(json.dumps(value, allow_nan=False, ensure_ascii=True,
                            sort_keys=True, separators=(",", ":")).encode("utf-8"))


def file_fingerprint(path: Path, *, relative_to: Path | None = None) -> dict[str, object]:
    """Fingerprint verifier code without traversing a data archive."""
    resolved = path.resolve()
    _require(resolved.is_file(), "verifier file missing")
    data = resolved.read_bytes()
    value: dict[str, object] = {"bytes": len(data), "sha256": sha256(data)}
    if relative_to is None:
        value["path"] = str(resolved)
    else:
        parent = relative_to.resolve()
        _require(resolved.is_relative_to(parent), "verifier file escapes bundle")
        value["path"] = resolved.relative_to(parent).as_posix()
    return value


def archive_identity(archive: str) -> dict[str, object]:
    """Return the fixed, ordered identity contract before opening an archive."""
    _require(archive in ARCHIVES, "archive outside explicit legacy scope")
    profile = ARCHIVES[archive]
    return {
        "archive": archive,
        "archive_root": str(Path(ROOT) / archive),
        "producer_commit": LEGACY_PRODUCER,
        "cycles": profile["cycles"],
        "amplitude": profile["amplitude"],
        "index_sha256": profile["index"],
        "manifest_sha256": profile["manifest"],
        "config_sha256": profile["config"],
        "static_sha256": profile["static"],
        "reference_inventory_sha256": profile["reference_inventory_sha256"],
    }


def declared_archive_order() -> list[dict[str, object]]:
    _require(tuple(ARCHIVES) == ARCHIVE_ORDER, "archive profile declaration order drifted")
    return [archive_identity(archive) for archive in ARCHIVE_ORDER]


def verifier_fingerprint() -> dict[str, object]:
    """Bind this runner to the exact local source bundle used by Python.

    The selected files are code only.  This intentionally does not discover or
    inspect any FEM archive member, so the receipt can be emitted before the
    first archive read.
    """
    bundle_root = BUNDLE_ROOT.resolve()
    source_root = SOURCE_ROOT.resolve()
    _require(source_root.is_dir() and Path(__file__).resolve().is_relative_to(bundle_root),
             "verifier bundle layout is incomplete")
    module_files: list[dict[str, object]] = []
    loaded_modules: set[str] = set()
    for name, module in sorted(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not isinstance(module_file, str):
            continue
        candidate = Path(module_file).resolve()
        if candidate.suffix == ".py" and candidate.is_relative_to(source_root):
            item = file_fingerprint(candidate, relative_to=bundle_root)
            item["module"] = name
            module_files.append(item)
            loaded_modules.add(name)
    missing = sorted(set(REQUIRED_VERIFIER_MODULES) - loaded_modules)
    _require(not missing, "required verifier module missing or imported outside bundle: " + ",".join(missing))
    module_files.sort(key=lambda item: (str(item["path"]), str(item["module"])))
    script = file_fingerprint(Path(__file__), relative_to=bundle_root)
    bundle = {"script": script, "source_modules": module_files}
    return {"schema": RECEIPT_SCHEMA, **bundle,
            "bundle_sha256": canonical_digest(bundle)}


def dependency_fingerprint(distribution_name: str, module) -> dict[str, object]:
    """Record installed-package identity without hashing a large binary tree."""
    try:
        distribution = importlib_metadata.distribution(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        distribution = None
    module_file = Path(module.__file__).resolve()
    _require(module_file.is_file(), "dependency module file missing")
    record = None if distribution is None else distribution.read_text("RECORD")
    metadata = None if distribution is None else distribution.read_text("METADATA")
    return {
        "distribution": distribution_name,
        "distribution_metadata_available": distribution is not None,
        "version": getattr(module, "__version__", None) if distribution is None else distribution.version,
        "module_file": str(module_file),
        "module_file_sha256": sha256(module_file.read_bytes()),
        "record_sha256": None if record is None else sha256(record.encode("utf-8")),
        "metadata_sha256": None if metadata is None else sha256(metadata.encode("utf-8")),
    }


def environment_fingerprint() -> dict[str, object]:
    """Capture only execution settings that can select code or numerical paths."""
    torch_config = torch.__config__.show()
    return {
        "python": {
            "executable": sys.executable,
            "implementation": sys.implementation.name,
            "version": sys.version,
        },
        "platform": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "dependency_fingerprints": [
            dependency_fingerprint("torch", torch),
            dependency_fingerprint("numpy", np),
            dependency_fingerprint("h5py", h5py),
        ],
        "torch_runtime": {
            "cuda_version": torch.version.cuda,
            "default_dtype": str(torch.get_default_dtype()),
            "git_version": getattr(torch.version, "git_version", None),
            "num_interop_threads": torch.get_num_interop_threads(),
            "num_threads": torch.get_num_threads(),
            "torch_config_sha256": sha256(torch_config.encode("utf-8")),
        },
        "selected_environment": {key: os.environ.get(key) for key in RECEIPT_ENVIRONMENT_KEYS},
        "sys_path": list(sys.path),
    }


def event_stream_checkpoint() -> dict[str, object]:
    """Hash all receipt events emitted before the completion record."""
    return {"event_count_before_complete": _EVENT_COUNT,
            "event_stream_sha256_before_complete": _EVENT_DIGEST.hexdigest()}


def digest(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def require_relative(root: Path, path: Path) -> None:
    _require(path.resolve().is_relative_to(root.resolve()) and path.is_file(),
             "manifest path missing or escapes archive")


def normalized_relative(value: str) -> str:
    relative = PurePosixPath(value.replace("\\", "/"))
    _require(not relative.is_absolute() and ".." not in relative.parts and str(relative) != ".",
             "invalid relative archive member")
    return relative.as_posix()


def verify_manifest(root: Path, expected_hash: str) -> dict[str, str]:
    data = (root / "SHA256SUMS.txt").read_bytes()
    _require(sha256(data) == expected_hash, "SHA256SUMS identity mismatch")
    members: dict[str, str] = {}
    for line in data.decode("utf-8-sig").splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?(.+)", line)
        _require(match is not None, "invalid manifest line")
        relative = normalized_relative(match[2])
        _require(relative not in members, "duplicate manifest member")
        require_relative(root, root / relative)
        members[relative] = match[1].lower()
    _require(bool(members), "empty manifest")
    return members


def read_bound_member(root: Path, members: dict[str, str], relative: str) -> bytes:
    relative = normalized_relative(relative)
    _require(relative in members, "required file absent from manifest")
    path = root / relative
    require_relative(root, path)
    data = path.read_bytes()
    _require(sha256(data) == members[relative], "manifest member hash mismatch")
    return data


def parse_json_object(data: bytes, label: str) -> dict[str, object]:
    """Decode a manifest-bound JSON receipt as an object, never a loose value."""
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _require(False, label + " is not valid UTF-8 JSON")
    _require(isinstance(value, dict), label + " must be a JSON object")
    return value


def require_sha256(value: object, label: str) -> str:
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None,
             label + " must be a SHA-256 hex digest")
    return value.lower()


def require_positive_integer(value: object, label: str) -> int:
    _require(type(value) is int and value > 0, label + " must be a positive integer")
    return value


def bind_producer_provenance(
    source: dict[str, object],
    source_after: dict[str, object],
    profile: dict[str, object],
    source_bytes: bytes,
    source_after_bytes: bytes,
) -> dict[str, object]:
    """Bind the before/after source receipts to the frozen archive profile.

    This checks receipt assertions and identifiers only.  It deliberately does
    not claim a runtime verification of any producer source or arithmetic blob.
    """
    expected_inventory = require_sha256(profile["reference_inventory_sha256"],
                                        "frozen reference inventory lock")
    source_inventory = require_sha256(source.get("reference_inventory_sha256"),
                                      "source receipt reference inventory")
    after_inventory = require_sha256(source_after.get("reference_inventory_sha256"),
                                     "source-after receipt reference inventory")
    _require(source_inventory == after_inventory == expected_inventory,
             "source receipt inventory identity differs from frozen profile")
    _require(source_after.get("verified") is True,
             "source-after receipt is not verified")
    file_count = require_positive_integer(source_after.get("file_count"),
                                          "source-after receipt file_count")
    reference_file_count = require_positive_integer(source_after.get("reference_file_count"),
                                                    "source-after receipt reference_file_count")
    _require(file_count == reference_file_count,
             "source-after receipt file count differs from reference count")
    return {
        "source_receipt_sha256": sha256(source_bytes),
        "source_after_receipt_sha256": sha256(source_after_bytes),
        "reference_inventory_sha256": expected_inventory,
        "source_after_verified": True,
        "source_after_file_count": file_count,
        "source_after_reference_file_count": reference_file_count,
    }


def bind_run_summary(summary: dict[str, object], profile: dict[str, object],
                     physical_count: int, summary_bytes: bytes) -> dict[str, object]:
    """Require the archive's replay summary to match the frozen profile."""
    cycles = profile["cycles"]
    _require(type(cycles) is int and cycles > 0, "invalid locked cycle count")
    provenance = summary.get("provenance")
    _require(isinstance(provenance, dict), "archive summary provenance missing")
    _require(provenance.get("execution_mode") == "replay_existing",
             "archive summary is not an existing replay")
    logical_state_count = require_positive_integer(summary.get("logical_state_count"),
                                                   "archive summary logical_state_count")
    cycle_count = require_positive_integer(summary.get("cycle_count"),
                                           "archive summary cycle_count")
    _require(logical_state_count == cycles * 6,
             "archive summary logical state count differs from frozen profile")
    _require(cycle_count == cycles, "archive summary cycle count differs from frozen profile")
    _require(summary.get("sealed") is True and summary.get("unique_payload_count") == physical_count,
             "archive summary mismatch")
    return {
        "run_summary_relative_path": "run_summary.json",
        "run_summary_sha256": sha256(summary_bytes),
        "execution_mode": "replay_existing",
        "logical_state_count": logical_state_count,
        "cycle_count": cycle_count,
        "unique_payload_count": physical_count,
        "sealed": True,
    }


def validate_sequence(rows: list[dict[str, str]], cycles: int) -> list[dict[str, str]]:
    expected = [f"c{cycle:04d}_s{substep:02d}"
                for cycle in range(1, cycles + 1) for substep in range(6)]
    _require([r["state_key"] for r in rows] == expected,
             "incomplete native substep coverage")
    by_key = {r["state_key"]: r for r in rows}
    for row in rows:
        cycle, substep = int(row["cycle"]), int(row["substep"])
        _require(row["state_key"] == f"c{cycle:04d}_s{substep:02d}",
                 "numeric cycle/substep disagrees with native state key")
        alias = substep == 0 and cycle > 1
        source = f"c{cycle - 1:04d}_s05" if alias else row["state_key"]
        _require(row["source_state_key"] == source and row["is_alias"] == str(int(alias)),
                 "invalid native alias")
        _require(row["timing"] == ("pre_cycle_committed" if substep == 0 else "post_history_commit"),
                 "native timing mismatch")
        _require(row["converged"] == "1", "unconverged native state")
        _require(float(row["nominal_load_factor"]) == (0., .25, .5, .75, 1., 0.)[substep],
                 "wrong nominal path")
        if alias:
            _require(all(row[k] == by_key[source][k] for k in
                         ("payload_file", "payload_sha256", "imposed_displacement")),
                     "alias source mismatch")
    return [row for row in rows if row["is_alias"] == "0"]


def prepare(root: Path):
    _require(root.name in ARCHIVES, "archive outside explicit legacy scope")
    profile = ARCHIVES[root.name]
    _require(os.path.normcase(str(root.resolve())) == os.path.normcase(str(Path(ROOT) / root.name)),
             "legacy archive root mismatch")
    context = replace(
        S09_E008_CONTEXT,
        run_id=f"legacy53ce:{root.name}:{profile['index'][:12]}",
        producer_commit=LEGACY_PRODUCER,
        state_index_sha256=profile["index"],
        static_sha256=profile["static"],
    )
    rows = load_state_index(root / "state_index.csv", context)
    physical = validate_sequence(rows, profile["cycles"])
    manifest = verify_manifest(root, profile["manifest"])
    _require(manifest.get("state_index.csv") == profile["index"], "state index is not manifest-bound")
    static_relative = f"static/{context.static_filename}"
    _require(manifest.get(static_relative) == profile["static"], "static file is not manifest-bound")
    _require(manifest.get("provenance/config_receipt.mat") == profile["config"],
             "config file is not manifest-bound")
    payload_relatives = {normalized_relative(row["payload_file"]) for row in physical}
    _require(len(payload_relatives) == len(physical) and
             all(relative.startswith("states/") and manifest.get(relative) == row["payload_sha256"].lower()
                 for relative, row in ((normalized_relative(row["payload_file"]), row) for row in physical)),
             "payload index/manifest binding mismatch")
    _require({f"states/{p.name}" for p in (root / "states").iterdir() if p.is_file()} == payload_relatives,
             "state file membership mismatch")
    source_bytes = read_bound_member(root, manifest, "provenance/source_receipt.json")
    source_after_bytes = read_bound_member(root, manifest, "provenance/source_after_receipt.json")
    summary_bytes = read_bound_member(root, manifest, "run_summary.json")
    source = parse_json_object(source_bytes, "source receipt")
    source_after = parse_json_object(source_after_bytes, "source-after receipt")
    summary = parse_json_object(summary_bytes, "archive summary")
    _require(source["source_commit"] == LEGACY_PRODUCER and source["source_dirty"] is False,
             "producer binding mismatch")
    provenance_binding = bind_producer_provenance(
        source, source_after, profile, source_bytes, source_after_bytes,
    )
    summary_binding = bind_run_summary(summary, profile, len(physical), summary_bytes)
    _require(source.get("run_id") in (None, "") and summary.get("provenance", {}).get("run_id") in (None, ""),
             "legacy profile must not invent or conceal a producer run identifier")
    static, static_receipt = decode_native_static(root / "static" / context.static_filename, context)
    cfg_bytes = (root / "provenance/config_receipt.mat").read_bytes()
    _require(sha256(cfg_bytes) == profile["config"], "config identity mismatch")
    static_bytes = (root / "static" / context.static_filename).read_bytes()
    _require(sha256(static_bytes) == profile["static"], "static changed during read")
    with h5py.File(io.BytesIO(static_bytes), "r") as handle, h5py.File(io.BytesIO(cfg_bytes), "r") as config_handle:
        _reject_external_hdf5_storage(handle)
        _reject_external_hdf5_storage(config_handle)
        static_group, config_group = handle["stage0b_static"], config_handle["config_receipt"]
        values = tuple(float(_mat_numeric(handle, static_group["material_parameters"], key).item())
                       for key in ("E", "ni", "Gc", "ell", "alpha_T", "p", "res_stiff")) + (static["thickness"],)
        _require(values == MATERIAL, "material mismatch")
        material = Material(*values)
        for key in ("u_max", "R", "alpha_T", "res_stiff", "n_step", "effective_uy",
                    "nominal_load_factor", "reset_fatigue_after_recovery"):
            _require(np.array_equal(_mat_numeric(handle, static_group["case_config"], key),
                                    _mat_numeric(config_handle, config_group, key)),
                     "static/config mismatch " + key)
        _require(float(_mat_numeric(config_handle, config_group, "u_max").item()) == profile["amplitude"],
                 "amplitude mismatch")
        _require(float(_mat_numeric(config_handle, config_group, "reset_fatigue_after_recovery").item()) == 1.,
                 "recovery reset absent")
        schedule = _mat_numeric(config_handle, config_group, "effective_uy").reshape(-1)
        _require(np.array_equal(np.unique(_mat_numeric(handle, static_group["mesh"]["native_mesh"],
                                                        "elem_material_id")), [1.]),
                 "mixed material IDs")
        xy = static["xy"]
        bottom, top = xy[:, 1] == xy[:, 1].min(), xy[:, 1] == xy[:, 1].max()
        for key, wanted in (("fix_X", bottom | top), ("fix_Y", bottom), ("disp_Y", top)):
            ids = _mat_numeric(handle, static_group["boundary_node_masks"], key).reshape(-1) - 1
            _require(np.array_equal(np.sort(ids), np.flatnonzero(wanted)),
                     "boundary mask mismatch " + key)
    mesh_id = "q4:" + static_receipt["node_coordinates_sha256"] + ":" + static_receipt["cells_0based_sha256"]
    _require(mesh_id == MESH_ID, "mesh identity mismatch")
    mesh = Mesh(torch.from_numpy(static["xy"].copy()), torch.from_numpy(static["conn"].copy()), mesh_id)
    trajectory_id = f"legacy53ce:{root.name}:{profile['index'][:12]}"
    record = TrajectoryRecord(
        trajectory_id, root.name, LEGACY_PRODUCER, mesh_id, "train",
        "development-only:legacy53ce_native_profile_20261024",
        semantics=RECOVERED_INITIAL_SEMANTICS,
        expected_state_count=profile["cycles"] * 5 + 1,
        material_values=values,
    )
    emit("binding", archive=root.name, producer_run_id=None,
         adapter_trajectory_id=trajectory_id, record=record.__dict__,
         index_sha256=profile["index"], manifest_sha256=profile["manifest"],
         config_sha256=profile["config"], static_sha256=profile["static"],
         static_receipt=static_receipt, physical_states=len(physical),
         aliases=len(rows) - len(physical), manifest_members=len(manifest),
         schedule=schedule.tolist(), rule=LEGACY_RULE,
         expected_negative_H_support=0, expected_negative_q_support=0,
         producer_provenance=provenance_binding,
         run_summary_contract=summary_binding,
         source_receipt_sha256=provenance_binding["source_receipt_sha256"],
         source_after_receipt_sha256=provenance_binding["source_after_receipt_sha256"],
         run_summary_relative_path=summary_binding["run_summary_relative_path"],
         run_summary_sha256=summary_binding["run_summary_sha256"],
         reference_inventory_sha256=provenance_binding["reference_inventory_sha256"],
         execution_mode=summary_binding["execution_mode"],
         logical_state_count=summary_binding["logical_state_count"],
         cycle_count=summary_binding["cycle_count"],
         declared_source_arithmetic_blobs=DECLARED_SOURCE_ARITHMETIC_BLOBS,
         source_arithmetic_runtime_verified=False,
         source_arithmetic_scope=(
             "declared source-side identifiers only; this adapter does not open a "
             "producer source checkout or verify arithmetic blobs at runtime"),
         training_started=False, solver_started=False, originals_modified=False)
    return physical, static, schedule, mesh, material, record


def run(root: Path) -> tuple[TrajectoryRecord, dict[str, object]]:
    started = time.monotonic()
    rows, static, schedule, mesh, material, record = prepare(root)
    SplitManifest([record]).validate()
    counts = {"states": 0, "transitions": 0, "repair_points": 0,
              "csv_load_differences": 0, "negative_H_points": 0, "negative_q_points": 0}

    def loader(_):
        previous_load = 0.
        previous_raw_q = previous_canonical_q = None
        for ordinal, row in enumerate(rows):
            _require(time.monotonic() - started < 1800, "30 minute validation cap reached")
            bound = precision_bound_row(row, archive=root.name, schedule=schedule)
            payload_relative = normalized_relative(row["payload_file"])
            decoded = decode_payload(root / payload_relative, bound,
                                     expected_nodes=len(mesh.xy), expected_elements=len(mesh.conn))
            before = [digest(a) for a in (decoded.u_node, decoded.d_node, decoded.history_gp)]
            negative_H = int((decoded.history_gp[..., 0] < 0).sum())
            negative_q = int((decoded.history_gp[..., 2] < 0).sum())
            _require(negative_H == negative_q == 0, "legacy negative support changed after preflight")
            if ordinal == 0:
                _require(np.array_equal(decoded.u_node, np.zeros_like(decoded.u_node)), "initial displacement is not zero")
                _require(np.array_equal(decoded.history_gp[..., :3], np.zeros_like(decoded.history_gp[..., :3])),
                         "initial history is not zero")
                _require(np.isfinite(decoded.d_node).all() and ((decoded.d_node >= 0) & (decoded.d_node <= 1)).all(),
                         "initial damage violates contract")
            load = decoded.imposed_displacement
            key_type = RecoveredInitialKey if ordinal == 0 else StateKey
            branch = "initial" if ordinal == 0 else "load" if load > previous_load else "unload" if load < previous_load else "hold"
            key = key_type(record.trajectory_id, record.condition_id, record.reference_id, record.mesh_id,
                           decoded.logical_cycle, decoded.logical_substep, ordinal, branch, load)
            state, receipt = adapt_native(
                decoded, key, mesh, material, archive=root.name, source_commit=LEGACY_PRODUCER,
                source_timing=row["timing"], native_shape=static["shape"],
                native_derivative=static["reference_derivative"],
            )
            _require(before == [digest(a) for a in (decoded.u_node, decoded.d_node, decoded.history_gp)],
                     "raw archive array changed")
            _require(np.array_equal(state.u.numpy(), decoded.u_node) and
                     np.array_equal(state.d.numpy(), decoded.d_node) and
                     np.array_equal(state.history.numpy(), decoded.history_gp[..., :3]),
                     "legacy profile altered a raw contract field")
            if previous_raw_q is not None:
                raw_increment = np.maximum(decoded.history_gp[..., 2] - previous_raw_q, 0.)
                canonical_increment = np.maximum(state.history[..., 2].numpy() - previous_canonical_q, 0.)
                _require(np.array_equal(raw_increment, canonical_increment),
                         "adaptation changes fatigue accumulation increment")
            previous_raw_q = decoded.history_gp[..., 2].copy()
            previous_canonical_q = state.history[..., 2].numpy().copy()
            counts["repair_points"] += len(receipt["repairs"])
            counts["csv_load_differences"] += int(float(row["imposed_displacement"]) != load)
            counts["negative_H_points"] += negative_H
            counts["negative_q_points"] += negative_q
            emit("adapted", archive=root.name, key=row["state_key"], ordinal=ordinal,
                 raw_csv_load=row["imposed_displacement"], canonical_load=load,
                 raw_array_digests=before, initial=ordinal == 0,
                 **receipt)
            previous_load = load
            yield state

    for state in iter_trajectory(record, loader, mesh, material):
        counts["states"] += 1
        counts["transitions"] += int(state.key.ordinal > 0)
    _require(counts["states"] == record.expected_state_count and counts["transitions"] == len(rows) - 1,
             "incomplete stream")
    _require(counts["repair_points"] == counts["negative_H_points"] == counts["negative_q_points"] == 0,
             "unexpected legacy repair or negative point")
    completion = {
        "archive": root.name,
        "archive_identity": archive_identity(root.name),
        "expected_physical_states": record.expected_state_count,
        "expected_transitions": len(rows) - 1,
        **counts,
        "elapsed_seconds": time.monotonic() - started,
    }
    emit("admitted", **completion,
         qualification_scope="synthetic archive learning, development conditions only",
         training_started=False, solver_started=False, originals_modified=False)
    return record, completion


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs=3, type=Path)
    args = parser.parse_args()
    _require(tuple(root.name for root in args.roots) == ARCHIVE_ORDER,
             "archives must be exactly U0.11, U0.12, U0.13 in frozen order")
    invocation_started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    archive_order = declared_archive_order()
    archive_order_sha256 = canonical_digest(archive_order)
    verifier_before = verifier_fingerprint()
    emit("invocation", receipt_schema=RECEIPT_SCHEMA, argv=list(sys.argv),
         cwd=str(Path.cwd()), root_arguments=[str(root) for root in args.roots],
         ordered_archive_identities=archive_order,
         archive_order_sha256=archive_order_sha256,
         verifier=verifier_before, environment=environment_fingerprint(),
         hostname=socket.gethostname(), pid=os.getpid(),
         training_started=False, solver_started=False, originals_modified=False)
    results = [run(root) for root in args.roots]
    records = [record for record, _ in results]
    SplitManifest(records).validate()
    verifier_after = verifier_fingerprint()
    _require(verifier_after["bundle_sha256"] == verifier_before["bundle_sha256"],
             "verifier bundle changed during validation")
    completion = {
        "receipt_schema": RECEIPT_SCHEMA,
        "archives": len(records),
        "archive_order_sha256": archive_order_sha256,
        "ordered_archive_identities": archive_order,
        "conditions": [record.condition_id for record in records],
        "per_archive": [summary for _, summary in results],
        "total_physical_states": sum(summary["states"] for _, summary in results),
        "total_transitions": sum(summary["transitions"] for _, summary in results),
        "elapsed_seconds": time.monotonic() - invocation_started,
        "verifier_bundle_sha256": verifier_before["bundle_sha256"],
        "verifier_script_sha256": verifier_before["script"]["sha256"],
        "verifier_bundle_unchanged": True,
        "test_conditions": 0,
        "rule": LEGACY_RULE,
        "training_started": False,
        "solver_started": False,
        "originals_modified": False,
    }
    emit("complete", **event_stream_checkpoint(), **completion)
