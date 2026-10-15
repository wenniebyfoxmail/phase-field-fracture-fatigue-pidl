"""Pure mapping/model-identity checks; never takes an optimisation step."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"SENS_tensile"))
from s04_e021_residual_coordinates import coordinate_rule, CoordinateResidualUV
from s04_e019_frozen_residual import build_model, state_digest


def example():
    lo=np.array([-.5,-.1]);hi=np.array([.1,.1])
    g=dict(lower=lo.tolist(),upper=hi.tolist(),center=((lo+hi)/2).tolist(),
           scale=((hi-lo)/2+.02).tolist(),padding=.02,damage_threshold=.1)
    xy=np.array([[-.301,-.0001],[-.299,.0001],[.4,0.]])
    d=dict(xy=xy,mass=np.ones(3),damage=np.ones(3),equilibrated_uv=np.array([[1.,0.],[1.,0.],[99.,0.]]))
    return d,np.zeros((3,2)),g


def test_rule_excludes_exterior_error_and_caps_coordinate_zoom():
    d,b,g=example();m=coordinate_rule(d,b,g)
    np.testing.assert_allclose(m['local_center'],[-.3,0.],atol=1e-15)
    np.testing.assert_allclose(m['local_scale'],np.array(g['scale'])/4)
    assert m['core_damage_error_energy_fraction']<.001


def test_mapping_keeps_initial_zero_output_parameter_identity_and_physical_support():
    d,b,g=example();m=coordinate_rule(d,b,g)
    backbone=torch.nn.Linear(2,2).double();old=build_model(7,'localized',g,backbone)
    new=CoordinateResidualUV(copy.deepcopy(old.backbone),copy.deepcopy(old.residual),g,m)
    assert state_digest(new.residual)==state_digest(old.residual)
    assert sum(p.numel() for p in new.parameters())==sum(p.numel() for p in old.parameters())
    xy=torch.tensor([[-.3,0.],[.4,0.],[-.2,.5],[-.2,-.5]],dtype=torch.float64)
    torch.testing.assert_close(old(2*xy),new(2*xy),rtol=0,atol=0)
    with torch.no_grad():new.residual.output_layer.bias.fill_(1.)
    assert torch.count_nonzero(new.correction_physical(xy)[1:])==0
    for k in ('lower','upper','center','scale'):assert torch.equal(getattr(old,k),getattr(new,k))


def test_nonfinite_or_zero_residual_is_rejected():
    d,b,g=example();d['equilibrated_uv']=b.copy()
    with pytest.raises(ValueError,match='positive'):coordinate_rule(d,b,g)
    d['equilibrated_uv'][0,0]=np.nan
    with pytest.raises(ValueError,match='nonfinite'):coordinate_rule(d,b,g)
