import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/censor_projection_diagnostic'))
import numpy as np
import pytest
from hard_kkt import assess

def test_legal_reactions_and_collapsed():
    out,v,_=assess([9,-9,10,0],[.2,1,1,.5],[.2,.1,1,.2],np.arange(4),np.ones(4)/4,1.)
    assert out['status']=='PASS' and np.array_equal(v,np.zeros(4))
    assert out['hard_mass_rms_free']==0 and out['box_mass_rms_free']>0

def test_wrong_sign_and_interior():
    out,v,_=assess([-2,3,4],[.2,1,.5],[.2,.1,.2],np.arange(3))
    np.testing.assert_equal(v,[-2,3,4]); assert out['status']=='FAIL'

def test_infeasible_not_hidden_by_reaction():
    out,_,_=assess([9],[.1],[.2],np.arange(1))
    assert out['status']=='INFEASIBLE'

def test_near_collapsed_not_silently_fixed():
    out,_,_=assess([1],[1.-2e-13],[1.-5e-13],np.arange(1))
    assert out['status']=='AMBIGUOUS_NEAR_BOTH_BOUNDS'

def test_bad_fixed_and_nonfinite():
    out,_,_=assess([0,0],[.2,.9],[.2,.9],np.array([0]))
    assert out['status']=='INFEASIBLE'
    with pytest.raises(ValueError): assess([float('nan')],[.2],[.2],np.array([0]))

def test_mass_not_subset_normalized():
    out,_,_=assess([.001,0],[.5,1],[.1,1],np.array([0]),np.array([.2,.8]),1.)
    assert out['hard_mass_rms_free']==pytest.approx(np.sqrt(.2)*.005)

def test_exact_endpoint_in_narrow_interval():
    out,_,_=assess([1,-1],[1.-5e-13,1.],[1.-5e-13,1.-5e-13],np.arange(2))
    assert out['status']=='PASS' and out['counts']['lower']==1 and out['counts']['upper']==1

def test_tiny_violation_never_passes():
    out,_,_=assess([0],[0],[-5e-13],np.array([0]),np.ones(1),1.)
    assert out['status']=='FEASIBILITY_TOLERANCE_ONLY'
    assert out['hard_mass_rms_free'] is None
