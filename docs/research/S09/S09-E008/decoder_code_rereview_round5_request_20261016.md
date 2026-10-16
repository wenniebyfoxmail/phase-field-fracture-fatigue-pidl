请对 S09-E008 Stage-0A 真实 schema 最小修复做第五轮只读 Code Ready 复审。请用中文。第四轮 commit da46f2b 已 CODE_READY_PASS；获准的首次真实只读 audit 随后 fail closed，证明真实 exporter 的 converged 是 MATLAB logical uint8 (1,1)，而 reviewed decoder 错要求 float64。

本轮只审核 exact commit `918ec57e1b6eaf3c9489ae37af866328775021ac` 中这个 schema 修复及直接回归。不得访问真实 payload、训练、FEM 或扩展其他范围。

必须核查：新 logical reader 是否严格要求 uint8 (1,1)、MATLAB_class=logical、MATLAB_int_decode=1、value 精确为预期布尔；是否拒绝 float64替代、错class、错marker、0/非布尔值；正常 synthetic full route 是否无回归。不得把已通过的其他事项重新扩展。

输出第一行只给 CODE_READY_PASS 或 REVISE_AND_REREVIEW；记录 exact commit、独立测试、finding；若 PASS，只允许保留 A001 receipt 后进行一次新的 read-only capability attempt，仍不授权训练。

## Manifest
- `docs/research/S09/S09-E008/decoder_code_review_round4_20261016.md` sha256 `524b9199bce3c4a1fdcc6a3b298b40881dde9ff79d0a9dce909a23d282cd5a10` bytes `964`
- `docs/research/S09/S09-E008/data_capability_a001_20261016.md` sha256 `60c53be8f33e2601fe220e00896efcc649a02dd20bf2160bd7d62afc9ce2d56e` bytes `1494`
- `source/s09_stage0a_packet.py` sha256 `02f1f742d3b69977d10db5ba46904864104ec7ce1dd93e7c5c660d39dae589e0` bytes `15015`
- `source/s09_stage0a_capability.py` sha256 `a2fe082938837e16bc26f7f41cd2063726255ec59bf70e36d884ccfd0b2df5ad` bytes `17204`
- `tests/test_s09_stage0a_packet.py` sha256 `1a4f206d8eebc39b3911959951f06360afaa719801b434f24e5ad46756a1ceb2` bytes `10191`
- `tests/test_s09_stage0a_capability.py` sha256 `26ec4810f3d9153b05963804462979dd6159ca7d747222260b218e31ea099217` bytes `11646`

## FILE: docs/research/S09/S09-E008/decoder_code_review_round4_20261016.md

```md
# Stage-0A decoder independent Code Ready review, round 4 — 2026-10-16

- surface: Haofan ChatGPT Pro, Pro model;
- conversation: `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- reviewed commit: `da46f2bb7bfdf4bd559325f161a9b8827cafd319`;
- packet SHA256: `decf9f96a3aeeec6eedb5ce45e211c33bcdc77ae30ed7a868cd7d1a1c1ea6acd`;
- verdict: `CODE_READY_PASS` after 7m40s.

The reviewer matched eight snapshot files, ran 23 included tests, 31 directed
checks and six syntax checks. Alias load equality and scalar thickness were
closed; C1, 366-state decode, endpoint assembly and C2/C4/C5 showed no direct
regression. Decoder integrity, full-trajectory decoded qualification and P1
interface passed at Code Ready level.

This PASS authorised only a read-only CITPC12 scientific data-capability audit:
full hash preflight plus static, shape, order, alias, channel and normaliser
checks. It did not authorise training, FEM, Stage 0B or scientific claims.

```

## FILE: docs/research/S09/S09-E008/data_capability_a001_20261016.md

```md
# S09-E008-A001 scientific data-capability audit — first attempt

## Identity

- producer: `CITPC12` via `citpc12-ssh`;
- sealed run: `hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae`;
- reviewed code: `da46f2bb7bfdf4bd559325f161a9b8827cafd319`;
- remote workspace:
  `C:\q4runs\_capability_audits\S09-E008-A001-stage0a-capability-20261016`;
- receipt SHA256:
  `982d4ae3bb23ff2b93133bc049bc0fdcd8cdc8a5fd240f1a07fc2bbd5dc72dc1`.

## Result

`FAILED_CLOSED` after 8.74 seconds at the first dynamic payload. No P1 freeze,
training, FEM, model, backward or optimiser step occurred.

The exact payload hash matched the index. Real scalar storage was:

- cycle/substep/imposed displacement: float64 `(1,1)`, MATLAB class `double`;
- converged: uint8 `(1,1)`, MATLAB class `logical`, `MATLAB_int_decode=1`,
  value `1`.

The reviewed decoder required float64 for `converged`, so it correctly stopped
but its synthetic fixture did not match the exact exporter schema. This is a
bounded parser-contract mismatch, not evidence that the sealed scientific data
are invalid.

## Repair and boundary

The parser now has an exact MATLAB logical reader requiring uint8 `(1,1)`,
class `logical`, integer-decode marker `1`, and exact Boolean value. Tests cover
float64 substitution, wrong class and false value. Because this changes the
reviewed decoder, another exact-commit Code Ready review is required before any
second read-only attempt. The first receipt remains preserved and is not
overwritten.

