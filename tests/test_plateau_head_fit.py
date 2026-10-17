"""Small numerical fixtures; no model, training loop or producer access."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest


PATH = Path(__file__).resolve().parents[1]/"tools/s04_e011_analysis/plateau_head_fit.py"
SPEC = importlib.util.spec_from_file_location("plateau_head_fit", PATH)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_affine_uv_exact_physical_fit_including_boundary():
    y = np.linspace(-.5, .5, 23)
    x = np.sin(np.arange(len(y)))
    h = np.column_stack((x, y))
    head = np.array([[.3, -.7, .8], [-.6, .4, .2]])
    U, theta = .12, np.pi/2
    bubble = (.5+y)*(.5-y)
    lift = U*(y+.5)[:, None]*np.array([[np.cos(theta), np.sin(theta)]])
    target = U*bubble[:, None]*(np.column_stack((h, np.ones(len(y)))) @ head.T)+lift
    r = m.fit_uv_head(h, np.column_stack((x,y)), U, theta,
                      target[:,0], target[:,1], np.linspace(.2,2,len(y)))
    np.testing.assert_allclose(r["head"], head, atol=2e-14)
    assert r["physical_error"]["max_abs"] < 1e-15
    assert r["fit"]["rank"] == 3
    assert r["fit"]["normal_residual_relative"] < 1e-13


def test_rank_deficiency_is_reported_not_capacity_failure():
    y = np.linspace(-.5,.5,13)
    h = np.column_stack((y, 2*y, np.ones(len(y))))
    r = m.fit_uv_head(h, np.column_stack((y,y)), .1, np.pi/2,
                      .1*(y+.5)*(.5-y)*(3*y+.2), .1*(y+.5), np.ones(len(y)))
    assert r["fit"]["rank"] == 2
    assert not r["fit"]["full_column_rank"]
    assert r["physical_error"]["max_abs"] < 1e-15


def test_smooth_inverse_affine_raw_witness_and_anchor_unchanged():
    h = np.linspace(-1,1,19)[:,None]
    raw = 2*h[:,0]+.3
    anchor = dict(r0=np.zeros(19), anchor_logit=np.linspace(-.2,.3,19),
                  anchor_scale=np.linspace(.8,1.2,19))
    before = {k:v.copy() for k,v in anchor.items()}
    logits = anchor["anchor_logit"]+anchor["anchor_scale"]*raw
    target = 1/(1+np.exp(-logits))
    r = m.fit_smooth_damage_head(h,target,np.ones(19),anchor)
    np.testing.assert_allclose(r["head"], [2,.3], atol=2e-14)
    assert r["physical_error"]["max_abs"] < 1e-14
    for k in anchor:
        assert np.array_equal(before[k],anchor[k])


def test_endpoint_clipping_is_visible_and_invalid_damage_rejected():
    h = np.arange(4)[:,None]
    anchor = dict(r0=np.zeros(4),anchor_logit=np.zeros(4),anchor_scale=np.ones(4))
    r = m.fit_smooth_damage_head(h,[0,.2,.8,1],np.ones(4),anchor)
    assert r["clipped_nodes"] == 2
    assert r["target_clip_max_abs"] == pytest.approx(1e-7)
    assert np.all((r["d"]>=0)&(r["d"]<=1))
    with pytest.raises(ValueError,match="in "):
        m.fit_smooth_damage_head(h,[-.01,.2,.8,1],np.ones(4),anchor)


def test_zero_load_has_zero_rank_and_cannot_repair_boundary():
    y = np.linspace(-.5,.5,7)
    r = m.fit_uv_head(y[:,None],np.column_stack((y,y)),0.,0.,
                      np.ones(7),np.zeros(7),np.ones(7))
    assert r["fit"]["rank"] == 0
    assert r["target_boundary_mismatch_max"] == 1.
    assert r["physical_error"]["max_abs"] == 1.
