import copy
import hashlib
import io
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from mechanical_residual_risk import (
    add_mechanical_residual_risk,
    interior_free_node_mask,
    mechanical_mean_excess_from_fields,
    nodal_lumped_dual_area,
    weighted_mean_excess,
    weighted_quantile_detached,
)
from fit import fit, fit_with_early_stopping


class DummyMaterial:
    mat_lmbda = 0.5769230769230769
    mat_mu = 0.3846153846153846
    w1 = 1.0
    l0 = 0.01


class DummyPFF:
    se_split = "volumetric"

    def Edegrade(self, damage):
        return (1.0 - damage) ** 2, -2.0 * (1.0 - damage)

    def damageFun(self, damage):
        return damage, torch.ones_like(damage), 8.0 / 3.0

    def irrPenalty(self):
        return 1.0


class TinyField(torch.nn.Module):
    """Small actual-fit integration fixture, not a production training model."""

    def __init__(self, dtype):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(2, 6),
            torch.nn.Tanh(),
            torch.nn.Linear(6, 3),
        ).to(dtype=dtype)
        self.lmbda = torch.tensor(0.12, dtype=dtype)

    def fieldCalculation(self, inp):
        raw = self.net(inp)
        return raw[:, 0], raw[:, 1], torch.sigmoid(raw[:, 2])


def structured_triangles(n=4):
    axis = torch.linspace(-0.5, 0.5, n, dtype=torch.float64)
    yy, xx = torch.meshgrid(axis, axis, indexing="ij")
    coords = torch.stack([xx.reshape(-1), yy.reshape(-1)], dim=1)
    cells = []
    for row in range(n - 1):
        for col in range(n - 1):
            a = row * n + col
            b = a + 1
            c = a + n
            d = c + 1
            cells.extend([[a, b, d], [a, d, c]])
    conn = torch.tensor(cells, dtype=torch.long)
    areas = torch.full((len(cells),), 0.5 / ((n - 1) ** 2), dtype=torch.float64)
    return coords, conn, areas


def state_bytes(model, optimizer):
    buffer = io.BytesIO()
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict()}, buffer)
    return buffer.getvalue()


def actual_fit_once(optimizer_kind, initial_state, *, risk_config, dtype=torch.float32,
                    epochs=1):
    inp64, conn, areas64 = structured_triangles()
    inp = inp64.to(dtype=dtype)
    areas = areas64.to(dtype=dtype)
    field = TinyField(dtype)
    field.load_state_dict(copy.deepcopy(initial_state))
    training_set = [(inp, torch.zeros(len(inp), dtype=dtype))]
    hist_alpha = torch.zeros(len(inp), dtype=dtype)

    if optimizer_kind == "lbfgs":
        optimizer = torch.optim.LBFGS(
            field.parameters(), lr=0.05, max_iter=1, history_size=2,
            line_search_fn=None,
        )
        losses = fit(
            field, training_set, conn, areas, hist_alpha, DummyMaterial(),
            DummyPFF(), 0.0, epochs, optimizer,
            mechanical_risk_dict=risk_config,
        )
    elif optimizer_kind == "rprop":
        optimizer = torch.optim.Rprop(field.parameters(), lr=1e-3)
        losses = fit_with_early_stopping(
            field, training_set, conn, areas, hist_alpha, DummyMaterial(),
            DummyPFF(), 0.0, epochs, optimizer, 0.0,
            mechanical_risk_dict=risk_config,
        )
    else:
        raise AssertionError(f"unknown optimizer kind: {optimizer_kind}")
    return losses, field, optimizer


def enabled_risk_config(dtype=torch.float32):
    inp64, conn, areas64 = structured_triangles()
    inp = inp64.to(dtype=dtype)
    areas = areas64.to(dtype=dtype)
    bounds = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=dtype)
    return {
        "enable": True,
        "lambda": 1e-4,
        "alpha": 0.5,
        "node_mask": interior_free_node_mask(inp, bounds),
        "dual_area": nodal_lumped_dual_area(conn, areas, len(inp)),
        "scale": 0.12,
    }


