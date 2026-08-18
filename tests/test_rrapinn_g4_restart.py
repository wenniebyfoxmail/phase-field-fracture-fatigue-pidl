from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from rrapinn_g4_restart import (
    HISTORY_ROLES,
    FROZEN_FILE_SOURCE_SHA256,
    MODEL_ROLES,
    REQUIRED_FILES,
    SOURCE_MESH_SHA256,
    SOURCE_SETTINGS_SHA256,
    publish_directory_exclusive,
    stage_bundle,
    validate_bundle,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_bundle(root: Path) -> Path:
    root.mkdir()
    records = {}
    for name in sorted(REQUIRED_FILES):
        path = root / name
        if name.endswith(".npy"):
            array = np.arange(301, dtype=np.float64)
            np.save(path, array, allow_pickle=False)
            records[name] = {
                "sha256": sha256(path),
                "source_sha256": FROZEN_FILE_SOURCE_SHA256[name],
                "shape": [301],
                "dtype": "float64",
                "semantic_role": HISTORY_ROLES[name],
                "last_raw_step": 300,
                "finite_policy": {
                    "allow_nan": name == "Kt_vs_cycle.npy",
                    "allow_inf": False,
                },
                "nan_count": 0,
                "inf_count": 0,
            }
        else:
            path.write_bytes(name.encode("utf-8"))
            records[name] = {
                "sha256": sha256(path),
                "source_sha256": FROZEN_FILE_SOURCE_SHA256[name],
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
            "model_settings_sha256": SOURCE_SETTINGS_SHA256,
            "mesh_sha256": SOURCE_MESH_SHA256,
        },
        "files": records,
        "claim_boundary": "test",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_validate_and_stage_exact_bundle(tmp_path: Path):
    bundle = make_bundle(tmp_path / "bundle")
    manifest_sha = sha256(bundle / "manifest.json")
    assert validate_bundle(bundle, manifest_sha)["start_state"]["raw_step"] == 300
    destination = tmp_path / "staged"
    stage_bundle(bundle, destination, manifest_sha)
    assert {p.name for p in destination.iterdir()} == REQUIRED_FILES


def test_rejects_future_history_unexpected_file_and_tampering(tmp_path: Path):
    bundle = make_bundle(tmp_path / "bundle")
    np.save(bundle / "E_el_vs_cycle.npy", np.arange(302), allow_pickle=False)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        validate_bundle(bundle)

    bundle = make_bundle(tmp_path / "bundle2")
    (bundle / "extra.pt").write_bytes(b"future")
    with pytest.raises(ValueError, match="unexpected"):
        validate_bundle(bundle)

    bundle = make_bundle(tmp_path / "bundle3")
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["start_state"]["future_history_forbidden"] = False
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="start-state"):
        validate_bundle(bundle)


def test_staging_requires_empty_destination(tmp_path: Path):
    bundle = make_bundle(tmp_path / "bundle")
    manifest_sha = sha256(bundle / "manifest.json")
    destination = tmp_path / "staged"
    destination.mkdir()
    (destination / "existing").write_text("do not overwrite")
    with pytest.raises(FileExistsError, match="not exist"):
        stage_bundle(bundle, destination, manifest_sha)


def test_staging_does_not_replace_existing_empty_destination(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "owned").write_text("source")
    destination = tmp_path / "staged"
    destination.mkdir()
    with pytest.raises(FileExistsError, match="refusing"):
        publish_directory_exclusive(source, destination)
    assert destination.is_dir() and not any(destination.iterdir())
    assert (source / "owned").read_text() == "source"


def test_kt_nan_is_explicitly_allowed_but_inf_is_rejected(tmp_path: Path):
    bundle = make_bundle(tmp_path / "bundle")
    path = bundle / "Kt_vs_cycle.npy"
    array = np.load(path, allow_pickle=False)
    array[0] = np.nan
    np.save(path, array, allow_pickle=False)
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["files"][path.name]["sha256"] = sha256(path)
    manifest["files"][path.name]["nan_count"] = 1
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    validate_bundle(bundle)

    array[1] = np.inf
    np.save(path, array, allow_pickle=False)
    manifest["files"][path.name]["sha256"] = sha256(path)
    manifest["files"][path.name]["inf_count"] = 1
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="finite-value"):
        validate_bundle(bundle)


def test_runner_resume_requires_the_full_frozen_protocol(tmp_path: Path):
    bundle = make_bundle(tmp_path / "bundle")
    manifest_sha = sha256(bundle / "manifest.json")
    spec = importlib.util.spec_from_file_location(
        "g4_resume_runner", ROOT / "SENS_tensile" / "run_fem_mesh_probe_driver_umax.py"
    )
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    parser = runner._build_parser()
    frozen = [
        "0.12", "--resume-bundle", str(bundle),
        "--resume-bundle-manifest-sha256", manifest_sha,
        "--mechanical-risk-mode", "absent",
        "--mechanical-residual-export-steps", "379,409",
        "--boundary-first-detect-receipt", "--hard-stop-physical-cycle", "92",
        "--hard-alpha-recovery-step",
        "--displacement-steps", "0.03,0.06,0.09,0.12,0",
        "--history-driver-reduction-mode", "fem_gp_tri3_g_mean",
        "--fem-irr-penalty", "--epochs-rprop", "10000",
        "--epochs-lbfgs", "0", "--optim-rel-tol", "5e-7",
        "--fresh-output-required", "--require-clean-git",
        "--required-head-commit", "a" * 40,
    ]
    assert runner._validate_restart_args(parser.parse_args(frozen))["start_state"]["raw_step"] == 300
    with pytest.raises(ValueError, match="frozen U0.12 protocol"):
        runner._validate_restart_args(parser.parse_args(frozen[:-2]))
