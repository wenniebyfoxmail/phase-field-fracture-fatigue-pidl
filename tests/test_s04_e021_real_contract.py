"""Optional local-asset decoder tests with synthetic completion envelopes.

No parameter optimizer is stepped (LR replay uses an empty metadata optimizer). The declared steps/runtime in these temporary
unit fixtures are synthetic, not evidence of an actual E021 producer execution.
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "SENS_tensile"))
from aggregate_s04_e021_coordinate_screen import prepare_baseline, validate_record
from run_s04_e021_coordinate_screen import (
    monitor_full_field,
    support_diagnostics,
    final_metrics,
    sha256,
    PARAMETER_COUNT,
    RESIDUAL_PARAMETER_COUNT,
)
from s04_e021_screen import (
    CONTROL_LOCKS,
    build_candidate,
    PROTOCOL_REVISION,
    native_replay,
    schedule_identity,
)

PROJECT = REPO.parents[2]
OLD = PROJECT / "local_archive/experiments/S04-E019/producer_execution_v1/raw"
PREVIOUS = PROJECT / "local_archive/experiments/S04-E020/producer_execution_v1/raw"
pytestmark = pytest.mark.skipif(
    not OLD.exists() or not PREVIOUS.exists(),
    reason="optional exact local research assets absent",
)


@pytest.fixture(scope="module")
def data():
    old_threads = torch.get_num_threads()
    torch.set_num_threads(2)
    s = "c20s4"
    d = prepare_baseline(
        s,
        OLD / "inputs" / f"{s}.npz",
        OLD / "backbones" / s,
        OLD / "runs" / CONTROL_LOCKS[s]["run_id"],
    )
    yield {s: d}
    torch.set_num_threads(old_threads)


def assemble_fixture(path, data):
    s = "c20s4"
    d = data[s]
    previous = next((PREVIOUS / "runs").glob(f"*-{s}-localized-s7"))
    rec = json.loads((previous / "metrics.json").read_text())
    receipt = json.loads((previous / "RUN_RECEIPT.json").read_text())
    cp = torch.load(
        previous / "final_step_10000.pt", map_location="cpu", weights_only=True
    )
    g = rec["geometry"]
    mapping = d["coordinate_mapping"]
    model = build_candidate(7, "localized", g, copy.deepcopy(d["base_model"]), mapping)
    xy = torch.tensor(d["xy"], dtype=torch.float64)
    target = torch.tensor(d["equilibrated_uv"], dtype=torch.float64)
    mon = monitor_full_field(model, xy, target, d["mass"], d["damage"], 0)
    from run_s04_e021_coordinate_screen import predict_in_chunks

    uv = predict_in_chunks(model, xy).numpy()
    mon.update(support_diagnostics(uv, d["base_uv"], d, g))
    trace = []
    for k in range(0, 10001, 1000):
        t = dict(
            mon,
            step=k,
            lr_used=native_replay()[k - 1] if k else None,
            lr_next=native_replay()[k] if k < 10000 else None,
        )
        trace.append(t)
    for name in ["learning_rates.npy", "expected_learning_rates.npy"]:
        np.save(path / name, np.array(native_replay(), dtype="<f8"))
    (path / "coordinate_map.json").write_text(json.dumps(mapping))
    pre = dict(
        protocol_revision=PROTOCOL_REVISION,
        state=s,
        seed=7,
        alpha="0.7",
        arm="localized",
        run_id=receipt["run_id"],
        code_commit="0" * 40,
        reference_sha256=rec["reference_sha256"],
        backbone_digest=d["base_digest"],
        initial_residual_digest=d["initial_residual_digest"],
        initial_model_digest=d["initial_coordinate_model_digest"],
        coordinate_mapping=mapping,
        coordinate_map_sha256=sha256(path / "coordinate_map.json"),
        expected_learning_rates_sha256=sha256(path / "expected_learning_rates.npy"),
        lr_schedule=schedule_identity(native_replay()),
        runtime=CONTROL_LOCKS[s]["runtime"],
        new_optimizer_steps=0,
        dirty=False,
        created_utc="2026-10-15T00:00:00Z",
    )
    (path / "PRE_UPDATE.json").write_text(json.dumps(pre))
    common = dict(
        protocol_revision=PROTOCOL_REVISION,
        lr_schedule=pre["lr_schedule"],
        coordinate_mapping=mapping,
        coordinate_map_sha256=pre["coordinate_map_sha256"],
        expected_learning_rates_sha256=pre["expected_learning_rates_sha256"],
        learning_rates_sha256=sha256(path / "learning_rates.npy"),
        pre_update_sha256=sha256(path / "PRE_UPDATE.json"),
    )
    for asset in [rec, cp, receipt]:
        asset.update(common)
    cp["model_state_dict"] = {
        k: v.detach().cpu() for k, v in model.state_dict().items()
    }
    torch.save(cp, path / "final_step_10000.pt")
    np.savez_compressed(path / "prediction.npz", uv=uv)
    (path / "monitoring.json").write_text(json.dumps(trace))
    rec.update(
        metrics=final_metrics(d, uv),
        baseline_metrics=d["base_metrics"],
        baseline_regions=trace[0],
        support_diagnostics=support_diagnostics(uv, d["base_uv"], d, g),
        started_utc="2026-10-15T00:00:01Z",
        finished_utc="2026-10-15T00:00:02Z",
    )
    receipt.update(
        code_commit="0" * 40,
        dirty=False,
        started_utc=rec["started_utc"],
        finished_utc=rec["finished_utc"],
    )
    rebind(path, rec, receipt)
    return rec, receipt


def rebind(path, rec, receipt):
    for filename, key in [
        ("final_step_10000.pt", "checkpoint_sha256"),
        ("prediction.npz", "prediction_sha256"),
        ("monitoring.json", "monitoring_sha256"),
    ]:
        rec[key] = receipt[key] = sha256(path / filename)
    (path / "metrics.json").write_text(json.dumps(rec))
    receipt["metrics_sha256"] = sha256(path / "metrics.json")
    receipt["archive_file_hashes"] = {
        name: sha256(path / name)
        for name in [
            "final_step_10000.pt",
            "prediction.npz",
            "monitoring.json",
            "metrics.json",
            "learning_rates.npy",
            "expected_learning_rates.npy",
            "coordinate_map.json",
            "PRE_UPDATE.json",
        ]
    }
    (path / "RUN_RECEIPT.json").write_text(json.dumps(receipt))


@pytest.mark.parametrize(
    "mode",
    [
        None,
        "actual_map_buffer",
        "pre_counter",
        "pre_time",
        "reference_rho",
        "prediction",
    ],
)
def test_full_numerical_decoder_with_temporary_synthetic_envelope(tmp_path, data, mode):
    rec, receipt = assemble_fixture(tmp_path, data)
    if mode == "actual_map_buffer":
        cp = torch.load(
            tmp_path / "final_step_10000.pt", map_location="cpu", weights_only=True
        )
        cp["model_state_dict"]["local_center"][0] += 0.01
        torch.save(cp, tmp_path / "final_step_10000.pt")
    if mode in ["pre_counter", "pre_time"]:
        p = tmp_path / "PRE_UPDATE.json"
        pre = json.loads(p.read_text())
        pre["new_optimizer_steps"] = 1 if mode == "pre_counter" else 0
        if mode == "pre_time":
            pre["created_utc"] = "2026-10-15T00:00:03Z"
        p.write_text(json.dumps(pre))
        h = sha256(p)
        cp = torch.load(
            tmp_path / "final_step_10000.pt", map_location="cpu", weights_only=True
        )
        cp["pre_update_sha256"] = h
        torch.save(cp, tmp_path / "final_step_10000.pt")
        rec["pre_update_sha256"] = receipt["pre_update_sha256"] = h
    if mode == "reference_rho":
        rec["baseline_metrics"] = dict(rec["baseline_metrics"], reference_rho_u=1e-7)
    if mode == "prediction":
        uv = np.load(tmp_path / "prediction.npz")["uv"]
        uv[200, 0] += 0.001
        np.savez_compressed(tmp_path / "prediction.npz", uv=uv)
    rebind(tmp_path, rec, receipt)
    if mode is None:
        row = validate_record(tmp_path / "metrics.json", "0" * 40, data)
        assert row["displacement_mass_rms_over_abs_Us"] > 0.001
    else:
        with pytest.raises((ValueError, AssertionError)):
            validate_record(tmp_path / "metrics.json", "0" * 40, data)
