import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools/s04_e011_analysis'))
from audit_fem_final_residuals import projected_gradient


def test_feasible_descent_signs_and_fixed_bounds():
    d=np.array([0.,0.,.5,1.,1.,1.])
    grad=np.array([2.,-3.,4.,5.,-6.,7.])
    lower=np.array([0.,0.,0.,0.,0.,1.])
    np.testing.assert_array_equal(projected_gradient(d,grad,lower),[0.,-3.,4.,5.,0.,0.])


def test_monotone_lower_bound_removes_reaction_but_keeps_violation():
    d=np.array([.4,.4,.5]); lower=np.array([.4,.4,.4])
    np.testing.assert_array_equal(projected_gradient(d,np.array([2.,-3.,4.]),lower),[0.,-3.,4.])
    with pytest.raises(ValueError): projected_gradient(d,np.ones(3),np.ones(3)*2)
