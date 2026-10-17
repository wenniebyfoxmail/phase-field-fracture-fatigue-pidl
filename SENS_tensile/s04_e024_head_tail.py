"""Fixed E023 model; one stage-mask change, no new training budget."""
import copy, hashlib, json
from pathlib import Path
import numpy as np
import torch
from s04_e023_head_scale import *
from s04_e023_head_scale import validate_behavior_envelope as validate_e023_envelope
from s04_e023_head_scale import validate_activation as validate_joint_activation
from s04_e023_head_scale import HeadScaledUV, scales_from_rms, array_digest
from s04_e022_screen import LastHiddenLeakyReLU
from network import TrainableReLU
from s04_e020_delayed_decay import region_values

PROTOCOL_REVISION = "20261017-r1-8000joint-2000headonly-comparative"
STAGE_RULE = dict(
    joint_updates=8000,
    head_only_updates=2000,
    total_updates=10000,
    transition_before_update=8001,
    head_moments_reset=False,
    hidden_weight_decay_after_transition=False,
    head_scale_fixed=True,
)
EVALUATION_RULE = dict(
    kind="paired-relative-UV-and-background-cost",
    direct_comparator="own_E023",
    historical_001="diagnostic_only_not_physical_standard_or_route_gate",
    background_acceptability="UNDEFINED",
    application="damage_crack_fatigue",
    application_tolerance="UNDEFINED_REQUIRES_COUPLED_HISTORY_VALIDATION",
    compute_budget="10000_new_updates_8000joint_2000headonly",
)
HEAD_LOCKS = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "docs/research/S04/S04-E024/e023_control_locks.json"
    ).read_text()
)


def phase_for_update(step):
    if type(step) is not int or not 1 <= step <= 10000:
        raise ValueError("actual update outside1..10000")
    return "joint" if step <= 8000 else "head_only"


def hidden_named(model):
    return [
        (n, p)
        for n, p in model.residual.named_parameters()
        if not n.startswith("output_layer.")
    ]


def set_phase(model, phase):
    if phase not in ("joint", "head_only"):
        raise ValueError("unknown stage")
    for n, p in model.residual.named_parameters():
        p.requires_grad_(phase == "joint" or n.startswith("output_layer."))
    validate_activation(model, phase)


def validate_activation(model, phase="joint"):
    if phase not in ("joint", "head_only"):
        raise ValueError("unknown stage")
    acts = model.residual.activations
    if (
        len(acts) != 8
        or type(acts[-1]) is not LastHiddenLeakyReLU
        or acts[-1].negative_slope != 0.01
    ):
        raise ValueError("last activation identity")
    if any(type(a) is not TrainableReLU for a in acts[:7]):
        raise ValueError("first seven activation identity")
    if any(not torch.isfinite(a.coeff).all() for a in acts):
        raise ValueError("nonfinite activation coefficient")
    for n, p in model.residual.named_parameters():
        want = phase == "joint" or n.startswith("output_layer.")
        if p.requires_grad != want:
            raise ValueError("stage parameter mask: " + n)
        if not want and p.grad is not None:
            raise ValueError("frozen parameter has gradient: " + n)
    if any(p.requires_grad or p.grad is not None for p in model.backbone.parameters()):
        raise ValueError("backbone trainability/gradient")


def validate_head_scale(model, calibration, phase="joint"):
    if type(model) is not HeadScaledUV or calibration.get("rule") != HEAD_SCALE_RULE:
        raise ValueError("head class/rule")
    s = np.asarray(calibration["rms"])
    d = np.asarray(calibration["scale"])
    if (
        s.shape != (284,)
        or d.shape != (284,)
        or not np.array_equal(scales_from_rms(s), d)
    ):
        raise ValueError("head schema/formula")
    if (
        array_digest(s) != calibration["rms_digest"]
        or array_digest(d) != calibration["scale_digest"]
    ):
        raise ValueError("head digest")
    for n, v in (("head_rms", s), ("head_scale", d)):
        b = getattr(model, n)
        if (
            b.requires_grad
            or b.dtype != torch.float64
            or not torch.equal(b.detach().cpu(), torch.tensor(v, dtype=torch.float64))
        ):
            raise ValueError("head buffer drift")
    validate_activation(model, phase)


def cpu_tree(x):
    if torch.is_tensor(x):
        return x.detach().cpu().clone()
    if isinstance(x, dict):
        return {k: cpu_tree(v) for k, v in x.items()}
    if isinstance(x, list):
        return [cpu_tree(v) for v in x]
    if isinstance(x, tuple):
        return tuple(cpu_tree(v) for v in x)
    return x