```

## FILE: source/s09_stage0a_packet.py

```py
"""Fail-closed Stage-0A payload decoding for S09-E008.

This module has no CLI and does not choose or open a scientific archive by
itself.  Callers must supply an already qualified state index and explicit
cycle membership.  Every selected payload is hashed before the first HDF5
file is opened.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from numbers import Integral
from pathlib import Path
import re

import h5py
import numpy as np


SHA256 = re.compile(r"[0-9a-f]{64}")
STATE_KEY = re.compile(r"c(?P<cycle>[0-9]{4})_s(?P<substep>[0-9]{2})")
REQUIRED_DATASETS = {
    "u_node",
    "d_node",
    "history_gp",
    "strain_en_undgr_gp",
    "strain_en_degr_gp",
}


@dataclass(frozen=True)
class DecodedStage0AState:
    logical_cycle: int
    logical_substep: int
    source_state_key: str
    u_node: np.ndarray
    d_node: np.ndarray
    history_gp: np.ndarray
    strain_en_undgr_gp: np.ndarray
    strain_en_degr_gp: np.ndarray
    imposed_displacement: float
    payload_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _integer(row: dict[str, str], name: str) -> int:
    value = int(row[name])
    _require(str(value) == row[name] or row[name] == f"{value:d}",
             f"noncanonical integer {name}")
    return value


def _state_identity(key: str) -> tuple[int, int]:
    match = STATE_KEY.fullmatch(key)
    _require(match is not None, f"invalid state key: {key}")
    return int(match.group("cycle")), int(match.group("substep"))


def index_by_key(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_key = {row["state_key"]: row for row in rows}
    _require(len(by_key) == len(rows), "duplicate state key")
    return by_key


def _payload_path(states_dir: Path, row: dict[str, str]) -> Path:
    relative = Path(row["payload_file"])
    _require(
        relative.parts == ("states", relative.name)
        and relative.name not in ("", ".", ".."),
        f"invalid payload path for {row['state_key']}",
    )
    root = states_dir.resolve(strict=True)
    path = states_dir / relative.name
    _require(not path.is_symlink(), f"payload symlink is forbidden: {relative.name}")
    resolved = path.resolve(strict=True)
    _require(resolved.parent == root, f"payload escapes states directory: {relative.name}")
    return resolved


def transition_rows(
    rows: list[dict[str, str]], cycles: tuple[int, ...] | list[int]
) -> list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]]:
    """Return `(s00, s04, previous_s05)` rows after causal identity checks."""
    _require(
        all(isinstance(cycle, Integral) and not isinstance(cycle, (bool, np.bool_))
            for cycle in cycles),
        "cycles must contain exact integer values",
    )
    selected = tuple(int(cycle) for cycle in cycles)
    _require(selected == tuple(sorted(set(selected))),
             "cycles must be unique and increasing")
    _require(all(1 <= cycle <= 73 for cycle in selected), "cycle out of range")
    by_key = index_by_key(rows)
    result = []
    for cycle in selected:
        pre_key = f"c{cycle:04d}_s00"
        peak_key = f"c{cycle:04d}_s04"
        _require(pre_key in by_key and peak_key in by_key,
                 f"missing Stage-0A rows for cycle {cycle}")
        pre, peak = by_key[pre_key], by_key[peak_key]
        _require(_integer(pre, "cycle") == cycle and _integer(pre, "substep") == 0,
                 f"invalid pre row for cycle {cycle}")
        _require(_integer(peak, "cycle") == cycle and _integer(peak, "substep") == 4,
                 f"invalid peak row for cycle {cycle}")
        _require(pre["timing"] == "pre_cycle_committed",
                 f"invalid pre timing for cycle {cycle}")
        _require(peak["timing"] == "post_history_commit",
                 f"invalid peak timing for cycle {cycle}")
        _require(peak["is_alias"] == "0" and peak["source_state_key"] == peak_key,
                 f"peak row cannot be an alias for cycle {cycle}")
        previous = None
        if cycle == 1:
            _require(pre["is_alias"] == "0" and pre["source_state_key"] == pre_key,
                     "cycle-1 pre row must be native")
        else:
            previous_key = f"c{cycle - 1:04d}_s05"
            _require(previous_key in by_key, f"missing {previous_key}")
            previous = by_key[previous_key]
            _require(
                _integer(previous, "cycle") == cycle - 1
                and _integer(previous, "substep") == 5
                and previous["timing"] == "post_history_commit"
                and previous["is_alias"] == "0"
                and previous["source_state_key"] == previous_key
                and previous["converged"] == "1"
                and SHA256.fullmatch(previous["payload_sha256"]) is not None,
                f"invalid previous s05 row for cycle {cycle}",
            )
            _require(pre["is_alias"] == "1" and
                     pre["source_state_key"] == previous_key and
                     pre["payload_file"] == previous["payload_file"] and
                     pre["payload_sha256"] == previous["payload_sha256"],
                     f"invalid s00 alias for cycle {cycle}")
        for row in (pre, peak):
            _require(SHA256.fullmatch(row["payload_sha256"]) is not None,
                     f"invalid payload hash for {row['state_key']}")
            _require(row["converged"] == "1", f"unconverged {row['state_key']}")
        result.append((pre, peak, previous))
    return result


def preflight_payloads(
    states_dir: Path,
    transitions: list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]],
) -> list[dict[str, object]]:
    """Hash every unique required payload before any scientific decode."""
    rows = [row for pre, peak, _ in transitions for row in (pre, peak)]
    return preflight_rows(states_dir, rows)


def preflight_rows(
    states_dir: Path, rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    """Hash every unique payload represented by `rows` without opening HDF5."""
    expected: dict[Path, str] = {}
    for row in rows:
        path = _payload_path(states_dir, row)
        prior = expected.setdefault(path, row["payload_sha256"])
        _require(prior == row["payload_sha256"],
                 f"conflicting hashes for {path.name}")
    inventory = []
    for path in sorted(expected):
        _require(path.is_file(), f"missing payload: {path.name}")
        observed = sha256_file(path)
        _require(observed == expected[path], f"preflight hash mismatch: {path.name}")
        inventory.append({"file": path.name, "sha256": observed, "bytes": path.stat().st_size})
    return inventory


def _exact_scalar(handle: h5py.File, name: str, expected: float) -> float:
    dataset = handle[name]
    _require(dataset.dtype == np.dtype("float64") and dataset.shape == (1, 1),
             f"invalid scalar storage: {name}")
    value = float(np.asarray(dataset)[0, 0])
    _require(np.isfinite(value) and value == expected, f"scalar mismatch: {name}")
    return value


def _require_matlab_string(handle: h5py.File, name: str) -> None:
    dataset = handle[name]
    value = dataset.attrs.get("MATLAB_class", b"")
    if isinstance(value, bytes):
        value = value.decode("ascii")
    _require(value == "string", f"{name} is not an exact MATLAB string")


def _exact_matlab_logical(handle: h5py.File, name: str, expected: bool) -> bool:
    """Decode the producer's exact MATLAB-v7.3 scalar logical storage."""
    dataset = handle[name]
    matlab_class = dataset.attrs.get("MATLAB_class", b"")
    if isinstance(matlab_class, bytes):
        matlab_class = matlab_class.decode("ascii")
    int_decode = dataset.attrs.get("MATLAB_int_decode", None)
    _require(
        dataset.dtype == np.dtype("uint8")
        and dataset.shape == (1, 1)
        and matlab_class == "logical"
        and int_decode == 1,
        f"invalid MATLAB logical storage: {name}",
    )
    value = int(np.asarray(dataset)[0, 0])
    _require(value in (0, 1) and bool(value) is expected,
             f"logical mismatch: {name}")
    return bool(value)


