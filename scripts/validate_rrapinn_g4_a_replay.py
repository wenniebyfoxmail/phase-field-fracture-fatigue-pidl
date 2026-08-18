#!/usr/bin/env python3
"""Validate the Taobo A-arm c60-to-step305 replay sentinel by decoded values."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


STEP = 305
HISTORY_LENGTH = STEP + 1
REFERENCE_HASHES = {
    "checkpoint_step_305.pt": "3cb19e54cf000e577ce74d8ebcae6e5360ec2e678849ef7d8c282474773cb1b4",
    "trained_1NN_305.pt": "03d9c16043dbd293a4db20a82591c84b0fc775249ab5d132c4adb70ff4c35a39",
}
HISTORIES = (
    "E_el_vs_cycle.npy", "alpha_bar_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy",
    "x_tip_vs_cycle.npy", "Kt_vs_cycle.npy", "energy_gradient_terms_vs_cycle.npy",
)
REFERENCE_HISTORY_CONTRACT = {
    "E_el_vs_cycle.npy": ("0ae5520c58431f80615b54534f3395b12f65ee76a8f7831a0edd2caf9723ae71", (448,), "float64"),
    "alpha_bar_vs_cycle.npy": ("10d23fd4ce8e6b87ed7b9117e94ebadbcf401362cb2b8a9674961876d2aa8cc1", (448, 3), "float64"),
    "x_tip_alpha_vs_cycle.npy": ("ba24cd21ec5d4a497bcf4c75eda72b034e1853c82327b87b0c26724f8723b1d2", (448,), "float64"),
    "x_tip_vs_cycle.npy": ("ba24cd21ec5d4a497bcf4c75eda72b034e1853c82327b87b0c26724f8723b1d2", (448,), "float64"),
    "Kt_vs_cycle.npy": ("d738ba1d18d813a0ab7ef35aabd2fd1650ededdf225625cddf3479b83a4fec22", (448,), "float64"),
    "energy_gradient_terms_vs_cycle.npy": ("f1394b4b68b143d4ba15b70808859b6792a3fb1ac60ee95a23ceb46f8e872f56", (448, 7), "float64"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _equal(left, right):
    if torch.is_tensor(left) and torch.is_tensor(right):
        return left.shape == right.shape and left.dtype == right.dtype and torch.equal(left, right)
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_equal(left[key], right[key]) for key in left)
    return left == right


def validate_reference_history(path: Path, expected) -> np.ndarray:
    expected_sha, expected_shape, expected_dtype = expected
    if sha256(path) != expected_sha:
        raise RuntimeError(f"frozen reference history hash mismatch: {path.name}")
    array = np.load(path, allow_pickle=False)
    if array.shape != expected_shape or str(array.dtype) != expected_dtype:
        raise RuntimeError(f"frozen reference history schema mismatch: {path.name}")
    return array


def validate_replay(reference: Path, candidate: Path) -> dict:
    reference = Path(reference).resolve()
    candidate = Path(candidate).resolve()
    for name, expected in REFERENCE_HASHES.items():
        if sha256(reference / name) != expected:
            raise RuntimeError(f"frozen step305 reference hash mismatch: {name}")
    reference_model = torch.load(
        reference / "trained_1NN_305.pt", map_location="cpu", weights_only=True
    )
    candidate_model = torch.load(
        candidate / "trained_1NN_305.pt", map_location="cpu", weights_only=True
    )
    if not _equal(reference_model, candidate_model):
        raise RuntimeError("FAIL_IMPLEMENTATION_DRIFT: decoded model tensors differ")
    reference_checkpoint = torch.load(
        reference / "checkpoint_step_305.pt", map_location="cpu", weights_only=False
    )
    candidate_checkpoint = torch.load(
        candidate / "checkpoint_step_305.pt", map_location="cpu", weights_only=False
    )
    if not _equal(reference_checkpoint, candidate_checkpoint):
        raise RuntimeError("FAIL_IMPLEMENTATION_DRIFT: decoded checkpoint state differs")
    history_receipts = {}
    for name in HISTORIES:
        reference_array = validate_reference_history(
            reference / name, REFERENCE_HISTORY_CONTRACT[name]
        )
        candidate_array = np.load(candidate / name, allow_pickle=False)
        if candidate_array.shape[0] != HISTORY_LENGTH:
            raise RuntimeError(f"FAIL_IMPLEMENTATION_DRIFT: candidate {name} length is not 306")
        expected_prefix = reference_array[:HISTORY_LENGTH]
        if candidate_array.shape != expected_prefix.shape or not np.array_equal(
            candidate_array, expected_prefix, equal_nan=True
        ):
            raise RuntimeError(f"FAIL_IMPLEMENTATION_DRIFT: history differs: {name}")
        history_receipts[name] = {
            "reference_sha256": REFERENCE_HISTORY_CONTRACT[name][0],
            "reference_shape": list(REFERENCE_HISTORY_CONTRACT[name][1]),
            "shape": list(candidate_array.shape),
            "candidate_sha256": sha256(candidate / name),
        }
    return {
        "schema": "rrapinn-g4-a-replay-sentinel-v1",
        "status": "PASS_EXACT_DECODED_REPLAY",
        "training_authorized": False,
        "reference_step": STEP,
        "comparison": "decoded_tensor_and_array_exact_with_nan_equality",
        "serialized_byte_identity_required": False,
        "histories": history_receipts,
        "claim_boundary": "A-arm implementation-drift sentinel only; no efficacy claim.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference-best-models", type=Path, required=True)
    ap.add_argument("--candidate-best-models", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    payload = validate_replay(args.reference_best_models, args.candidate_best_models)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
