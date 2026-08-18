#!/usr/bin/env python3
"""Build the future-free U0.12 c60 restart bundle without entering training."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch


EXPECTED_SOURCE_SHA256 = {
    "trained_1NN_initTraining.pt": "1044740e0004fe11688ec4930a4c3ea25cf0bd252bb66b29e6ddca6bbeb07a9e",
    "trained_1NN_300.pt": "1316984f53297075dccadd38efd04972ce3942caa294b4b0a4f61c3c87b10d41",
    "checkpoint_step_300.pt": "771bf8122c34097ddaee55e9952c3bef187aa320dfcd02eed148febe6e10e729",
    "E_el_vs_cycle.npy": "0ae5520c58431f80615b54534f3395b12f65ee76a8f7831a0edd2caf9723ae71",
    "alpha_bar_vs_cycle.npy": "10d23fd4ce8e6b87ed7b9117e94ebadbcf401362cb2b8a9674961876d2aa8cc1",
    "x_tip_alpha_vs_cycle.npy": "ba24cd21ec5d4a497bcf4c75eda72b034e1853c82327b87b0c26724f8723b1d2",
    "x_tip_vs_cycle.npy": "ba24cd21ec5d4a497bcf4c75eda72b034e1853c82327b87b0c26724f8723b1d2",
    "Kt_vs_cycle.npy": "d738ba1d18d813a0ab7ef35aabd2fd1650ededdf225625cddf3479b83a4fec22",
    "time_vs_cycle.npy": "a390b0d731a56ab81f9db6055dee8a47e32ddab31b32b2747f82a85abcc2a7d6",
    "energy_gradient_terms_vs_cycle.npy": "f1394b4b68b143d4ba15b70808859b6792a3fb1ac60ee95a23ceb46f8e872f56",
}
EXPECTED_SETTINGS_SHA256 = "015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047"
EXPECTED_MESH_SHA256 = "16b447e3dd789e300f5181c3cf9b34322e4f27575867b354f55473d2969a9ed8"
HISTORY_ROLES = {
    "E_el_vs_cycle.npy": "elastic_energy_history",
    "alpha_bar_vs_cycle.npy": "mean_damage_history",
    "x_tip_alpha_vs_cycle.npy": "damage_tip_history",
    "x_tip_vs_cycle.npy": "damage_tip_history_legacy_alias",
    "Kt_vs_cycle.npy": "stress_intensity_history",
    "time_vs_cycle.npy": "runtime_history",
    "energy_gradient_terms_vs_cycle.npy": "energy_gradient_history",
}
MODEL_ROLES = {
    "trained_1NN_initTraining.pt": "pretraining_state",
    "trained_1NN_300.pt": "restart_model_state",
    "checkpoint_step_300.pt": "restart_fatigue_state",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--mesh", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    archive = args.archive.resolve()
    source = archive / "best_models"
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite restart bundle: {output}")
    settings = archive / "model_settings.txt"
    if _sha256(settings) != EXPECTED_SETTINGS_SHA256:
        raise RuntimeError("U0.12 source model_settings.txt hash mismatch")
    if _sha256(args.mesh.resolve()) != EXPECTED_MESH_SHA256:
        raise RuntimeError("U0.12 PIDL mesh hash mismatch")
    actual = {name: _sha256(source / name) for name in EXPECTED_SOURCE_SHA256}
    if actual != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(f"U0.12 c60 source hash mismatch: {actual}")

    checkpoint = torch.load(
        source / "checkpoint_step_300.pt", map_location="cpu", weights_only=False
    )
    required_state = {"hist_alpha", "hist_fat", "psi_plus_prev", "psi_history_elem"}
    if not required_state.issubset(checkpoint):
        raise RuntimeError("c60 checkpoint is missing required fatigue state")
    if checkpoint.get("_frac_detected") is not False or checkpoint.get("_frac_cycle") is not None:
        raise RuntimeError("c60 checkpoint is not a clean pre-event state")

    root = Path(__file__).parents[1]
    sys.path.insert(0, str(root / "SENS_tensile"))
    from rrapinn_g4_restart import publish_directory_exclusive, validate_bundle

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=output.parent))
    try:
        records = {}
        for name in EXPECTED_SOURCE_SHA256:
            src = source / name
            dst = temporary / name
            if name.endswith(".npy"):
                array = np.load(src, allow_pickle=False)
                if array.ndim < 1 or array.shape[0] < 301:
                    raise RuntimeError(f"source history is shorter than c60: {name}")
                truncated = np.asarray(array[:301]).copy()
                with dst.open("xb") as handle:
                    np.save(handle, truncated, allow_pickle=False)
                records[name] = {
                    "sha256": _sha256(dst),
                    "source_sha256": EXPECTED_SOURCE_SHA256[name],
                    "shape": list(truncated.shape),
                    "dtype": str(truncated.dtype),
                    "semantic_role": HISTORY_ROLES[name],
                    "last_raw_step": 300,
                    "finite_policy": {
                        "allow_nan": name == "Kt_vs_cycle.npy",
                        "allow_inf": False,
                    },
                    "nan_count": int(np.isnan(truncated).sum()),
                    "inf_count": int(np.isinf(truncated).sum()),
                }
            else:
                shutil.copy2(src, dst)
                records[name] = {
                    "sha256": _sha256(dst),
                    "source_sha256": EXPECTED_SOURCE_SHA256[name],
                    "semantic_role": MODEL_ROLES[name],
                    "last_raw_step": 300,
                }
        manifest = {
            "schema": "rrapinn-g4-c60-restart-bundle-v1",
            "training_authorized": False,
            "development_case": "U0.12",
            "start_state": {
                "label": "c60_unloaded_post_commit",
                "raw_step": 300,
                "next_raw_step": 301,
                "history_length": 301,
                "future_history_forbidden": True,
            },
            "source": {
                "archive": str(archive),
                "model_settings_sha256": EXPECTED_SETTINGS_SHA256,
                "mesh_sha256": EXPECTED_MESH_SHA256,
            },
            "files": records,
            "claim_boundary": "Restart materialization only; no training or efficacy claim.",
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        validate_bundle(temporary)
        publish_directory_exclusive(temporary, output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    validated = validate_bundle(output)
    print(json.dumps(validated, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