def test_weighted_quantile_and_mean_excess_hand_calculated():
    values = torch.tensor([1.0, 2.0, 10.0], dtype=torch.float64, requires_grad=True)
    weights = torch.tensor([0.8, 0.1, 0.1], dtype=torch.float64)
    threshold = weighted_quantile_detached(values, weights, 0.85)
    utility, threshold2 = weighted_mean_excess(values, weights, 0.85)
    assert threshold.item() == pytest.approx(2.0)
    assert threshold2.item() == pytest.approx(2.0)
    assert utility.item() == pytest.approx(0.1 * 8.0 / 0.15)
    utility.backward()
    assert values.grad.tolist() == pytest.approx([0.0, 0.0, 0.1 / 0.15])


def test_weighted_utility_permutation_and_common_area_scale_invariant():
    values = torch.tensor([0.2, 1.0, 3.0, 4.0], dtype=torch.float64)
    weights = torch.tensor([0.1, 0.2, 0.3, 0.4], dtype=torch.float64)
    base, q0 = weighted_mean_excess(values, weights, 0.5)
    perm = torch.tensor([2, 0, 3, 1])
    shuffled, q1 = weighted_mean_excess(values[perm], weights[perm], 0.5)
    rescaled, q2 = weighted_mean_excess(values, 17.0 * weights, 0.5)
    assert shuffled.item() == pytest.approx(base.item())
    assert rescaled.item() == pytest.approx(base.item())
    assert q1.item() == pytest.approx(q0.item())
    assert q2.item() == pytest.approx(q0.item())


def test_weighted_quantile_tie_is_deterministic():
    values = torch.tensor([1.0, 2.0, 2.0, 5.0], dtype=torch.float64)
    weights = torch.tensor([0.2, 0.2, 0.4, 0.2], dtype=torch.float64)
    q = weighted_quantile_detached(values, weights, 0.5)
    assert q.item() == 2.0


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1])
def test_invalid_alpha_fails_closed(alpha):
    with pytest.raises(ValueError, match="strictly between"):
        weighted_mean_excess(torch.ones(2), torch.ones(2), alpha)


def test_invalid_weights_and_nonfinite_values_fail_closed():
    with pytest.raises(ValueError, match="strictly positive"):
        weighted_mean_excess(torch.ones(2), torch.tensor([1.0, 0.0]), 0.5)
    with pytest.raises(ValueError, match="finite"):
        weighted_mean_excess(torch.tensor([1.0, float("nan")]), torch.ones(2), 0.5)


def test_triangle_dual_area_and_interior_mask():
    conn = torch.tensor([[0, 1, 2], [0, 2, 3]])
    areas = torch.tensor([0.5, 0.5], dtype=torch.float64)
    dual = nodal_lumped_dual_area(conn, areas, 4)
    assert dual.tolist() == pytest.approx([1.0 / 3.0, 1.0 / 6.0, 1.0 / 3.0, 1.0 / 6.0])

    coords = torch.tensor([
        [-0.5, -0.5], [0.0, -0.5], [0.5, -0.5],
        [-0.5, 0.0], [0.0, 0.0], [0.5, 0.0],
        [-0.5, 0.5], [0.0, 0.5], [0.5, 0.5],
    ])
    bounds = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    mask = interior_free_node_mask(coords, bounds)
    assert torch.where(mask)[0].tolist() == [4]

    with pytest.raises(ValueError, match="strictly positive"):
        nodal_lumped_dual_area(conn, torch.tensor([0.5, 0.0]), 4)


@pytest.mark.parametrize("config", [None, {"enable": False}])
def test_disabled_helper_returns_exact_same_tensor(config):
    base = torch.tensor(3.0, requires_grad=True)
    result, diagnostics = add_mechanical_residual_risk(base, config=config)
    assert result is base
    assert diagnostics is None


def test_disabled_path_preserves_loss_gradient_update_state_and_checkpoint_bytes():
    torch.manual_seed(7)
    model_a = torch.nn.Linear(2, 1, bias=True).double()
    model_b = copy.deepcopy(model_a)
    optimizer_a = torch.optim.SGD(model_a.parameters(), lr=0.1, momentum=0.9)
    optimizer_b = torch.optim.SGD(model_b.parameters(), lr=0.1, momentum=0.9)
    x = torch.tensor([[1.0, -2.0], [0.5, 0.25]], dtype=torch.float64)

    optimizer_a.zero_grad()
    loss_a = model_a(x).square().sum()
    loss_a.backward()
    grads_a = [p.grad.detach().clone() for p in model_a.parameters()]
    optimizer_a.step()

    optimizer_b.zero_grad()
    original = model_b(x).square().sum()
    loss_b, diagnostics = add_mechanical_residual_risk(original, config={"enable": False})
    assert loss_b is original
    assert diagnostics is None
    loss_b.backward()
    grads_b = [p.grad.detach().clone() for p in model_b.parameters()]
    optimizer_b.step()

    assert loss_a.detach().item() == loss_b.detach().item()
    assert all(torch.equal(a, b) for a, b in zip(grads_a, grads_b))
    assert all(torch.equal(a, b) for a, b in zip(model_a.parameters(), model_b.parameters()))
    bytes_a = state_bytes(model_a, optimizer_a)
    bytes_b = state_bytes(model_b, optimizer_b)
    assert bytes_a == bytes_b
    assert hashlib.sha256(bytes_a).hexdigest() == hashlib.sha256(bytes_b).hexdigest()


