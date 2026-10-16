"""Optional local-asset decoder tests with synthetic completion envelopes.

No parameter optimizer is stepped (LR replay uses an empty metadata optimizer). The declared steps/runtime in these temporary
unit fixtures are synthetic, not evidence of an actual E023 producer execution.
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
from aggregate_s04_e023_head_scale_screen import prepare_baseline, validate_record
from run_s04_e023_head_scale_screen import (
    monitor_full_field,
    support_diagnostics,
    final_metrics,
    sha256,
    PARAMETER_COUNT,
    RESIDUAL_PARAMETER_COUNT,
)
from s04_e023_head_scale import (
    CONTROL_LOCKS,
    DIRECT_LOCKS,
    ACTIVATION_RULE,
    HEAD_SCALE_RULE,
    LEAK_LOCKS,
    gradient_coordinate_audit,
    build_candidate,
    PROTOCOL_REVISION,
    native_replay,
    schedule_identity,
)

PROJECT = REPO.parents[2]
OLD = PROJECT / "local_archive/experiments/S04-E019/producer_execution_v1/raw"
PREVIOUS = PROJECT / "local_archive/experiments/S04-E021/producer_execution_v2/raw"
LEAK = PROJECT / "local_archive/experiments/S04-E022/producer_execution_v1/raw"
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
        PREVIOUS / "runs" / DIRECT_LOCKS[s]["run_id"],
        LEAK / "runs" / LEAK_LOCKS[s]["run_id"],
    )
    # Synthetic envelope uses Mac-native metadata, NOT a formal producer admission.
    d["direct_actual_rates"] = np.asarray(native_replay(), dtype="<f8")
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
    model, calibration = build_candidate(
        7, "localized", g, copy.deepcopy(d["base_model"]), mapping, d["xy"], d["mass"]
    )
    xy = torch.tensor(d["xy"], dtype=torch.float64)
    target = torch.tensor(d["equilibrated_uv"], dtype=torch.float64)
    mon = monitor_full_field(model, xy, target, d["mass"], d["damage"], 0)
    from run_s04_e023_head_scale_screen import predict_in_chunks

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
    (path / "head_scale.json").write_text(json.dumps(d["head_calibration"]))
    (path / "head_gradient_preflight.json").write_text(
        json.dumps(d["head_gradient_preflight"])
    )
    pre = dict(
        protocol_revision=PROTOCOL_REVISION,
        activation_rule=ACTIVATION_RULE,
        head_scale_rule=HEAD_SCALE_RULE,
        paired_e022_control_lock=LEAK_LOCKS[s],
        head_scale_sha256=sha256(path / "head_scale.json"),
        head_gradient_preflight_sha256=sha256(path / "head_gradient_preflight.json"),
        paired_e021_control_lock=DIRECT_LOCKS[s],
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
        activation_rule=ACTIVATION_RULE,
        head_scale_rule=HEAD_SCALE_RULE,
        paired_e022_control_lock=LEAK_LOCKS[s],
        head_scale_sha256=sha256(path / "head_scale.json"),
        head_gradient_preflight_sha256=sha256(path / "head_gradient_preflight.json"),
        paired_e021_control_lock=DIRECT_LOCKS[s],
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
        e021_direct_control_admission=d["e021_direct_control"],
        e022_direct_control_admission=d["leak_control"],
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
            "head_scale.json",
            "head_gradient_preflight.json",
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
        "candidate_rho",
        "candidate_strain",
        "candidate_reference_rho",
        "candidate_strain_norm",
        "candidate_bc",
        "activation_metadata",
        "direct_control_identity",
        "direct_native_mismatch",
        "pre_activation",
        "checkpoint_activation",
        "head_buffer",
        "scale_file",
        "head_pre_rule",
    ],
)
def test_full_numerical_decoder_with_temporary_synthetic_envelope(tmp_path, data, mode):
    rec, receipt = assemble_fixture(tmp_path, data)
    if mode == "head_buffer":
        cp = torch.load(
            tmp_path / "final_step_10000.pt", map_location="cpu", weights_only=True
        )
        cp["model_state_dict"]["head_scale"][0] *= 2
        torch.save(cp, tmp_path / "final_step_10000.pt")
    if mode == "scale_file":
        f = tmp_path / "head_scale.json"
        value = json.loads(f.read_text())
        value["scale"][0] *= 2
        f.write_text(json.dumps(value))
        for asset in (rec, receipt):
            asset["head_scale_sha256"] = sha256(f)
        cp = torch.load(
            tmp_path / "final_step_10000.pt", map_location="cpu", weights_only=True
        )
        cp["head_scale_sha256"] = sha256(f)
        torch.save(cp, tmp_path / "final_step_10000.pt")
        pre = json.loads((tmp_path / "PRE_UPDATE.json").read_text())
        pre["head_scale_sha256"] = sha256(f)
        (tmp_path / "PRE_UPDATE.json").write_text(json.dumps(pre))
        h = sha256(tmp_path / "PRE_UPDATE.json")
        rec["pre_update_sha256"] = receipt["pre_update_sha256"] = h
        cp["pre_update_sha256"] = h
        torch.save(cp, tmp_path / "final_step_10000.pt")
    if mode == "head_pre_rule":
        f = tmp_path / "PRE_UPDATE.json"
        pre = json.loads(f.read_text())
        pre["head_scale_rule"] = {}
        f.write_text(json.dumps(pre))
        h = sha256(f)
        rec["pre_update_sha256"] = receipt["pre_update_sha256"] = h
        cp = torch.load(
            tmp_path / "final_step_10000.pt", map_location="cpu", weights_only=True
        )
        cp["pre_update_sha256"] = h
        torch.save(cp, tmp_path / "final_step_10000.pt")
    if mode == "direct_native_mismatch":
        data = copy.deepcopy(data)
        data["c20s4"]["direct_actual_rates"][123] += 1e-9
    if mode in ("pre_activation", "checkpoint_activation"):
        name = "PRE_UPDATE.json" if mode == "pre_activation" else "final_step_10000.pt"
        target = tmp_path / name
        asset = (
            json.loads(target.read_text())
            if name.endswith("json")
            else torch.load(target, map_location="cpu", weights_only=True)
        )
        asset["activation_rule"] = dict(ACTIVATION_RULE, negative_slope=0.02)
        if name.endswith("json"):
            target.write_text(json.dumps(asset))
            cp = torch.load(
                tmp_path / "final_step_10000.pt", map_location="cpu", weights_only=True
            )
            cp["pre_update_sha256"] = sha256(target)
            torch.save(cp, tmp_path / "final_step_10000.pt")
            rec["pre_update_sha256"] = receipt["pre_update_sha256"] = sha256(target)
        else:
            torch.save(asset, target)
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
    candidate_tampers = {
        "candidate_rho": ("predicted_rho_u", 123.0, "gate_rho_u"),
        "candidate_strain": ("strain_relative_l2", 456.0, "gate_strain_fit"),
        "candidate_reference_rho": ("reference_rho_u", 789.0, None),
        "candidate_strain_norm": ("strain_error_norm", 999.0, None),
        "candidate_bc": ("essential_bc_max_abs_error", 1.0, "gate_essential_bc"),
    }
    if mode in candidate_tampers:
        key, value, gate = candidate_tampers[mode]
        rec["metrics"][key] = value
        if gate is not None:
            rec["metrics"][gate] = False
        rec["metrics"]["joint_pass"] = all(
            v for k, v in rec["metrics"].items() if k.startswith("gate_")
        )
    if mode == "prediction":
        uv = np.load(tmp_path / "prediction.npz")["uv"]
        uv[200, 0] += 0.001
        np.savez_compressed(tmp_path / "prediction.npz", uv=uv)
    if mode == "activation_metadata":
        rec["activation_rule"] = dict(ACTIVATION_RULE, negative_slope=0.02)
    if mode == "direct_control_identity":
        receipt["paired_e021_control_lock"] = DIRECT_LOCKS["c60s4"]
    rebind(tmp_path, rec, receipt)
    if mode is None:
        row = validate_record(tmp_path / "metrics.json", "0" * 40, data)
        assert row["displacement_mass_rms_over_abs_Us"] > 0.001
    else:
        error = (
            pytest.raises(ValueError, match="candidate metric mismatch")
            if mode in candidate_tampers
            else pytest.raises((ValueError, AssertionError))
        )
        with error:
            validate_record(tmp_path / "metrics.json", "0" * 40, data)


def test_coherent_scale_checkpoint_and_hash_forgery_still_rejected(tmp_path, data):
    from s04_e023_head_scale import scales_from_rms, array_digest

    rec, receipt = assemble_fixture(tmp_path, data)
    f = tmp_path / "head_scale.json"
    cal = json.loads(f.read_text())
    rms = np.array(cal["rms"])
    rms[0] *= 2
    scale = scales_from_rms(rms)
    cal.update(
        rms=rms.tolist(),
        scale=scale.tolist(),
        rms_digest=array_digest(rms),
        scale_digest=array_digest(scale),
    )
    f.write_text(json.dumps(cal))
    h = sha256(f)
    pre_path = tmp_path / "PRE_UPDATE.json"
    pre = json.loads(pre_path.read_text())
    pre["head_scale_sha256"] = h
    pre_path.write_text(json.dumps(pre))
    pre_sha = sha256(pre_path)
    cp_path = tmp_path / "final_step_10000.pt"
    cp = torch.load(cp_path, map_location="cpu", weights_only=True)
    cp["head_scale_sha256"] = h
    cp["pre_update_sha256"] = pre_sha
    cp["model_state_dict"]["head_scale"] = torch.tensor(scale)
    cp["model_state_dict"]["head_rms"] = torch.tensor(rms)
    torch.save(cp, cp_path)
    for asset in (rec, receipt):
        asset.update(head_scale_sha256=h, pre_update_sha256=pre_sha)
    rebind(tmp_path, rec, receipt)
    with pytest.raises(
        ValueError, match="initial head calibration/gradient recomputation mismatch"
    ):
        validate_record(tmp_path / "metrics.json", "0" * 40, data)
