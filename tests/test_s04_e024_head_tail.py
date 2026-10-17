"""Stage logic tests with manually declared optimizer states, zero parameter updates."""
import copy, sys
from pathlib import Path
import pytest
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "SENS_tensile"))
from test_s04_e023_head_scale import pair
from s04_e024_head_tail import *
from aggregate_s04_e024_head_tail_screen import summarize


def staged():
    _, m, cal, xy, mass = pair()
    opt = torch.optim.AdamW(m.residual.parameters(), lr=0.001, weight_decay=1e-8)
    with torch.no_grad():
        m.residual.output_layer.weight.fill_(0.0001)
        m.residual.output_layer.bias.fill_(0.0002)
    # Synthetic metadata fixture, never optimizer.step or a training loop.
    for p in m.residual.parameters():
        opt.state[p] = dict(
            step=torch.tensor(8000.0),
            exp_avg=torch.ones_like(p) * 0.01,
            exp_avg_sq=torch.ones_like(p) * 0.02,
        )
    return m, opt, cal, xy


def test_transition_retains_function_rng_moments_and_counts():
    m, o, c, xy = staged()
    q = torch.tensor(xy)
    before = m.correction_physical(q).detach()
    rng = torch.random.get_rng_state().clone()
    d = tree_digest(o.state_dict())
    weights = state_digest(m)
    e = enter_head_only(m, o, 8000)
    validate_head_scale(m, c, "head_only")
    check_tail(m, o, 8000, e)
    assert (
        state_digest(m) == weights
        and tree_digest(o.state_dict()) == d
        and torch.equal(rng, torch.random.get_rng_state())
    )
    torch.testing.assert_close(before, m.correction_physical(q), rtol=0, atol=0)
    assert [n for n, p in m.residual.named_parameters() if p.requires_grad] == [
        "output_layer.weight",
        "output_layer.bias",
    ]
    g = torch.autograd.grad(
        m.correction_physical(q).sum(), tuple(m.residual.output_layer.parameters())
    )
    assert len(g) == 2 and all(p.grad is None for p in m.parameters())


@pytest.mark.parametrize("bad", [0, 8001, 7999, 10001, True])
def test_wrong_transition_rejected(bad):
    m, o, _, _ = staged()
    with pytest.raises(ValueError):
        enter_head_only(m, o, bad)


def test_phase_boundaries_and_no_10001():
    assert phase_for_update(1) == phase_for_update(8000) == "joint"
    assert phase_for_update(8001) == phase_for_update(10000) == "head_only"
    for k in (0, 10001, True):
        with pytest.raises(ValueError):
            phase_for_update(k)


@pytest.mark.parametrize(
    "bad", ["weight", "moment", "count", "grad", "mask", "D", "coeff"]
)
def test_frozen_corruption_rejected(bad):
    m, o, c, _ = staged()
    e = enter_head_only(m, o, 8000)
    n, p = hidden_named(m)[0]
    with torch.no_grad():
        if bad == "weight":
            p[0, 0] += 1
        if bad == "moment":
            o.state[p]["exp_avg"][0, 0] += 1
        if bad == "count":
            o.state[p]["step"].fill_(8001)
        if bad == "grad":
            p.grad = torch.ones_like(p)
        if bad == "mask":
            p.requires_grad_(True)
        if bad == "D":
            m.head_scale[0] *= 2
        if bad == "coeff":
            m.residual.activations[0].coeff.requires_grad_(True)
    with pytest.raises(ValueError):
        validate_head_scale(m, c, "head_only")
        check_tail(m, o, 8000, e)


def test_head_counter_10000_hidden_8000_and_head_change_allowed():
    m, o, c, _ = staged()
    e = enter_head_only(m, o, 8000)
    with torch.no_grad():
        for p in m.residual.output_layer.parameters():
            p.add_(0.001)
            o.state[p]["step"].fill_(10000)
    check_tail(m, o, 10000, e)
    validate_head_scale(m, c, "head_only")
    assert optimizer_counts(m, o, 10000) == dict(
        head_updates=10000, hidden_updates=8000
    )


def test_001_is_only_diagnostic_and_background_acceptance_not_invented():
    rows = []
    for state in HEAD_LOCKS:
        r = dict(
            state=state,
            displacement_mass_rms_over_abs_Us=0.002,
            final_damage_conditional_rms=0.01,
            final_background_conditional_rms=0.0002,
            background_inside_support_conditional_rms=0.0004,
        )
        for pre in ("direct_E023_", "direct_E022_", "direct_E021_", "control_"):
            for reg, v in [
                ("full", 0.003),
                ("damage", 0.02),
                ("background", 0.00019),
                ("inside_background", 0.00039),
            ]:
                r[pre + reg] = v
        r["control_background_inside_support_conditional_rms"] = 0.00039
        rows.append(r)
    s = summarize(rows)
    assert s["verdict"] == "PAIRED_COMPARATIVE_EVALUATION_COMPLETE"
    assert not any(s["legacy_full_001_diagnostic"].values())
    assert s["route_acceptance"] is None and s["background_cost_acceptability"] is None
    assert len(s["paired_comparisons"]) == 48
    assert all(
        x["change_percent"] < 0
        for x in s["paired_comparisons"]
        if x["region"] == "full"
    )
    assert all(
        x["change_percent"] > 0
        for x in s["paired_comparisons"]
        if x["region"] == "background"
    )
    assert summarize(rows + [rows[0]])["verdict"] == "INADMISSIBLE"
    assert summarize(rows[:2])["verdict"] == "INCONCLUSIVE"


def test_wrong_head_counter_after_freeze_is_rejected():
    m, o, c, _ = staged()
    e = enter_head_only(m, o, 8000)
    for p in m.residual.output_layer.parameters():
        o.state[p]["step"].fill_(10000)
    o.state[m.residual.output_layer.bias]["step"].fill_(9999)
    with pytest.raises(ValueError):
        check_tail(m, o, 10000, e)