@pytest.mark.parametrize("optimizer_kind", ["lbfgs", "rprop"])
def test_actual_fit_risk_off_is_bitwise_identical(optimizer_kind):
    torch.manual_seed(101)
    initial = TinyField(torch.float32).state_dict()
    losses_a, field_a, optimizer_a = actual_fit_once(
        optimizer_kind, initial, risk_config=None,
    )
    losses_b, field_b, optimizer_b = actual_fit_once(
        optimizer_kind, initial, risk_config={"enable": False},
    )
    assert losses_a == losses_b
    assert all(torch.equal(a, b) for a, b in zip(field_a.parameters(), field_b.parameters()))
    assert all(
        (a.grad is None and b.grad is None)
        or torch.equal(a.grad, b.grad)
        for a, b in zip(field_a.parameters(), field_b.parameters())
    )
    assert state_bytes(field_a, optimizer_a) == state_bytes(field_b, optimizer_b)


@pytest.mark.parametrize("optimizer_kind,epochs", [("lbfgs", 1), ("rprop", 2)])
def test_actual_fit_risk_on_float32_is_finite(optimizer_kind, epochs):
    torch.manual_seed(103)
    initial = TinyField(torch.float32).state_dict()
    losses, field, _ = actual_fit_once(
        optimizer_kind, initial, risk_config=enabled_risk_config(), epochs=epochs,
    )
    assert len(losses) == epochs
    assert all(torch.isfinite(torch.tensor(loss)) for loss in losses)
    assert all(torch.all(torch.isfinite(param)) for param in field.parameters())
    assert all(
        param.grad is None or torch.all(torch.isfinite(param.grad))
        for param in field.parameters()
    )


def test_enabled_mechanical_risk_has_finite_second_order_gradient_and_detached_damage_path():
    torch.manual_seed(11)
    inp, conn, areas = structured_triangles()
    bounds = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float64)
    mask = interior_free_node_mask(inp, bounds)
    dual = nodal_lumped_dual_area(conn, areas, len(inp))
    raw = torch.nn.Parameter(0.03 * torch.randn(len(inp), 3, dtype=torch.float64))
    u, v = raw[:, 0], raw[:, 1]
    damage = torch.sigmoid(raw[:, 2])

    utility, diagnostics = mechanical_mean_excess_from_fields(
        inp, u, v, damage, DummyMaterial(), DummyPFF(), areas, conn,
        node_mask=mask, dual_area=dual, scale=0.12, alpha=0.5,
    )
    first = torch.autograd.grad(utility, raw, create_graph=True)[0]
    second = torch.autograd.grad(first[:, :2].square().sum(), raw)[0]
    assert torch.isfinite(utility)
    assert torch.all(torch.isfinite(first))
    assert torch.all(torch.isfinite(second))
    assert torch.equal(first[:, 2], torch.zeros_like(first[:, 2]))
    assert diagnostics["population_nodes"] == 4
    assert diagnostics["threshold"].requires_grad is False


def test_enabled_wrapper_adds_only_configured_coefficient():
    torch.manual_seed(13)
    inp, conn, areas = structured_triangles()
    bounds = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]], dtype=torch.float64)
    mask = interior_free_node_mask(inp, bounds)
    dual = nodal_lumped_dual_area(conn, areas, len(inp))
    raw = torch.nn.Parameter(0.02 * torch.randn(len(inp), 3, dtype=torch.float64))
    base = raw.square().mean()
    combined, diagnostics = add_mechanical_residual_risk(
        base_loss=base,
        config={"enable": True, "lambda": 0.25, "alpha": 0.5,
                "node_mask": mask, "dual_area": dual, "scale": 0.12},
        inp=inp, u=raw[:, 0], v=raw[:, 1], damage=torch.sigmoid(raw[:, 2]),
        matprop=DummyMaterial(), pffmodel=DummyPFF(), element_area=areas,
        connectivity=conn,
    )
    assert combined.item() == pytest.approx(
        base.item() + 0.25 * diagnostics["risk_mean_excess"].item()
    )