def tree_digest(x):
    h = hashlib.sha256()

    def add(v):
        if torch.is_tensor(v):
            a = v.detach().cpu().contiguous()
            h.update(str((str(a.dtype), tuple(a.shape))).encode())
            h.update(a.numpy().tobytes())
        elif isinstance(v, dict):
            for k in sorted(v, key=str):
                h.update(str((type(k).__name__, k)).encode())
                add(v[k])
        elif isinstance(v, (list, tuple)):
            h.update(type(v).__name__.encode())
            for z in v:
                add(z)
        else:
            h.update(json.dumps(v, sort_keys=True, allow_nan=False).encode())

    add(x)
    return h.hexdigest()


def optimizer_counts(model, optimizer, completed, deep=True):
    named = list(model.residual.named_parameters())
    if (
        type(optimizer) is not torch.optim.AdamW
        or len(optimizer.param_groups) != 1
        or [id(p) for p in optimizer.param_groups[0]["params"]]
        != [id(p) for _, p in named]
    ):
        raise ValueError("optimizer identity/order")
    for n, p in named:
        want = completed if n.startswith("output_layer.") else min(completed, 8000)
        st = optimizer.state.get(p, {})
        if want == 0:
            if st:
                raise ValueError("optimizer initialized before update1")
        elif (
            set(st) != {"step", "exp_avg", "exp_avg_sq"}
            or float(st["step"]) != want
            or (deep and any(not torch.isfinite(v).all() for v in st.values()))
        ):
            raise ValueError("optimizer counters/state: " + n)
    return dict(head_updates=completed, hidden_updates=min(completed, 8000))


def frozen_digest(model):
    return tree_digest({n: p for n, p in hidden_named(model)})


def hidden_optimizer_digest(model, optimizer):
    return tree_digest({n: optimizer.state[p] for n, p in hidden_named(model)})


def enter_head_only(model, optimizer, completed):
    if completed != 8000:
        raise ValueError("stage transition only after8000")
    validate_activation(model, "joint")
    optimizer_counts(model, optimizer, 8000)
    before = tree_digest(optimizer.state_dict())
    weights = state_digest(model)
    optimizer.zero_grad(set_to_none=True)
    set_phase(model, "head_only")
    if before != tree_digest(optimizer.state_dict()) or weights != state_digest(model):
        raise ValueError("transition changed weights/optimizer")
    return dict(
        hidden_digest=frozen_digest(model),
        hidden_optimizer_digest=hidden_optimizer_digest(model, optimizer),
        optimizer_digest=before,
        model_digest=weights,
    )


def check_tail(model, optimizer, completed, entry, deep=True):
    validate_activation(model, "head_only")
    optimizer_counts(model, optimizer, completed, deep=deep)
    if deep and (
        frozen_digest(model) != entry["hidden_digest"]
        or hidden_optimizer_digest(model, optimizer) != entry["hidden_optimizer_digest"]
    ):
        raise ValueError("hidden weights/moments/decay changed")


def check_head_files(state, directory):
    for n, h in HEAD_LOCKS[state]["files"].items():
        if sha256(Path(directory) / n) != h:
            raise ValueError("E023 control identity: " + n)


def require_head_native_profile(state, directory):
    check_head_files(state, directory)
    np.testing.assert_array_equal(
        np.asarray(native_replay()),
        np.load(Path(directory) / "learning_rates.npy", allow_pickle=False),
    )


