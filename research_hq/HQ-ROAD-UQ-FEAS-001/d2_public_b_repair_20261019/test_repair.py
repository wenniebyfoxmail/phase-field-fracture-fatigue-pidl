"""Read-only, no-training checks for the D2 repair package."""
import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from repair_model import ResNet18UNet
import d2_runner


EXPECTED_WEIGHTS_SHA256 = "f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_model(weights):
    assert sha256(weights) == EXPECTED_WEIGHTS_SHA256
    torch.manual_seed(7)
    model = ResNet18UNet(weights).eval()
    for shape in [(1, 3, 64, 96), (1, 3, 65, 99)]:
        with torch.no_grad():
            logits, features = model(torch.rand(shape), return_feature=True)
        assert tuple(logits.shape) == (shape[0], 1, shape[2], shape[3])
        assert tuple(features.shape) == (shape[0], 512)
        assert torch.isfinite(logits).all() and torch.isfinite(features).all()


def test_gaps_loader(raw_zip):
    rows = d2_runner.gaps_pairs(raw_zip)
    assert len(rows) == 384
    nonempty = 0
    for row in rows:
        rgb, mask = d2_runner.load_gaps(row)
        assert rgb.shape == (1080, 1920, 3) and mask.shape == (1080, 1920)
        nonempty += bool(mask.any())
    assert nonempty == 382


def test_gate_math():
    rows = []
    for i in range(382):
        rows.append({"id": str(i), "error": 0.4 if i < 95 else 0.8,
                     "dice": 0.1 if i < 287 else 0.0,
                     "pred_empty": i >= 287, "pred_full": False,
                     "U_LC": float(i), "U_H": float(i), "U_Z": float(i)})
    result = d2_runner.summarize(rows)
    assert result["thresholds"] == {"nonempty_n": 382, "dice_positive_min": 287,
                                     "degenerate_max_exclusive": 191, "accepted_n": 95}
    assert result["F1"] is True and result["F2"] is True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--gapszip", required=True)
    args = parser.parse_args()
    test_model(Path(args.weights))
    test_gaps_loader(Path(args.gapszip))
    test_gate_math()
    print(json.dumps({"status": "pass", "checks": ["official_weights_strict_load",
          "even_and_odd_forward", "finite_logits_and_512d_features",
          "gaps_384_pair_decode_382_nonempty", "frozen_gate_arithmetic"],
          "training_or_optimizer_steps": 0, "road420_access": False}, indent=2))


if __name__ == "__main__":
    main()