def test_enabled_wrapper_rejects_empty_mask_and_nonpositive_scale():
    inp, conn, areas = structured_triangles()
    dual = nodal_lumped_dual_area(conn, areas, len(inp))
    raw = torch.nn.Parameter(0.02 * torch.randn(len(inp), 3, dtype=torch.float64))
    common = dict(
        inp=inp, u=raw[:, 0], v=raw[:, 1], damage=torch.sigmoid(raw[:, 2]),
        matprop=DummyMaterial(), pffmodel=DummyPFF(), element_area=areas,
        connectivity=conn,
    )
    with pytest.raises(ValueError, match="non-empty"):
        add_mechanical_residual_risk(
            raw.square().mean(),
            config={"enable": True, "node_mask": torch.zeros(len(inp), dtype=torch.bool),
                    "dual_area": dual, "scale": 0.12},
            **common,
        )
    with pytest.raises(ValueError, match="scale must be positive"):
        add_mechanical_residual_risk(
            raw.square().mean(),
            config={"enable": True, "node_mask": torch.ones(len(inp), dtype=torch.bool),
                    "dual_area": dual, "scale": 0.0},
            **common,
        )


@pytest.mark.parametrize("bad_scale", [float("nan"), float("inf"), -float("inf")])
def test_enabled_wrapper_rejects_nonfinite_scale(bad_scale):
    inp, conn, areas = structured_triangles()
    dual = nodal_lumped_dual_area(conn, areas, len(inp))
    raw = torch.nn.Parameter(0.02 * torch.randn(len(inp), 3, dtype=torch.float64))
    with pytest.raises(ValueError, match="scale must be positive"):
        add_mechanical_residual_risk(
            raw.square().mean(),
            config={"enable": True, "node_mask": torch.ones(len(inp), dtype=torch.bool),
                    "dual_area": dual, "scale": bad_scale},
            inp=inp, u=raw[:, 0], v=raw[:, 1], damage=torch.sigmoid(raw[:, 2]),
            matprop=DummyMaterial(), pffmodel=DummyPFF(), element_area=areas,
            connectivity=conn,
        )


@pytest.mark.parametrize("bad_lambda", [float("nan"), float("inf"), -1e-3])
def test_enabled_wrapper_rejects_invalid_lambda(bad_lambda):
    inp, conn, areas = structured_triangles()
    config = enabled_risk_config(dtype=torch.float64)
    config["lambda"] = bad_lambda
    raw = torch.nn.Parameter(0.02 * torch.randn(len(inp), 3, dtype=torch.float64))
    with pytest.raises(ValueError, match="lambda must be non-negative"):
        add_mechanical_residual_risk(
            raw.square().mean(), config=config,
            inp=inp, u=raw[:, 0], v=raw[:, 1], damage=torch.sigmoid(raw[:, 2]),
            matprop=DummyMaterial(), pffmodel=DummyPFF(), element_area=areas,
            connectivity=conn,
        )


def test_enabled_wrapper_rejects_element_mask_until_active_domain_measure_exists():
    inp, conn, areas = structured_triangles()
    config = enabled_risk_config(dtype=torch.float64)
    raw = torch.nn.Parameter(0.02 * torch.randn(len(inp), 3, dtype=torch.float64))
    with pytest.raises(ValueError, match="incompatible with element_mask"):
        add_mechanical_residual_risk(
            raw.square().mean(), config=config,
            inp=inp, u=raw[:, 0], v=raw[:, 1], damage=torch.sigmoid(raw[:, 2]),
            matprop=DummyMaterial(), pffmodel=DummyPFF(), element_area=areas,
            connectivity=conn, element_mask=torch.ones(len(areas)),
        )


def test_model_train_risk_setup_does_not_read_late_void_mask_local():
    source = (ROOT / "source" / "model_train.py").read_text(encoding="utf-8")
    setup_start = source.index("# Mechanical-only residual risk is opt-in")
    setup_end = source.index("# ★ δ-1 element-level IS", setup_start)
    setup = source[setup_start:setup_end]
    assert "_void_energy_mask" not in setup
    assert "void_notch_mask" in setup