def admit_head_control(state, directory, data, backbone, base):
    directory = Path(directory)
    check_head_files(state, directory)
    lock = HEAD_LOCKS[state]
    receipt = json.loads((directory / "RUN_RECEIPT.json").read_text())
    record = json.loads((directory / "metrics.json").read_text())
    cp = torch.load(
        directory / "final_step_10000.pt", map_location="cpu", weights_only=True
    )
    for a in (
        receipt,
        record,
        cp,
        json.loads((directory / "PRE_UPDATE.json").read_text()),
    ):
        validate_e023_envelope(a, state)
    if (
        receipt["code_commit"] != lock["code_commit"]
        or receipt["run_id"] != lock["run_id"]
        or receipt["dirty"] is not False
        or data["reference_sha256"] != lock["reference_sha256"]
    ):
        raise ValueError("E023 direct identity")
    geom = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    mapping = admit_coordinate_map(state, data, base, geom)
    if mapping != lock["coordinate_mapping"]:
        raise ValueError("E023 map")
    model, _ = build_candidate(
        7, "localized", geom, copy.deepcopy(backbone), mapping, data["xy"], data["mass"]
    )
    model.load_state_dict(cp["model_state_dict"], strict=True)
    validate_head_scale(model, json.loads((directory / "head_scale.json").read_text()))
    if state_digest(model.backbone) != lock["backbone_digest"]:
        raise ValueError("E023 backbone")
    with np.load(directory / "prediction.npz") as f:
        uv = f["uv"].copy()
    np.testing.assert_allclose(
        predict_in_chunks(model, torch.tensor(data["xy"], dtype=torch.float64)).numpy(),
        uv,
        rtol=0,
        atol=1e-12,
    )
    regions = region_values(data, uv)
    trace = json.loads((directory / "monitoring.json").read_text())
    for key, field in [
        ("full", "displacement_mass_rms_over_abs_Us"),
        ("damage", "damage_conditional_rms_over_abs_Us"),
        ("background", "background_conditional_rms_over_abs_Us"),
    ]:
        np.testing.assert_allclose(regions[key], trace[-1][field], rtol=0, atol=1e-14)
    return dict(
        lock=lock,
        regions=regions,
        recorded_elapsed_seconds=record["elapsed_seconds"],
        recorded_cost_scope="historical loop plus finalization wall time; uncontrolled shared GPU load; not pure kernel time",
        portability_policy="Historical bytes/UV only; E023 primaryFAIL and strictMac exceptions retained",
    )


def validate_behavior_envelope(asset, state):
    validate_e023_envelope(asset, state)
    if (
        asset.get("stage_rule") != STAGE_RULE
        or asset.get("evaluation_rule") != EVALUATION_RULE
        or asset.get("paired_e023_control_lock") != HEAD_LOCKS[state]
    ):
        raise ValueError("stage/evaluation/E023 envelope")


