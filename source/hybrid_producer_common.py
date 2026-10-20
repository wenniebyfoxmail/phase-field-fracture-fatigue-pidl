"""Producer serialization, immutable package admission and field comparison."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

import numpy as np

from hybrid_inputs import sha256


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".json-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def append_event(path, value):
    with Path(path).open("a") as handle:
        handle.write(json.dumps(value, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def lossless_snapshot(source,target):
    """Recompress exact NPY member bytes, including all evidence/metadata.

    This changes ZIP storage only. Verify every uncompressed member digest;
    never decode, cast, drop or regenerate scientific arrays or certificates.
    """
    target=Path(target)
    fd,name=tempfile.mkstemp(prefix='.snapshot-',suffix='.npz',dir=target.parent)
    os.close(fd)
    def members(path):
        result={}
        with zipfile.ZipFile(path) as z:
            for item in z.infolist():
                if item.filename in result or not item.filename.endswith('.npy'):
                    raise RuntimeError('unexpected or duplicate NPZ member')
                h=hashlib.sha256()
                with z.open(item) as f:
                    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
                result[item.filename]=h.hexdigest()
        return result
    try:
        expected=members(source)
        with zipfile.ZipFile(source) as zin,zipfile.ZipFile(name,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as zout:
            for item in zin.infolist():
                with zin.open(item) as src,zout.open(item.filename,'w',force_zip64=True) as dst:
                    for block in iter(lambda:src.read(1024*1024),b''):dst.write(block)
        if members(name)!=expected:raise RuntimeError('lossless snapshot member bytes differ')
        with open(name,'rb') as f:os.fsync(f.fileno())
        os.replace(name,target)
    finally:
        if os.path.exists(name):os.unlink(name)


def verify_package(code_root, manifest):
    if object_sha(manifest["files"]) != manifest["artifact_id"]:
        raise RuntimeError("source artifact manifest corrupt")
    for path, expected in manifest["files"].items():
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("nonlocal source path")
        if sha256(Path(code_root) / path) != expected:
            raise RuntimeError(f"source bytes differ from reviewed package: {path}")


def classical_guess(current, previous, next_load, current_load, previous_load):
    """One fixed secant extrapolator; no online reference-based choice."""
    if previous is None or abs(current_load - previous_load) <= 1.e-14:
        return current.damage.copy()
    ratio = (next_load - current_load) / (current_load - previous_load)
    # Extrapolation is only a guess. During unload a negative ratio reverts to
    # the lower via clip; no healing or rolling lower occurs.
    return np.clip(current.damage + ratio * (current.damage - previous.damage), current.damage, 1.)


def compare_states(backend, candidate, reference):
    weights = backend.kin.det_jacobians
    area = float(weights.sum())
    result = {}
    for name, a, b in (("u", candidate.displacement[0::2], reference.displacement[0::2]),
                        ("v", candidate.displacement[1::2], reference.displacement[1::2]),
                        ("d", candidate.damage, reference.damage)):
        delta = (backend.gp @ (a-b)).reshape(-1, 4)
        result[name + "_gp_rms"] = float(np.sqrt(np.sum(weights * delta**2) / area))
    for name, a, b in (("A", candidate.accumulated, reference.accumulated),
                        ("r", candidate.driver, reference.driver),
                        ("f", candidate.fatigue, reference.fatigue)):
        result[name + "_gp_rms"] = float(np.sqrt(np.sum(weights * (a-b)**2) / area))
    return result
