"""Persist and replay one accepted cyclic step without running a solver.

The caller supplies the physical replay. A receipt alone is never sufficient:
both entry points load the tensor bundle with ``weights_only=True`` and require
a successful replay of those loaded values. Tensors are snapshotted on CPU;
arbitrary Python objects, tensor subclasses, and non-finite values are refused.

Each step needs a fresh directory whose parent already exists. Failed writes
leave that directory incomplete and it must not be reused for a retry.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import torch


BUNDLE_NAME = "bundle.pt"
COMPLETION_NAME = "completion.json"
SCHEMA_VERSION = 1
_REQUIRED = {
    "network_state", "common_problem", "old_state", "fields", "history",
    "f_solve", "f_commit", "state_key", "provenance", "acceptance_records",
}


class PersistenceVerificationError(RuntimeError):
    """No verified state is available for continuation or post-processing."""


def _copy_supported(value, path="payload", *, json_only=False, ancestors=()):
    """Copy the deliberately small serialization vocabulary, without pickle hooks."""
    kind = type(value)
    if kind is torch.Tensor and not json_only:
        if value.layout != torch.strided or value.is_quantized or value.device.type == "meta":
            raise ValueError(f"{path}: only ordinary dense materialized tensors are supported")
        result = value.detach().cpu().clone()
        if (result.is_floating_point() or result.is_complex()) and not bool(torch.isfinite(result).all()):
            raise ValueError(f"{path}: non-finite tensor")
        return result
    if kind in (type(None), bool, int, str):
        return value
    if kind is float:
        if not math.isfinite(value):
            raise ValueError(f"{path}: non-finite scalar")
        return value
    if kind not in ((dict, list) if json_only else (dict, list, tuple)):
        raise TypeError(f"{path}: unsupported value type {kind.__name__}")
    if id(value) in ancestors or len(ancestors) >= 64:
        raise ValueError(f"{path}: cyclic or excessively nested container")
    parents = (*ancestors, id(value))
    if kind is dict:
        if any(type(key) is not str for key in value):
            raise TypeError(f"{path}: all mapping keys must be strings")
        return {key: _copy_supported(item, f"{path}.{key}", json_only=json_only,
                                     ancestors=parents) for key, item in value.items()}
    items = [_copy_supported(item, f"{path}[{index}]", json_only=json_only,
                             ancestors=parents) for index, item in enumerate(value)]
    return tuple(items) if kind is tuple else items


def _snapshot_payload(payload):
    if type(payload) is not dict or not _REQUIRED.issubset(payload):
        raise ValueError(f"payload requires keys {sorted(_REQUIRED)}")
    network = payload["network_state"]
    if type(network) not in (dict, OrderedDict) or not network:
        raise ValueError("network_state must be a nonempty tensor mapping")
    if any(type(key) is not str or type(value) is not torch.Tensor
           for key, value in network.items()):
        raise TypeError("network_state requires string keys and ordinary tensors")
    # nn.Module.state_dict() commonly returns OrderedDict. Its tensor mapping is
    # made explicit; arbitrary attached Python attributes are not serialized.
    canonical = dict(payload)
    canonical["network_state"] = dict(network)
    for name in ("common_problem", "old_state", "fields", "state_key", "provenance"):
        if type(canonical[name]) is not dict or not canonical[name]:
            raise ValueError(f"{name} must be a nonempty plain dictionary")
    for name in ("f_solve", "f_commit"):
        if type(canonical[name]) is not torch.Tensor:
            raise TypeError(f"{name} must be an ordinary tensor")
    for name in ("common_problem", "state_key", "provenance", "acceptance_records"):
        _copy_supported(canonical[name], name, json_only=True)
    if "metadata" in canonical:
        _copy_supported(canonical["metadata"], "metadata", json_only=True)
    return _copy_supported(canonical)


def _assert_same(expected, actual, path="payload"):
    if type(expected) is not type(actual):
        raise PersistenceVerificationError(f"{path}: type changed after serialization or replay")
    if type(expected) is torch.Tensor:
        if (expected.dtype != actual.dtype or expected.shape != actual.shape
                or actual.device.type != "cpu" or actual.requires_grad
                or actual.layout != torch.strided or not torch.equal(expected, actual)):
            raise PersistenceVerificationError(f"{path}: tensor dtype, shape or values changed")
    elif type(expected) is dict:
        if expected.keys() != actual.keys():
            raise PersistenceVerificationError(f"{path}: mapping keys changed")
        for key in expected:
            _assert_same(expected[key], actual[key], f"{path}.{key}")
    elif type(expected) in (list, tuple):
        if len(expected) != len(actual):
            raise PersistenceVerificationError(f"{path}: sequence length changed")
        for index, (left, right) in enumerate(zip(expected, actual)):
            _assert_same(left, right, f"{path}[{index}]")
    elif expected != actual:
        raise PersistenceVerificationError(f"{path}: scalar value changed")


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sync_directory(directory):
    """Best effort on filesystems that do not support directory fsync."""
    descriptor = None
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fsync(descriptor)
    except OSError:
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return True


def _atomic_write(directory, name, writer):
    destination = directory / name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite {destination}")
    # The directory was exclusively created for this call. Temp files remain
    # available for diagnosis if writing or publishing fails.
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{name}.", suffix=".tmp",
                                     dir=directory, delete=False) as stream:
        temporary = Path(stream.name)
        writer(stream)
        stream.flush()
        os.fsync(stream.fileno())
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite {destination}")
    os.rename(temporary, destination)
    return _sync_directory(directory)


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       allow_nan=False, indent=2) + "\n").encode("utf-8")


def _read_bundle(directory):
    bundle = directory / BUNDLE_NAME
    if bundle.is_symlink() or not bundle.is_file():
        raise PersistenceVerificationError("missing regular tensor bundle")
    with bundle.open("rb") as stream:
        loaded = torch.load(stream, map_location="cpu", weights_only=True)
    # Validate without silently normalizing types in the loaded artifact.
    validated = _snapshot_payload(loaded)
    _assert_same(validated, loaded)
    return loaded


def _metadata(payload):
    return {
        "common_problem": payload["common_problem"],
        "provenance": payload["provenance"],
        "acceptance_records": payload["acceptance_records"],
        "payload_metadata": payload.get("metadata", {}),
    }


def _run_replay(loaded, replay):
    if not callable(replay):
        raise TypeError("a physical replay callback is required")
    before = _snapshot_payload(loaded)
    result = replay(loaded)
    _assert_same(before, loaded)
    if type(result) is not dict or result.get("accepted") is not True:
        raise PersistenceVerificationError("loaded-state replay did not explicitly accept the state")
    return _copy_supported(result, "replay", json_only=True)


def persist_verified_step(directory, payload, replay):
    """Save, strictly reload and replay a step, returning only its loaded payload.

    Required payload keys are listed in ``_REQUIRED``. ``common_problem``,
    ``state_key``, ``provenance``, ``acceptance_records`` and optional ``metadata``
    contain ordinary finite JSON values. Other fields may also contain dense
    tensors. Network OrderedDicts are normalized to plain tensor dictionaries.
    CPU/device conversion and detachment are intentional snapshot operations.
    """
    directory = Path(directory)
    # Never touch an existing step, including an incomplete prior attempt.
    directory.mkdir(parents=False, exist_ok=False)
    completion = directory / COMPLETION_NAME
    try:
        if not callable(replay):
            raise TypeError("a physical replay callback is required")
        snapshot = _snapshot_payload(payload)
        directory_synced = _atomic_write(directory, BUNDLE_NAME,
                                          lambda stream: torch.save(snapshot, stream))
        bundle = directory / BUNDLE_NAME
        digest = _sha256(bundle)
        loaded = _read_bundle(directory)
        _assert_same(snapshot, loaded)
        replay_record = _run_replay(loaded, replay)
        if _sha256(bundle) != digest:
            raise PersistenceVerificationError("bundle changed during loaded-state replay")
        record = {
            "schema_version": SCHEMA_VERSION, "complete": True,
            "bundle": BUNDLE_NAME, "bundle_sha256": digest,
            "state_key": loaded["state_key"], "metadata": _metadata(loaded),
            "replay": replay_record, "bundle_directory_fsync": directory_synced,
        }
        _atomic_write(directory, COMPLETION_NAME,
                      lambda stream: stream.write(_json_bytes(record)))
        return loaded
    except BaseException as error:
        # Completion is our last publication. Never leave it on a failed call.
        if completion.exists() or completion.is_symlink():
            completion.unlink()
            _sync_directory(directory)
        try:
            _atomic_write(directory, "incomplete.json", lambda stream: stream.write(
                _json_bytes({"complete": False, "error_type": type(error).__name__,
                             "reason": str(error)})))
        except Exception:
            pass  # Absence of completion remains the authoritative failure signal.
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        raise PersistenceVerificationError(f"step remains incomplete: {error}") from error


def _read_completion(path):
    if path.is_symlink() or not path.is_file():
        raise PersistenceVerificationError("step has no regular completion record")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key}")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError(f"non-finite JSON constant {value}")
    with path.open("r", encoding="utf-8") as stream:
        record = json.load(stream, object_pairs_hook=unique_object,
                           parse_constant=invalid_constant)
    _copy_supported(record, "completion", json_only=True)
    if (type(record) is not dict or type(record.get("schema_version")) is not int
            or record["schema_version"] != SCHEMA_VERSION
            or record.get("complete") is not True or record.get("bundle") != BUNDLE_NAME):
        raise PersistenceVerificationError("invalid completion record")
    return record


def load_verified_step(directory, replay):
    """Read-only load with hash, metadata and fresh physical replay verification.

    A previous completion record cannot substitute for the current replay.
    Rejected or corrupted artifacts are never returned and are not rewritten.
    """
    directory = Path(directory)
    try:
        if directory.is_symlink() or not directory.is_dir():
            raise PersistenceVerificationError("step must be a real directory")
        incomplete = directory / "incomplete.json"
        if incomplete.exists() or incomplete.is_symlink():
            raise PersistenceVerificationError("step is explicitly marked incomplete")
        record = _read_completion(directory / COMPLETION_NAME)
        bundle = directory / BUNDLE_NAME
        if bundle.is_symlink() or not bundle.is_file():
            raise PersistenceVerificationError("missing regular tensor bundle")
        digest = _sha256(bundle)
        if record.get("bundle_sha256") != digest:
            raise PersistenceVerificationError("bundle checksum differs from completion record")
        loaded = _read_bundle(directory)
        _assert_same(record.get("state_key"), loaded["state_key"], "state_key")
        _assert_same(record.get("metadata"), _metadata(loaded), "metadata")
        if type(record.get("replay")) is not dict or record["replay"].get("accepted") is not True:
            raise PersistenceVerificationError("completion does not contain an accepted replay")
        _run_replay(loaded, replay)
        if _sha256(bundle) != digest:
            raise PersistenceVerificationError("bundle changed during loaded-state replay")
        return loaded
    except Exception as error:
        if isinstance(error, PersistenceVerificationError):
            raise
        raise PersistenceVerificationError(f"step cannot be verified: {error}") from error