def _reject_external_hdf5_storage(handle: h5py.File) -> None:
    """Reject links or dataset storage that can read bytes outside the payload."""
    seen: set[int] = set()

    def walk(group: h5py.Group) -> None:
        token = hash(group.id)
        if token in seen:
            return
        seen.add(token)
        for key in group.keys():
            link = group.get(key, getlink=True)
            _require(isinstance(link, h5py.HardLink),
                     f"non-hard HDF5 link is forbidden: {group.name}/{key}")
            value = group[key]
            if isinstance(value, h5py.Group):
                walk(value)
            elif isinstance(value, h5py.Dataset):
                _require(not value.is_virtual,
                         f"virtual HDF5 dataset is forbidden: {value.name}")
                plist = value.id.get_create_plist()
                _require(plist.get_external_count() == 0,
                         f"external raw HDF5 storage is forbidden: {value.name}")
            else:
                raise ValueError(f"unsupported HDF5 object: {group.name}/{key}")

    walk(handle)


def decode_payload(
    path: Path,
    row: dict[str, str],
    *,
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> DecodedStage0AState:
    """Decode one hash-verified native payload without implicit dtype casts."""
    _require(not path.is_symlink(), f"payload symlink is forbidden: {path.name}")
    payload = path.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    _require(observed == row["payload_sha256"],
             f"immediate hash mismatch: {path.name}")
    logical_cycle = _integer(row, "cycle")
    logical_substep = _integer(row, "substep")
    source_cycle, source_substep = _state_identity(row["source_state_key"])
    # HDF5 reads the same immutable byte buffer that produced `observed`.
    with h5py.File(io.BytesIO(payload), "r") as handle:
        _reject_external_hdf5_storage(handle)
        _require(REQUIRED_DATASETS.issubset(handle.keys()),
                 f"required fields missing: {path.name}")
        expected_shapes = {
            "u_node": (2, expected_nodes),
            "d_node": (1, expected_nodes),
            "history_gp": (4, expected_gp, expected_elements),
            "strain_en_undgr_gp": (expected_gp, expected_elements),
            "strain_en_degr_gp": (expected_gp, expected_elements),
        }
        for name, shape in expected_shapes.items():
            dataset = handle[name]
            _require(dataset.dtype == np.dtype("float64"),
                     f"{name} must be stored float64")
            _require(dataset.shape == shape, f"native shape mismatch: {name}")
        _exact_scalar(handle, "state_metadata/cycle", float(source_cycle))
        _exact_scalar(handle, "state_metadata/substep", float(source_substep))
        imposed = _exact_scalar(
            handle, "state_metadata/imposed_displacement", float(row["imposed_displacement"])
        )
        _exact_matlab_logical(
            handle, "state_metadata/producer_metadata/converged", True
        )
        _require_matlab_string(handle, "state_metadata/state_key")
        _require_matlab_string(handle, "state_metadata/timing")
        _require_matlab_string(handle, "state_metadata/history_channel_labels")
        # Exact string contents are fixed by the matched source commit. MATLAB
        # v7.3 stores string objects through its opaque MCOS subsystem; row and
        # source identities therefore provide the inspectable timing/label lock.
        _require(source_substep in range(6), "source substep outside frozen path")
        u = np.asarray(handle["u_node"]).T
        d = np.asarray(handle["d_node"]).reshape(-1)
        history = np.asarray(handle["history_gp"]).transpose(2, 1, 0)
        undgr = np.asarray(handle["strain_en_undgr_gp"]).T
        degr = np.asarray(handle["strain_en_degr_gp"]).T
    for name, value in (("u_node", u), ("d_node", d), ("history_gp", history),
                        ("strain_en_undgr_gp", undgr), ("strain_en_degr_gp", degr)):
        _require(value.dtype == np.float64 and np.isfinite(value).all(),
                 f"invalid decoded values: {name}")
    _require(np.all((d >= 0) & (d <= 1)), "damage outside [0,1]")
    return DecodedStage0AState(
        logical_cycle=logical_cycle,
        logical_substep=logical_substep,
        source_state_key=row["source_state_key"],
        u_node=u,
        d_node=d,
        history_gp=history,
        strain_en_undgr_gp=undgr,
        strain_en_degr_gp=degr,
        imposed_displacement=imposed,
        payload_sha256=observed,
    )


def decode_stage0a_transitions(
    *,
    states_dir: Path,
    rows: list[dict[str, str]],
    cycles: tuple[int, ...] | list[int],
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> tuple[list[tuple[DecodedStage0AState, DecodedStage0AState]], dict[str, object]]:
    """Preflight then decode explicit s00-to-s04 transitions."""
    pairs = transition_rows(rows, cycles)
    inventory = preflight_payloads(states_dir, pairs)
    decoded = []
    alias_checks = []
    for pre_row, peak_row, previous_row in pairs:
        pre_path = _payload_path(states_dir, pre_row)
        peak_path = _payload_path(states_dir, peak_row)
        kwargs = dict(expected_nodes=expected_nodes, expected_elements=expected_elements,
                      expected_gp=expected_gp)
        pre = decode_payload(pre_path, pre_row, **kwargs)
        peak = decode_payload(peak_path, peak_row, **kwargs)
        if previous_row is not None:
            previous = decode_payload(pre_path, previous_row, **kwargs)
            equal = (np.array_equal(pre.u_node, previous.u_node) and
                     np.array_equal(pre.d_node, previous.d_node) and
                     np.array_equal(pre.history_gp, previous.history_gp) and
                     np.array_equal(pre.strain_en_undgr_gp, previous.strain_en_undgr_gp) and
                     np.array_equal(pre.strain_en_degr_gp, previous.strain_en_degr_gp))
            _require(equal, f"numerical s05-to-s00 alias mismatch at cycle {pre.logical_cycle}")
            alias_checks.append(pre.logical_cycle)
        decoded.append((pre, peak))
    receipt = {
        "preflight_completed_before_decode": True,
        "payload_inventory": inventory,
        "decoded_cycles": [pre.logical_cycle for pre, _ in decoded],
        "numerical_s05_to_s00_alias_cycles": alias_checks,
        "history_channel_order": ["H", "alpha_bar", "q_prev", "f"],
    }
    return decoded, receipt

```

## FILE: source/s09_stage0a_capability.py

```py
"""Identity-bound, read-only capability adapter for S09-E008 Stage 0A.

The exact public wrapper is frozen to one sealed run.  It qualifies metadata,
static identity and all 366 unique payload hashes before any HDF5 decode.  It
then validates all six physical substeps, derives native weights from the same
verified static bytes, constructs the 73 endpoint transitions internally and
only then freezes P1.  No caller-supplied scientific array crosses that route.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path

import h5py
import numpy as np

from s09_stage0a_packet import (
    _reject_external_hdf5_storage,
    decode_payload,
    index_by_key,
    preflight_rows,
)
from s09_stage0a_p1_freeze import freeze_p1_contract


@dataclass(frozen=True)
class Stage0ACapabilityContext:
    run_id: str
    producer_commit: str
    state_index_sha256: str
    static_sha256: str
    expected_nodes: int
    expected_elements: int
    expected_gp: int
    history_channel_order: tuple[str, ...]
    nominal_load_path: tuple[float, ...]
    static_filename: str = "native_q4_mesh_dofs_quadrature.mat"
    static_semantics: str = "exact-static-hash+producer-source-bound-native-order"

    @property
    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


S09_E008_CONTEXT = Stage0ACapabilityContext(
    run_id="hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae",
    producer_commit="862992a60edc7f59335365beacb5c71fc8592a7a",
    state_index_sha256="3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
    static_sha256="b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e",
    expected_nodes=86_756,
    expected_elements=86_408,
    expected_gp=4,
    history_channel_order=("H", "alpha_bar", "q_prev", "f"),
    nominal_load_path=(0.0, 0.25, 0.5, 0.75, 1.0, 0.0),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_identity_file(path: Path, expected_name: str, expected_sha256: str) -> bytes:
    if path.name != expected_name or path.is_symlink() or not path.is_file():
        raise ValueError(f"invalid identity file: {expected_name}")
    data = path.read_bytes()
    if _sha256_bytes(data) != expected_sha256:
        raise ValueError(f"identity hash mismatch: {expected_name}")
    return data


def load_state_index(index_path: Path, context: Stage0ACapabilityContext) -> list[dict[str, str]]:
    data = _read_identity_file(index_path, "state_index.csv", context.state_index_sha256)
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    required = {
        "state_key", "cycle", "substep", "timing", "is_alias",
        "source_state_key", "payload_file", "payload_sha256",
        "nominal_load_factor", "imposed_displacement", "converged",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError("state index schema mismatch")
    return list(reader)


def _require_complete_six_state_index(
    rows: list[dict[str, str]], context: Stage0ACapabilityContext
) -> None:
    if len(rows) != 73 * 6:
        raise ValueError("full trajectory must contain 438 logical rows")
    by_key = index_by_key(rows)
    if set(by_key) != {f"c{cycle:04d}_s{substep:02d}"
                       for cycle in range(1, 74) for substep in range(6)}:
        raise ValueError("full six-state coverage mismatch")
    for cycle in range(1, 74):
        for substep, expected_load in enumerate(context.nominal_load_path):
            key = f"c{cycle:04d}_s{substep:02d}"
            row = by_key[key]
            if int(row["cycle"]) != cycle or int(row["substep"]) != substep:
                raise ValueError(f"logical identity mismatch: {key}")
            timing = "pre_cycle_committed" if substep == 0 else "post_history_commit"
            if row["timing"] != timing or row["converged"] != "1":
                raise ValueError(f"timing/convergence mismatch: {key}")
            if float(row["nominal_load_factor"]) != expected_load:
                raise ValueError(f"prescribed path mismatch: {key}")
            if substep == 0 and cycle > 1:
                prior = f"c{cycle - 1:04d}_s05"
                prior_row = by_key[prior]
                valid = (
                    row["is_alias"] == "1"
                    and row["source_state_key"] == prior
                    and row["payload_file"] == prior_row["payload_file"]
                    and row["payload_sha256"] == prior_row["payload_sha256"]
                )
            else:
                valid = row["is_alias"] == "0" and row["source_state_key"] == key
            if not valid:
                raise ValueError(f"source identity mismatch: {key}")


def _qualify_full_trajectory(
    *, run_root: Path, context: Stage0ACapabilityContext
) -> tuple[list[dict[str, str]], dict[str, object]]:
    index_path = run_root / "state_index.csv"
    static_path = run_root / "static" / context.static_filename
    rows = load_state_index(index_path, context)
    _require_complete_six_state_index(rows, context)
    _read_identity_file(static_path, context.static_filename, context.static_sha256)
    inventory = preflight_rows(run_root / "states", rows)
    if len(inventory) != 366:
        raise ValueError("expected exactly 366 unique physical payloads")
    receipt = {
        "verdict": "FULL_TRAJECTORY_HASH_QUALIFIED",
        "context_sha256": context.digest,
        "run_id": context.run_id,
        "producer_commit": context.producer_commit,
        "state_index_sha256": context.state_index_sha256,
        "static_sha256": context.static_sha256,
        "static_semantics": context.static_semantics,
        "history_channel_order": list(context.history_channel_order),
        "nominal_load_path": list(context.nominal_load_path),
        "qualified_cycles": list(range(1, 74)),
        "qualified_substeps": list(range(6)),
        "unique_payload_inventory": inventory,
        "unique_payload_count": len(inventory),
        "all_payload_hashes_preflighted": True,
        "hdf5_open_count": 0,
        "scientific_execution_authorized": False,
    }
    return rows, receipt


def qualify_s09_e008_full_trajectory(
    run_root: Path,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Exact-run wrapper; changing identity requires a new reviewed version."""
    return _qualify_full_trajectory(run_root=run_root, context=S09_E008_CONTEXT)


def _array_sha256(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def _mat_field(handle: h5py.File, value, name: str):
    """Dereference one scalar MATLAB-v7.3 struct field."""
    if not isinstance(value, h5py.Group) or name not in value:
        raise ValueError(f"static MATLAB field missing: {name}")
    field = value[name]
    if isinstance(field, h5py.Group):
        return field
    if not isinstance(field, h5py.Dataset):
        raise ValueError(f"unsupported static MATLAB field: {name}")
    reference_type = h5py.check_dtype(ref=field.dtype)
    if reference_type is not None:
        refs = np.asarray(field).reshape(-1)
        if len(refs) != 1 or not refs[0]:
            raise ValueError(f"static MATLAB field is not scalar: {name}")
        return handle[refs[0]]
    return field


def _mat_numeric(handle: h5py.File, value, name: str) -> np.ndarray:
    dataset = _mat_field(handle, value, name)
    if not isinstance(dataset, h5py.Dataset) or dataset.dtype.kind not in "fiu":
        raise ValueError(f"static field is not numeric: {name}")
    stored = np.asarray(dataset)
    # MATLAB stores array dimensions in reverse order in v7.3 HDF5.
    axes = tuple(reversed(range(stored.ndim)))
    return stored.transpose(axes) if axes else stored


def _derive_native_weights(
    static_path: Path, context: Stage0ACapabilityContext
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Derive weights only from the exact verified native static payload."""
    payload = _read_identity_file(static_path, context.static_filename, context.static_sha256)
    with h5py.File(io.BytesIO(payload), "r") as handle:
        _reject_external_hdf5_storage(handle)
        if "stage0b_static" not in handle:
            raise ValueError("stage0b_static root missing")
        root = handle["stage0b_static"]
        mesh = _mat_field(handle, root, "mesh")
        quadrature = _mat_field(handle, root, "quadrature")
        geometry = _mat_field(handle, root, "geometry")
        xy = _mat_numeric(handle, mesh, "node_coordinates")
        conn_raw = _mat_numeric(handle, mesh, "cells_0based")
        gauss_weight = _mat_numeric(handle, quadrature, "gauss_W").reshape(-1)
        nxi = _mat_numeric(handle, quadrature, "Nxi")
        dndxi = _mat_numeric(handle, quadrature, "dNdxi")
        thickness_raw = _mat_numeric(handle, geometry, "t")
        for name, value in (("node_coordinates", xy), ("gauss_W", gauss_weight),
                            ("Nxi", nxi), ("dNdxi", dndxi), ("t", thickness_raw)):
            if value.dtype != np.dtype("float64"):
                raise ValueError(f"static field must be stored float64: {name}")
        if thickness_raw.shape != (1, 1) or not np.isfinite(thickness_raw).all():
            raise ValueError("static thickness must be one finite scalar")
        thickness = float(thickness_raw.reshape(-1)[0])
    if conn_raw.dtype.kind not in "iu" or not np.equal(conn_raw, np.floor(conn_raw)).all():
        raise ValueError("static connectivity must contain exact integers")
    conn = conn_raw.astype(np.int64, copy=False)
    expected = (context.expected_nodes, context.expected_elements, context.expected_gp)
    if (xy.shape, conn.shape, gauss_weight.shape, nxi.shape, dndxi.shape) != (
        (expected[0], 2), (expected[1], 4), (expected[2],),
        (4, expected[2]), (2, 4, expected[2]),
    ):
        raise ValueError("static native-Q4 shape/order contract mismatch")
    if (not np.isfinite(xy).all() or not np.isfinite(gauss_weight).all()
            or not np.isfinite(nxi).all() or not np.isfinite(dndxi).all()
            or not np.isfinite(thickness) or thickness <= 0):
        raise ValueError("static native-Q4 values are invalid")
    if np.any(conn < 0) or np.any(conn >= context.expected_nodes):
        raise ValueError("static connectivity is out of bounds")
    element_xy = xy[conn]
    jacobian = np.einsum("ing,enj->egij", dndxi, element_xy)
    determinant = np.linalg.det(jacobian)
    gp_weight = determinant * gauss_weight[None, :] * thickness
    if not np.isfinite(gp_weight).all() or np.any(gp_weight <= 0):
        raise ValueError("nonpositive or nonfinite native GP weight")
    local = np.einsum("ng,eg->en", nxi, gp_weight)
    nodal_weight = np.zeros(context.expected_nodes, dtype=np.float64)
    np.add.at(nodal_weight, conn.reshape(-1), local.reshape(-1))
    if not np.isfinite(nodal_weight).all() or np.any(nodal_weight <= 0):
        raise ValueError("nonpositive or nonfinite native nodal weight")
    receipt = {
        "source_static_sha256": context.static_sha256,
        "derivation": "Q4 detJ * gauss_W * thickness; Nxi-consistent nodal lumping",
        "node_order": "native", "element_order": "native",
        "gauss_point_order": "native quadrature",
        "node_coordinates_sha256": _array_sha256(xy),
        "cells_0based_sha256": _array_sha256(conn),
        "gauss_weight_sha256": _array_sha256(gauss_weight),
        "Nxi_sha256": _array_sha256(nxi),
        "dNdxi_sha256": _array_sha256(dndxi),
        "thickness": thickness,
        "nodal_weight_sha256": _array_sha256(nodal_weight),
        "gp_weight_sha256": _array_sha256(gp_weight),
        "nodal_weight_shape": list(nodal_weight.shape),
        "gp_weight_shape": list(gp_weight.shape),
    }
    return nodal_weight, gp_weight, receipt


def _state_fingerprint(state) -> dict[str, object]:
    return {
        "source_state_key": state.source_state_key,
        "payload_sha256": state.payload_sha256,
        "imposed_displacement": state.imposed_displacement,
        "u_node_sha256": _array_sha256(state.u_node),
        "d_node_sha256": _array_sha256(state.d_node),
        "history_gp_sha256": _array_sha256(state.history_gp),
        "strain_en_undgr_gp_sha256": _array_sha256(state.strain_en_undgr_gp),
        "strain_en_degr_gp_sha256": _array_sha256(state.strain_en_degr_gp),
    }


def _qualify_decode_and_freeze(
    *, run_root: Path, context: Stage0ACapabilityContext
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Controlled metadata -> full decode -> P1 freeze route with no caller arrays."""
    rows, hash_receipt = _qualify_full_trajectory(run_root=run_root, context=context)
    nodal_weight, gp_weight, weight_receipt = _derive_native_weights(
        run_root / "static" / context.static_filename, context
    )
    shape_d = (73, context.expected_nodes)
    shape_h = (73, context.expected_elements, context.expected_gp, 4)
    d_pre = np.empty(shape_d, dtype=np.float64)
    d_peak = np.empty(shape_d, dtype=np.float64)
    history_pre = np.empty(shape_h, dtype=np.float64)
    history_peak = np.empty(shape_h, dtype=np.float64)
    u_peak = np.empty((73, context.expected_nodes, 2), dtype=np.float64)
    pre_filled = np.zeros(73, dtype=bool)
    peak_filled = np.zeros(73, dtype=bool)
    physical_bindings: dict[str, dict[str, object]] = {}
    native_rows = [row for row in rows if row["is_alias"] == "0"]
    if len(native_rows) != 366:
        raise ValueError("native physical row count mismatch")
    for row in native_rows:
        state = decode_payload(
            run_root / row["payload_file"], row,
            expected_nodes=context.expected_nodes,
            expected_elements=context.expected_elements,
            expected_gp=context.expected_gp,
        )
        key = row["state_key"]
        physical_bindings[key] = _state_fingerprint(state)
        cycle, substep = int(row["cycle"]), int(row["substep"])
        if substep == 0:
            target = 0
        elif substep == 5 and cycle < 73:
            target = cycle
        else:
            target = None
        if target is not None:
            d_pre[target] = state.d_node
            history_pre[target] = state.history_gp
            pre_filled[target] = True
        if substep == 4:
            target = cycle - 1
            d_peak[target] = state.d_node
            history_peak[target] = state.history_gp
            u_peak[target] = state.u_node
            peak_filled[target] = True
    if not pre_filled.all() or not peak_filled.all():
        raise ValueError("endpoint population is incomplete")
    by_key = index_by_key(rows)
    logical_bindings = {}
    for key, row in by_key.items():
        source = row["source_state_key"]
        binding = physical_bindings.get(source)
        if binding is None or binding["payload_sha256"] != row["payload_sha256"]:
            raise ValueError(f"logical-to-physical decoded binding mismatch: {key}")
        imposed = float(row["imposed_displacement"])
        if not np.isfinite(imposed) or imposed != binding["imposed_displacement"]:
            raise ValueError(f"logical-to-physical load mismatch: {key}")
        logical_bindings[key] = {
            "source_state_key": source,
            "payload_sha256": row["payload_sha256"],
            "imposed_displacement": imposed,
            "decoded_array_fingerprints": binding,
        }
    if len(logical_bindings) != 438:
        raise ValueError("decoded logical binding count mismatch")
    decode_receipt = {
        "verdict": "FULL_TRAJECTORY_DECODE_QUALIFIED",
        "context_sha256": context.digest,
        "source_hash_qualification": hash_receipt["verdict"],
        "decoded_physical_payload_count": len(physical_bindings),
        "decoded_logical_state_count": len(logical_bindings),
        "decoded_substeps": list(range(6)),
        "history_channel_order": list(context.history_channel_order),
        "history_channel_semantics": "source-bound-not-directly-decoded",
        "logical_state_bindings": logical_bindings,
    }
    result = freeze_p1_contract(
        cycles=np.arange(1, 74, dtype=np.int64),
        d_pre=d_pre, d_peak=d_peak,
        history_pre=history_pre, history_peak=history_peak, u_peak=u_peak,
        nodal_weight=nodal_weight, gp_weight=gp_weight,
    )
    result.update({
        "source_context_sha256": context.digest,
        "source_static_sha256": context.static_sha256,
        "native_weight_receipt": weight_receipt,
        "source_decode_verdict": decode_receipt["verdict"],
        "qualified_six_state_trajectory": True,
    })
    return result, hash_receipt, decode_receipt


def qualify_decode_and_freeze_s09_e008(
    run_root: Path,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Exact sealed-run route.  It performs no training or optimiser update."""
    return _qualify_decode_and_freeze(run_root=run_root, context=S09_E008_CONTEXT)

```

## FILE: tests/test_s09_stage0a_packet.py

```py
import hashlib
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_packet import (
    decode_payload,
    decode_stage0a_transitions,
    preflight_payloads,
    transition_rows,
)


def write_payload(path: Path, *, cycle: int, substep: int, load: float,
                  nodes: int = 4, elements: int = 2, dtype=np.float64):
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=np.arange(2 * nodes, dtype=dtype).reshape(2, nodes))
        handle.create_dataset("d_node", data=np.linspace(0, .5, nodes, dtype=dtype)[None])
        handle.create_dataset("history_gp", data=np.ones((4, 4, elements), dtype=dtype))
        handle.create_dataset("strain_en_undgr_gp", data=np.ones((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.ones((4, elements), dtype=dtype) * .5)
        metadata = handle.create_group("state_metadata")
        metadata.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        metadata.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        metadata.create_dataset("imposed_displacement", data=np.array([[load]], dtype=np.float64))
        producer = metadata.create_group("producer_metadata")
        converged = producer.create_dataset(
            "converged", data=np.array([[1]], dtype=np.uint8))
        converged.attrs["MATLAB_class"] = np.bytes_(b"logical")
        converged.attrs["MATLAB_int_decode"] = np.uint8(1)
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = metadata.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(*, cycle: int, substep: int, source: str, file: str, sha: str,
        alias: bool, load: float, timing: str):
    return {
        "state_key": f"c{cycle:04d}_s{substep:02d}",
        "cycle": str(cycle),
        "substep": str(substep),
        "source_state_key": source,
        "payload_file": f"states/{file}",
        "payload_sha256": sha,
        "is_alias": "1" if alias else "0",
        "converged": "1",
        "imposed_displacement": repr(load),
        "timing": timing,
    }


def two_cycle_fixture(tmp_path: Path):
    c1_pre = tmp_path / "c0001_s00.mat"
    c1_peak = tmp_path / "c0001_s04.mat"
    c1_post = tmp_path / "c0001_s05.mat"
    c2_peak = tmp_path / "c0002_s04.mat"
    write_payload(c1_pre, cycle=1, substep=0, load=0.0)
    write_payload(c1_peak, cycle=1, substep=4, load=.125)
    write_payload(c1_post, cycle=1, substep=5, load=0.0)
    write_payload(c2_peak, cycle=2, substep=4, load=.125)
    rows = [
        row(cycle=1, substep=0, source="c0001_s00", file=c1_pre.name,
            sha=digest(c1_pre), alias=False, load=0.0, timing="pre_cycle_committed"),
        row(cycle=1, substep=4, source="c0001_s04", file=c1_peak.name,
            sha=digest(c1_peak), alias=False, load=.125, timing="post_history_commit"),
        row(cycle=1, substep=5, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=False, load=0.0, timing="post_history_commit"),
        row(cycle=2, substep=0, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=True, load=0.0, timing="pre_cycle_committed"),
        row(cycle=2, substep=4, source="c0002_s04", file=c2_peak.name,
            sha=digest(c2_peak), alias=False, load=.125, timing="post_history_commit"),
    ]
    return rows


def test_transition_rows_requires_exact_alias_identity(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    assert pairs[1][2]["state_key"] == "c0001_s05"
    bad = [dict(value) for value in rows]
    bad[3]["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="alias"):
        transition_rows(bad, [2])


def test_transition_rows_rejects_malformed_previous_s05(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[2]["timing"] = "pre_cycle_committed"
    with pytest.raises(ValueError, match="previous s05"):
        transition_rows(rows, [2])


def test_preflight_hashes_all_payloads_before_decode(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    inventory = preflight_payloads(tmp_path, pairs)
    assert len(inventory) == 4
    (tmp_path / "c0002_s04.mat").write_bytes(b"changed")
    with pytest.raises(ValueError, match="preflight hash"):
        preflight_payloads(tmp_path, pairs)


def test_preflight_rejects_payload_path_escape(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[0]["payload_file"] = "../c0001_s00.mat"
    with pytest.raises(ValueError, match="payload path"):
        preflight_payloads(tmp_path, transition_rows(rows, [1]))


def test_preflight_rejects_payload_symlink(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    source = tmp_path / "c0001_s00.mat"
    target = tmp_path / "outside.mat"
    source.replace(target)
    os.symlink(target, source)
    rows[0]["payload_sha256"] = digest(target)
    with pytest.raises(ValueError, match="symlink"):
        preflight_payloads(tmp_path, transition_rows(rows, [1]))


@pytest.mark.parametrize("bad_cycles", [[1.9], [True], ["1"]])
def test_transition_rows_rejects_noninteger_cycle_requests_before_io(tmp_path: Path, bad_cycles):
    with pytest.raises(ValueError, match="exact integer"):
        transition_rows(two_cycle_fixture(tmp_path), bad_cycles)


def test_decoder_preserves_native_support_and_alias_equality(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    decoded, receipt = decode_stage0a_transitions(
        states_dir=tmp_path, rows=rows, cycles=[1, 2],
        expected_nodes=4, expected_elements=2,
    )
    assert len(decoded) == 2
    pre, peak = decoded[1]
    assert pre.d_node.shape == (4,)
    assert pre.u_node.shape == (4, 2)
    assert pre.history_gp.shape == (2, 4, 4)
    assert peak.strain_en_undgr_gp.shape == (2, 4)
    assert receipt["preflight_completed_before_decode"] is True
    assert receipt["numerical_s05_to_s00_alias_cycles"] == [2]


def test_decoder_rejects_non_float64_without_cast(tmp_path: Path):
    path = tmp_path / "bad.mat"
    write_payload(path, cycle=1, substep=4, load=.125, dtype=np.float32)
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="stored float64"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_rejects_logical_metadata_rounding(tmp_path: Path):
    path = tmp_path / "rounded.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        handle["state_metadata/cycle"][0, 0] = 1.25
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="cycle"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


@pytest.mark.parametrize("mutation", ["float64", "wrong_class", "false"])
def test_decoder_requires_exact_matlab_logical_convergence(tmp_path: Path, mutation):
    path = tmp_path / "bad_converged.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        parent = handle["state_metadata/producer_metadata"]
        dataset = parent["converged"]
        if mutation == "float64":
            del parent["converged"]
            parent.create_dataset("converged", data=np.array([[1.]], dtype=np.float64))
        elif mutation == "wrong_class":
            dataset.attrs.modify("MATLAB_class", np.bytes_(b"double"))
        else:
            dataset[0, 0] = 0
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="MATLAB logical|logical mismatch"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_rejects_external_hdf5_link(tmp_path: Path):
    external = tmp_path / "external.h5"
    with h5py.File(external, "w") as handle:
        handle.create_dataset("d", data=np.zeros((1, 4), dtype=np.float64))
    path = tmp_path / "linked.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        del handle["d_node"]
        handle["d_node"] = h5py.ExternalLink(external.name, "/d")
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="non-hard HDF5 link"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_reads_same_bytes_that_were_hashed(tmp_path: Path, monkeypatch):
    path = tmp_path / "stable.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    original_hash = digest(path)
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=original_hash, alias=False, load=.125, timing="post_history_commit")
    original_read = Path.read_bytes
    changed = False

    def read_then_replace(self):
        nonlocal changed
        data = original_read(self)
        if self == path and not changed:
            changed = True
            replacement = tmp_path / "replacement.mat"
            write_payload(replacement, cycle=1, substep=4, load=.125)
            with h5py.File(replacement, "r+") as handle:
                handle["d_node"][:] = .9
            replacement.replace(path)
        return data

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)
    decoded = decode_payload(path, item, expected_nodes=4, expected_elements=2)
    np.testing.assert_allclose(decoded.d_node, np.linspace(0, .5, 4))
    assert decoded.payload_sha256 == original_hash

```

## FILE: tests/test_s09_stage0a_capability.py

```py
import csv
import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_capability import (
    S09_E008_CONTEXT,
    _derive_native_weights,
    _qualify_decode_and_freeze,
    _qualify_full_trajectory,
)


FIELDNAMES = ["state_key", "cycle", "substep", "timing", "is_alias",
              "source_state_key", "payload_file", "payload_sha256",
              "nominal_load_factor", "imposed_displacement", "converged"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_qualified_fixture(tmp_path: Path):
    states = tmp_path / "states"; states.mkdir()
    static_dir = tmp_path / "static"; static_dir.mkdir()
    static = static_dir / "native_q4_mesh_dofs_quadrature.mat"
    static.write_bytes(b"synthetic-static")
    physical = {}
    rows = []
    loads = (0.0, .25, .5, .75, 1.0, 0.0)
    for cycle in range(1, 74):
        for substep, load in enumerate(loads):
            key = f"c{cycle:04d}_s{substep:02d}"
            alias = substep == 0 and cycle > 1
            source = f"c{cycle - 1:04d}_s05" if alias else key
            if source not in physical:
                path = states / f"{source}.mat"
                path.write_bytes(source.encode())
                physical[source] = (path.name, sha(path))
            filename, digest = physical[source]
            rows.append({
                "state_key": key, "cycle": str(cycle), "substep": str(substep),
                "timing": "pre_cycle_committed" if substep == 0 else "post_history_commit",
                "is_alias": "1" if alias else "0", "source_state_key": source,
                "payload_file": f"states/{filename}", "payload_sha256": digest,
                "nominal_load_factor": repr(load), "imposed_displacement": repr(load),
                "converged": "1",
            })
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(S09_E008_CONTEXT, state_index_sha256=sha(index),
                      static_sha256=sha(static), expected_nodes=3,
                      expected_elements=2)
    return context, rows


def write_static(path: Path):
    g = 1 / np.sqrt(3)
    locations = ((g, g), (-g, g), (g, -g), (-g, -g))
    nxi, dndxi = [], []
    for xi, eta in locations:
        nxi.append([.25*(1-xi)*(1-eta), .25*(1+xi)*(1-eta),
                    .25*(1+xi)*(1+eta), .25*(1-xi)*(1+eta)])
        dndxi.append([
            [-.25*(1-eta), .25*(1-eta), .25*(1+eta), -.25*(1+eta)],
            [-.25*(1-xi), -.25*(1+xi), .25*(1+xi), .25*(1-xi)],
        ])
    xy = np.array([[0,0], [1,0], [1,1], [0,1], [2,0], [2,1]], dtype=np.float64)
    conn = np.array([[0,1,2,3], [1,4,5,2]], dtype=np.int64)
    nxi = np.asarray(nxi).T
    dndxi = np.asarray(dndxi).transpose(1, 2, 0)
    with h5py.File(path, "w") as handle:
        root = handle.create_group("stage0b_static")
        mesh = root.create_group("mesh")
        mesh.create_dataset("node_coordinates", data=xy.T)
        mesh.create_dataset("cells_0based", data=conn.T)
        quadrature = root.create_group("quadrature")
        quadrature.create_dataset("gauss_W", data=np.ones((1, 4), dtype=np.float64))
        quadrature.create_dataset("Nxi", data=nxi.T)
        quadrature.create_dataset("dNdxi", data=dndxi.transpose(2, 1, 0))
        geometry = root.create_group("geometry")
        geometry.create_dataset("t", data=np.array([[1.]], dtype=np.float64))


def write_state(path: Path, *, cycle: int, substep: int, magnitude: float,
                bad_float32: bool = False):
    dtype = np.float32 if bad_float32 else np.float64
    nodes, elements = 6, 2
    u = np.ones((2, nodes), dtype=dtype) * np.array([[.01], [.1]], dtype=dtype)
    d = np.full((1, nodes), magnitude, dtype=dtype)
    decoded_history = np.ones((elements, 4, 4), dtype=dtype) * magnitude
    history = decoded_history.transpose(2, 1, 0)
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=u)
        handle.create_dataset("d_node", data=d)
        handle.create_dataset("history_gp", data=history)
        handle.create_dataset("strain_en_undgr_gp", data=np.zeros((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.zeros((4, elements), dtype=dtype))
        meta = handle.create_group("state_metadata")
        meta.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        meta.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        imposed = (0.0, .031249875, .062499875, .093749875, .124999875, 0.0)[substep]
        meta.create_dataset("imposed_displacement", data=np.array([[imposed]], dtype=np.float64))
        producer = meta.create_group("producer_metadata")
        converged = producer.create_dataset(
            "converged", data=np.array([[1]], dtype=np.uint8))
        converged.attrs["MATLAB_class"] = np.bytes_(b"logical")
        converged.attrs["MATLAB_int_decode"] = np.uint8(1)
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = meta.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def make_decodable_fixture(tmp_path: Path, *, corrupt_key: str | None = None):
    states = tmp_path / "states"; states.mkdir()
    static_dir = tmp_path / "static"; static_dir.mkdir()
    static = static_dir / "native_q4_mesh_dofs_quadrature.mat"
    write_static(static)
    physical = {}
    rows = []
    loads = (0.0, .25, .5, .75, 1.0, 0.0)
    imposed = (0.0, .031249875, .062499875, .093749875, .124999875, 0.0)
    for cycle in range(1, 74):
        for substep, load in enumerate(loads):
            key = f"c{cycle:04d}_s{substep:02d}"
            alias = substep == 0 and cycle > 1
            source = f"c{cycle - 1:04d}_s05" if alias else key
            if source not in physical:
                source_cycle = int(source[1:5]); source_step = int(source[-2:])
                magnitude = (source_cycle - 1) / 360 if source_step == 4 else 0.0
                path = states / f"{source}.mat"
                write_state(path, cycle=source_cycle, substep=source_step,
                            magnitude=magnitude, bad_float32=source == corrupt_key)
                physical[source] = (path.name, sha(path))
            filename, digest = physical[source]
            rows.append({
                "state_key": key, "cycle": str(cycle), "substep": str(substep),
                "timing": "pre_cycle_committed" if substep == 0 else "post_history_commit",
                "is_alias": "1" if alias else "0", "source_state_key": source,
                "payload_file": f"states/{filename}", "payload_sha256": digest,
                "nominal_load_factor": repr(load), "imposed_displacement": repr(imposed[substep]),
                "converged": "1",
            })
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(S09_E008_CONTEXT, state_index_sha256=sha(index),
                      static_sha256=sha(static), expected_nodes=6,
                      expected_elements=2)
    return context


def test_full_trajectory_qualification_binds_all_six_states_and_payloads(tmp_path: Path):
    context, _ = make_qualified_fixture(tmp_path)
    rows, receipt = _qualify_full_trajectory(run_root=tmp_path, context=context)
    assert len(rows) == 438
    assert len(receipt["unique_payload_inventory"]) == 366
    assert receipt["qualified_substeps"] == list(range(6))
    assert receipt["hdf5_open_count"] == 0


def test_full_trajectory_rejects_missing_s02_before_payload_decode(tmp_path: Path):
    context, rows = make_qualified_fixture(tmp_path)
    rows = [row for row in rows if row["state_key"] != "c0001_s02"]
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(context, state_index_sha256=sha(index))
    with pytest.raises(ValueError, match="438 logical"):
        _qualify_full_trajectory(run_root=tmp_path, context=context)


def test_controlled_route_derives_weights_decodes_all_six_states_and_freezes(tmp_path: Path):
    context = make_decodable_fixture(tmp_path)
    result, hash_receipt, decode_receipt = _qualify_decode_and_freeze(
        run_root=tmp_path, context=context)
    assert result["verdict"] == "P1_CONTRACT_FROZEN"
    assert result["qualified_six_state_trajectory"] is True
    assert result["native_weight_receipt"]["source_static_sha256"] == context.static_sha256
    assert hash_receipt["unique_payload_count"] == 366
    assert decode_receipt["decoded_physical_payload_count"] == 366
    assert decode_receipt["decoded_logical_state_count"] == 438
    assert set(decode_receipt["decoded_substeps"]) == set(range(6))


def test_native_weights_are_derived_from_static_geometry_and_order(tmp_path: Path):
    context = make_decodable_fixture(tmp_path)
    nodal, gp, receipt = _derive_native_weights(
        tmp_path / "static" / context.static_filename, context)
    np.testing.assert_allclose(gp, np.full((2, 4), .25), rtol=0, atol=1e-15)
    np.testing.assert_allclose(nodal, [.25, .5, .5, .25, .25, .25],
                               rtol=0, atol=1e-15)
    assert receipt["nodal_weight_sha256"] == hashlib.sha256(
        np.ascontiguousarray(nodal).tobytes()).hexdigest()


@pytest.mark.parametrize("stored", [
    np.array([[2.5, 5.0]], dtype=np.float64),
    np.array([[2.5, np.nan]], dtype=np.float64),
    np.empty((0, 0), dtype=np.float64),
])
def test_native_weight_derivation_rejects_non_scalar_thickness(tmp_path: Path, stored):
    context = make_decodable_fixture(tmp_path)
    static = tmp_path / "static" / context.static_filename
    with h5py.File(static, "r+") as handle:
        del handle["stage0b_static/geometry/t"]
        handle["stage0b_static/geometry"].create_dataset("t", data=stored)
    context = replace(context, static_sha256=sha(static))
    with pytest.raises(ValueError, match="one finite scalar"):
        _derive_native_weights(static, context)


def test_controlled_route_rejects_hash_valid_bad_intermediate_support(tmp_path: Path):
    context = make_decodable_fixture(tmp_path, corrupt_key="c0001_s02")
    with pytest.raises(ValueError, match="stored float64"):
        _qualify_decode_and_freeze(run_root=tmp_path, context=context)


@pytest.mark.parametrize("bad_load", [0.75, float("nan")])
def test_controlled_route_rejects_logical_alias_load_mismatch(tmp_path: Path, bad_load):
    context = make_decodable_fixture(tmp_path)
    index = tmp_path / "state_index.csv"
    with index.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    next(row for row in rows if row["state_key"] == "c0002_s00")[
        "imposed_displacement"] = repr(bad_load)
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(context, state_index_sha256=sha(index))
    with pytest.raises(ValueError, match="logical-to-physical load mismatch: c0002_s00"):
        _qualify_decode_and_freeze(run_root=tmp_path, context=context)

```
