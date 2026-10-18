import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e024_three_head import enrich_basis,admit_finite,uv_safe_fraction,GUARDS


def test_three_dimensional_reconstruction():
    old=np.eye(4)[:2].reshape(2,2,2);v=np.array([.3,.4,np.sqrt(.75),0.]).reshape(2,2)
    b,c,r,info=enrich_basis(old,v)
    np.testing.assert_allclose(c,[.3,.4,np.sqrt(.75)],atol=1e-14)
    np.testing.assert_allclose(r,v,atol=1e-14)
    np.testing.assert_array_equal(b[:2],old)
    assert info['orthogonal_remainder_norm']>0


def test_no_new_axis_refused():
    old=np.eye(4)[:2].reshape(2,2,2)
    with pytest.raises(ValueError):enrich_basis(old,old[0])


def test_actual_physical_guard_strictness():
    origin=dict.fromkeys(GUARDS,1.)
    assert admit_finite(dict.fromkeys(GUARDS,.9),origin,.02)[0]
    changed=origin.copy();changed['driver_inside_background']=1.+1e-15
    ok,why=admit_finite(changed,origin,.001)
    assert not ok and why==['driver_inside_background']
    assert not admit_finite(origin,origin,.021)[0]


def test_nonfinite_values_are_not_backtracking_candidates():
    origin=dict.fromkeys(GUARDS,1.);bad=origin.copy();bad['weak_squared']=np.nan
    with pytest.raises(ValueError):admit_finite(bad,origin,.01)


def test_exact_uv_curvature_half_crossing():
    error=np.array([[1.,0.],[2.,0.]])
    velocity=np.array([[-10.,0.],[-1.,0.]])
    w=dict(full=np.ones(2)/2,damage=np.array([1.,0.]),background=np.array([0.,1.]))
    t,terms=uv_safe_fraction(error,velocity,w)
    assert t==pytest.approx(.1)  # damage zero crossing .2, half is .1
    for weight in w.values():
        assert np.sum(weight[:,None]*(error+t*velocity)**2)<np.sum(weight[:,None]*error**2)
    with pytest.raises(ValueError):uv_safe_fraction(error,-velocity,w)
