"""Analytic checks of read-only reductions; no optimiser or training steps."""
import copy
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"SENS_tensile"))
from diagnose_s04_e020_features import stream_measure, gradient_summary, US
from s04_e019_frozen_residual import FrozenResidualUV, state_digest
from s04_e018_global_local import NeuralNet


def fixture():
    torch.manual_seed(19)
    lo=np.array([-.5,-.1]);hi=np.array([.1,.1])
    geometry=dict(lower=lo.tolist(),upper=hi.tolist(),center=((lo+hi)/2).tolist(),
                  scale=((hi-lo)/2+.02).tolist(),padding=.02,damage_threshold=.1)
    model=FrozenResidualUV(torch.nn.Linear(2,2).double(),NeuralNet(2,2,2,5,"TrainableReLU",1.).double(),"localized",geometry)
    xy=np.array([[-.4,0.],[-.2,.01],[0.,-.01],[.3,0.],[-.25,.3],[.05,.05]])
    base=np.zeros((len(xy),2))
    data=dict(xy=xy,mass=np.arange(1,len(xy)+1,dtype=float),damage=np.array([1.,0.,.8,0.,0.,0.]),
              equilibrated_uv=np.column_stack((xy[:,0]**2,xy[:,0]*xy[:,1]))*.01)
    return model,data,base


def test_streamed_gradients_equal_direct_full_region_gradients():
    model,data,base=fixture(); before=state_digest(model)
    result=stream_measure(model,data,base,chunk=2)
    pred=torch.tensor(base)+model.correction_physical(torch.tensor(data['xy']))
    sq=((pred-torch.tensor(data['equilibrated_uv']))**2).sum(1)/abs(US)**2
    w=torch.tensor(data['mass']/data['mass'].sum());mask=torch.tensor(data['damage']>.1)
    named=list(model.residual.named_parameters());ps=[p for _,p in named]
    gd=torch.autograd.grad((sq*w*mask).sum(),ps,retain_graph=True)
    gb=torch.autograd.grad((sq*w*(~mask)).sum(),ps)
    direct=gradient_summary(named,gd,gb)
    for actual,expected in zip(result['gradients'],direct):
        for key in ['damage_norm','background_norm','total_norm','cosine']:
            if expected[key] is None: assert actual[key] is None
            else: np.testing.assert_allclose(actual[key],expected[key],rtol=1e-10,atol=1e-14)
    assert state_digest(model)==before
    assert all(p.grad is None for p in model.parameters())


def test_chunking_leaves_losses_activations_and_spectra_unchanged():
    model,data,base=fixture()
    a=stream_measure(model,data,base,chunk=1);b=stream_measure(copy.deepcopy(model),data,base,chunk=6)
    np.testing.assert_allclose(a['full_rms'],b['full_rms'],rtol=1e-12)
    for x,y in zip(a['activations'],b['activations']):
        assert x['dead_units']==y['dead_units']
        np.testing.assert_allclose(x['mean_active_fraction'],y['mean_active_fraction'],rtol=1e-12)
    for x,y in zip(a['spectrum'],b['spectrum']):
        np.testing.assert_allclose(x['eigenvalues'],y['eigenvalues'],rtol=1e-10,atol=1e-15)


def test_zero_output_initial_hidden_gradient_is_structural_not_dead_features():
    model,data,base=fixture()
    with torch.no_grad():model.residual.output_layer.weight.zero_();model.residual.output_layer.bias.zero_()
    result=stream_measure(model,data,base,chunk=3)
    hidden=[r for r in result['gradients'] if r['group'] not in ('all','output_layer')]
    assert all(r['damage_norm']==r['background_norm']==0 for r in hidden)
    assert next(r for r in result['gradients'] if r['group']=='output_layer')['total_norm']>0
    assert any(r['dead_units']<r['width'] for r in result['activations'])