def validate_stage_artifacts(path, model, record, checkpoint, receipt):
    """Independent state/counter replay, no optimizer construction or update."""
    from datetime import datetime

    path = Path(path)
    entry_path = path / "HEAD_ONLY_STAGE_ENTRY.json"
    snap_path = path / "step_8000.pt"
    entry = json.loads(entry_path.read_text())
    snap = torch.load(snap_path, map_location="cpu", weights_only=True)
    for asset in (record, checkpoint, receipt):
        if (
            asset.get("stage_entry_sha256") != sha256(entry_path)
            or asset.get("stage_snapshot_sha256") != sha256(snap_path)
            or asset.get("head_updates") != 10000
            or asset.get("hidden_updates") != 8000
            or asset.get("final_training_phase") != "head_only"
        ):
            raise ValueError("final stage envelope")
    expected = dict(
        protocol_revision=PROTOCOL_REVISION,
        evaluation_rule=EVALUATION_RULE,
        code_commit=receipt["code_commit"],
        stage_rule=STAGE_RULE,
        state=record["state"],
        run_id=receipt["run_id"],
        completed_updates=8000,
        head_updates=8000,
        hidden_updates=8000,
        next_update=8001,
        pre_update_sha256=record["pre_update_sha256"],
        head_scale_sha256=record["head_scale_sha256"],
        head_gradient_preflight_sha256=record["head_gradient_preflight_sha256"],
    )
    for obj in (entry, snap):
        if any(obj.get(k) != v for k, v in expected.items()):
            raise ValueError("stage snapshot/receipt identity")
    if (
        entry.get("code_commit") != receipt["code_commit"]
        or entry.get("phase") != "head_only"
        or entry.get("optimizer_unchanged_across_freeze") is not True
        or entry.get("stage_snapshot_sha256") != sha256(snap_path)
    ):
        raise ValueError("stage receipt")
    stamps = [
        datetime.fromisoformat(x.replace("Z", "+00:00"))
        for x in (record["started_utc"], entry["created_utc"], record["finished_utc"])
    ]
    if any(t.tzinfo is None for t in stamps) or not stamps[0] <= stamps[1] <= stamps[2]:
        raise ValueError("stage chronology")
    profile = np.asarray(native_replay())
    if (
        entry["lr_used_update8000"] != profile[7999]
        or entry["lr_next_update8001"] != profile[8000]
    ):
        raise ValueError("stage actual LR")
    names = [n for n, _ in model.residual.named_parameters()]
    if (
        snap.get("optimizer_parameter_names") != names
        or checkpoint.get("optimizer_parameter_names") != names
    ):
        raise ValueError("optimizer names/order")
    os0 = snap["optimizer_state_dict"]
    os1 = checkpoint["optimizer_state_dict"]
    if len(os0["param_groups"]) != 1 or len(os1["param_groups"]) != 1:
        raise ValueError("optimizer group count")
    expected_hyper = dict(
        betas=(0.9, 0.999), eps=1e-8, weight_decay=1e-8, amsgrad=False, maximize=False
    )
    for groups, lr in (
        (os0["param_groups"], float(profile[8000])),
        (os1["param_groups"], 1e-5),
    ):
        g = groups[0]
        if (
            g["params"] != list(range(len(names)))
            or g["lr"] != lr
            or any(g.get(k) != v for k, v in expected_hyper.items())
        ):
            raise ValueError("optimizer hyperparameters/index/LR")
    h0 = {}
    h1 = {}
    for i, n in enumerate(names):
        a, b = os0["state"][i], os1["state"][i]
        head = n.startswith("output_layer.")
        if (
            set(a) != {"step", "exp_avg", "exp_avg_sq"}
            or set(b) != set(a)
            or float(a["step"]) != 8000
            or float(b["step"]) != (10000 if head else 8000)
        ):
            raise ValueError("final optimizer counters/schema")
        param = dict(model.residual.named_parameters())[n]
        for st in (a, b):
            if st["step"].numel() != 1 or any(
                not torch.isfinite(v).all() for v in st.values()
            ):
                raise ValueError("optimizer state nonfinite")
            if any(
                st[k].shape != param.shape or st[k].dtype != torch.float64
                for k in ("exp_avg", "exp_avg_sq")
            ):
                raise ValueError("optimizer moment shape/dtype")
        if not head:
            if tree_digest(a) != tree_digest(b):
                raise ValueError("hidden optimizer/decay drift")
            h0[n] = a
            h1[n] = b
    if (
        tree_digest(os0) != entry["optimizer_digest"]
        or tree_digest(h0) != entry["hidden_optimizer_digest"]
    ):
        raise ValueError("stage optimizer digest")
    if (
        tree_digest(
            {
                n: snap["model_state_dict"]["residual." + n]
                for n in names
                if not n.startswith("output_layer.")
            }
        )
        != entry["hidden_digest"]
    ):
        raise ValueError("stage hidden digest")
    stage_model = copy.deepcopy(model)
    stage_model.load_state_dict(snap["model_state_dict"], strict=True)
    set_phase(stage_model, "head_only")
    if state_digest(stage_model) != entry["model_digest"]:
        raise ValueError("stage model digest")
    for n, v in snap["model_state_dict"].items():
        if not n.startswith("residual.output_layer.") and not torch.equal(
            v, checkpoint["model_state_dict"][n]
        ):
            raise ValueError("frozen stage8000-final10000 tensor drift")
    trace = json.loads((path / "monitoring.json").read_text())
    for row in trace:
        k = row["step"]
        want = "joint" if k <= 8000 else "head_only"
        if (
            row.get("training_phase") != want
            or row.get("head_updates") != k
            or row.get("hidden_updates") != min(k, 8000)
        ):
            raise ValueError("passive stage counters")
    if (
        receipt.get("final_trainable_parameter_names")
        != ["output_layer.weight", "output_layer.bias"]
        or record.get("final_trainable_parameter_names")
        != receipt["final_trainable_parameter_names"]
        or checkpoint.get("final_trainable_parameter_names")
        != receipt["final_trainable_parameter_names"]
    ):
        raise ValueError("final trainable mask")
    return stage_model, entry


def sampler_audit(data):
    from run_s04_e019_frozen_residual_screen import (
        make_strata,
        draw_stratified,
        SAMPLE_SEED_OFFSET,
    )

    strata = make_strata(data["damage"], data["mass"])
    rng = np.random.Generator(np.random.PCG64(7 + SAMPLE_SEED_OFFSET))
    h = hashlib.sha256()
    prefix = None
    for k in range(1, 10001):
        a, b = draw_stratified(rng, strata, "0.7")
        h.update(np.asarray(np.concatenate((a, b)), dtype="<i8").tobytes())
        if k == 8000:
            prefix = h.hexdigest()
    return dict(prefix8000=prefix, full10000=h.hexdigest())
