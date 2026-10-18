import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'SENS_tensile'))
from s04_e024_head_cone import cone_projection, common_descent, elastic_driver, strain_adjoint
from s04_e024_weak_guard import Mechanics


def test_cone_projection_and_opposing_guards():
    v, p, info = cone_projection(np.array([-1., -2.]), np.array([[1., 0.]]))
    np.testing.assert_allclose(p, [0., 2.], atol=1e-14)
    np.testing.assert_allclose(v, [0., 1.], atol=1e-14)
    _, p, info = cone_projection(np.array([-1., 0.]), np.array([[1., 0.], [-1., 0.]]))
    np.testing.assert_allclose(p, 0, atol=1e-14)
    assert not info['resolved_nonzero']


def test_dependent_normals_and_scale_invariance():
    g = np.array([-1., -2., 3.])
    a = np.array([[1., 0., 0.], [2., 0., 0.], [0., 1., 0.]])
    v, p, _ = cone_projection(g, a)
    np.testing.assert_allclose(p, [0., 0., -3.], atol=1e-14)
    np.testing.assert_allclose(cone_projection(g, a * np.array([1e-8, 2e8, 7.])[:, None])[0], v, atol=1e-14)


def test_common_descent_strict_and_conflict():
    v, q, info = common_descent(np.eye(3))
    np.testing.assert_allclose(v, -np.ones(3) / np.sqrt(3), atol=1e-14)
    assert info['resolved_strict'] and info['largest_unit_slope'] < 0
    v, _, info = common_descent(np.array([[1., 0.], [-1., 0.], [0., 1.]]))
    assert not info['resolved_strict'] and np.count_nonzero(v) == 0


def test_finite_schema_refusal():
    with pytest.raises(ValueError): cone_projection(np.array([1., np.nan]), np.eye(2))
    with pytest.raises(ValueError): common_descent(np.array([[0., 0.]]))


def test_native_elastic_driver_adjoint_finite_difference():
    xy = np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]])
    conn = np.array([[0,1,2,3]])
    uv = np.c_[.03*xy[:,0]+.01*xy[:,1], .02*xy[:,1]]
    velocity = np.c_[.02*xy[:,0], -.01*xy[:,0]+.01*xy[:,1]]
    m = Mechanics(xy, conn, np.full(4,.3), uv)
    p, derivative = elastic_driver(m, uv, np.full((1,4),.3))
    det = np.stack([g[1] for g in m.geo], axis=1)
    analytic = np.sum(strain_adjoint(m, derivative) * velocity)
    h = 1e-5
    pp = elastic_driver(m, uv+h*velocity, np.full((1,4),.3))[0]
    pm = elastic_driver(m, uv-h*velocity, np.full((1,4),.3))[0]
    np.testing.assert_allclose(analytic, np.sum(det*(pp-pm))/(2*h), rtol=1e-9, atol=1e-12)
