"""E022: one last-hidden activation change, E021 direct and E019 common controls."""
import copy
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from s04_e021_screen import (CONTROL_LOCKS, MAP_LOCKS, OriginalCosineSchedule,
    admit_control, check_pair_identity, schedule_identity, check_schedule_identity,
    check_runtime_identity, update_lr, native_replay, admit_coordinate_map,
    validate_coordinate_buffers, build_candidate as build_relu_candidate)
from run_s04_e019_frozen_residual_screen import (sha256, state_digest, predict_in_chunks,
    anchor_component_geometry)
from s04_e020_delayed_decay import region_values
from network import TrainableReLU

PROTOCOL_REVISION='20261016-r1-last-hidden-leak001'
ACTIVATION_RULE=dict(branch='residual',hidden_index_zero_based=7,
    expression='leaky_relu(coeff*pre)',negative_slope=.01,first_seven='unchanged_TrainableReLU',
    layers=[dict(index=i,activation='TrainableReLU' if i<7 else 'LastHiddenLeakyReLU',negative_slope=0. if i<7 else .01,coefficient_key=f'residual.activations.{i}.coeff') for i in range(8)])
DIRECT_LOCKS=json.loads((Path(__file__).resolve().parents[1]/'docs/research/S04/S04-E022/e021_control_locks.json').read_text())


class LastHiddenLeakyReLU(nn.Module):
    def __init__(self, coeff):
        super().__init__()
        self.coeff=coeff
        self.negative_slope=.01

    def forward(self,x):
        return F.leaky_relu(self.coeff*x,negative_slope=self.negative_slope)


def validate_activation(model):
    acts=model.residual.activations
    if len(acts)!=8 or type(acts[-1]) is not LastHiddenLeakyReLU or acts[-1].negative_slope!=.01:
        raise ValueError('last-hidden activation identity mismatch')
    if any(type(a) is not TrainableReLU for a in acts[:7]):
        raise ValueError('first-seven activation drift')
    if not acts[-1].coeff.requires_grad or not torch.isfinite(acts[-1].coeff).all():
        raise ValueError('activation coefficient frozen/nonfinite')


def build_candidate(seed,arm,geometry,backbone,mapping):
    model=build_relu_candidate(seed,arm,geometry,backbone,mapping)
    model.residual.activations[7]=LastHiddenLeakyReLU(model.residual.activations[7].coeff)
    validate_activation(model)
    return model


def validate_behavior_envelope(asset,state):
    if asset.get('activation_rule')!=ACTIVATION_RULE or asset.get('paired_e021_control_lock')!=DIRECT_LOCKS[state]:
        raise ValueError('activation/direct-control envelope mismatch')


def check_direct_files(state,directory):
    for name,h in DIRECT_LOCKS[state]['files'].items():
        if sha256(Path(directory)/name)!=h:raise ValueError('E021 direct-control asset mismatch: '+name)


def admit_coordinate_control(state,directory,data,backbone,saved_base_uv):
    directory=Path(directory);lock=DIRECT_LOCKS[state];check_direct_files(state,directory)
    if data['reference_sha256']!=lock['reference_sha256']:raise ValueError('direct reference mismatch')
    if lock['runtime']!=CONTROL_LOCKS[state]['runtime']:raise ValueError('direct/common runtime mismatch')
    receipt=json.loads((directory/'RUN_RECEIPT.json').read_text());record=json.loads((directory/'metrics.json').read_text())
    if receipt['code_commit']!=lock['code_commit'] or receipt['run_id']!=lock['run_id'] or receipt['dirty'] is not False:
        raise ValueError('E021 direct source/run mismatch')
    geom=anchor_component_geometry(data['xy'],data['damage'],data['conn'],data['mass'])
    # Map is derived from the same frozen backbone, never the trained residual.
    mapping=admit_coordinate_map(state,data,saved_base_uv,geom)
    if mapping!=lock['coordinate_mapping']:raise ValueError('direct map mismatch')
    model=build_relu_candidate(7,'localized',geom,copy.deepcopy(backbone),mapping)
    cp=torch.load(directory/'final_step_10000.pt',map_location='cpu',weights_only=True)
    model.load_state_dict(cp['model_state_dict'],strict=True);validate_coordinate_buffers(model,mapping)
    if state_digest(model.backbone)!=lock['backbone_digest']:raise ValueError('direct backbone drift')
    for name in ('lower','upper','center','scale'):
        if not torch.equal(getattr(model,name),torch.tensor(geom[name],dtype=torch.float64)):raise ValueError('direct physical geometry drift')
    with np.load(directory/'prediction.npz') as f:uv=f['uv'].copy()
    evaluated=predict_in_chunks(model,torch.tensor(data['xy'],dtype=torch.float64)).cpu().numpy()
    np.testing.assert_allclose(evaluated,uv,rtol=0,atol=1e-12)
    regions=region_values(data,uv);trace=json.loads((directory/'monitoring.json').read_text())
    for key,field in [('full','displacement_mass_rms_over_abs_Us'),('damage','damage_conditional_rms_over_abs_Us'),('background','background_conditional_rms_over_abs_Us')]:
        np.testing.assert_allclose(regions[key],trace[-1][field],rtol=0,atol=1e-14)
    rates=np.load(directory/'learning_rates.npy',allow_pickle=False)
    np.testing.assert_array_equal(rates,np.load(directory/'expected_learning_rates.npy',allow_pickle=False))
    return dict(lock=lock,regions=regions,reference_rho_u_recorded=record['baseline_metrics']['reference_rho_u'],reference_rho_u_current=data['reference_rho_u'],
        portability_policy='historical byte/UV admission only; preserve E021 primaryFAIL and strict Mac nativeLR/reference-rho INADMISSIBLE')


def require_direct_native_profile(state,directory):
    check_direct_files(state,directory)
    if not np.array_equal(np.asarray(native_replay(),dtype='<f8'),np.load(Path(directory)/'learning_rates.npy',allow_pickle=False)):
        raise ValueError('producer native LR does not equal E021 direct-control profile')
