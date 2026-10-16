"""Nontraining activation/identity/LR/scoring tests, no parameter optimizer step."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from torch import nn
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e022_screen import (LastHiddenLeakyReLU,build_candidate,build_relu_candidate,validate_activation,ACTIVATION_RULE,DIRECT_LOCKS,
 validate_behavior_envelope,native_replay,update_lr,check_schedule_identity,schedule_identity,OriginalCosineSchedule,MAP_LOCKS)
from s04_e021_screen import MetadataOnlyOptimizer
from s04_e019_frozen_residual import state_digest,PARAMETER_COUNT,RESIDUAL_PARAMETER_COUNT
from aggregate_s04_e022_last_leak_screen import summarize


def pair():
    torch.set_num_threads(2)
    geometry=MAP_LOCKS['c20s4']['physical_geometry'];mapping=MAP_LOCKS['c20s4']['mapping']
    base=nn.Linear(2,3).double()
    old=build_relu_candidate(7,'localized',geometry,copy.deepcopy(base),mapping)
    new=build_candidate(7,'localized',geometry,copy.deepcopy(base),mapping)
    return old,new


def test_only_last_behavior_changes_no_rng_draw_or_parameter_difference():
    torch.manual_seed(117);before=torch.random.get_rng_state().clone()
    old,new=pair()
    # Backbone creation advances RNG equally outside candidate builders.
    rng=torch.random.get_rng_state().clone()
    _=build_candidate(7,'localized',MAP_LOCKS['c20s4']['physical_geometry'],copy.deepcopy(new.backbone),MAP_LOCKS['c20s4']['mapping'])
    assert torch.equal(rng,torch.random.get_rng_state())
    assert state_digest(old)==state_digest(new)
    assert set(old.state_dict())==set(new.state_dict())
    assert sum(p.numel() for p in new.residual.parameters())==RESIDUAL_PARAMETER_COUNT
    assert all(not p.requires_grad for p in new.backbone.parameters())
    for i in range(7):assert type(old.residual.activations[i]) is type(new.residual.activations[i])
    assert type(new.residual.activations[7]) is LastHiddenLeakyReLU
    xy=torch.tensor([[-.2,0.],[-.1,.01],[.4,.1]],dtype=torch.float64)
    torch.testing.assert_close(old.correction_physical(xy),new.correction_physical(xy),rtol=0,atol=0)
    assert torch.count_nonzero(new.correction_physical(xy))==0


@pytest.mark.parametrize('coefficient',[1.,-.5])
def test_fixed_leak_formula_and_negative_derivative(coefficient):
    c=nn.Parameter(torch.tensor(coefficient,dtype=torch.float64));a=LastHiddenLeakyReLU(c)
    x=torch.tensor([-2.,1.],dtype=torch.float64,requires_grad=True)
    y=a(x);expected=torch.where(c*x>=0,c*x,.01*c*x)
    torch.testing.assert_close(y,expected,rtol=0,atol=0)
    gx,gc=torch.autograd.grad(y.sum(),(x,c))
    torch.testing.assert_close(gx,torch.where(c*x>=0,c,.01*c),rtol=0,atol=0)
    assert torch.isfinite(gc) and c.grad is None


@pytest.mark.parametrize('mutation',['slope','first_layer','last_relu'])
def test_validator_rejects_behavior_changes(mutation):
    old,new=pair()
    if mutation=='slope':new.residual.activations[7].negative_slope=.02
    elif mutation=='first_layer':new.residual.activations[0]=LastHiddenLeakyReLU(new.residual.activations[0].coeff)
    else:new.residual.activations[7]=old.residual.activations[7]
    with pytest.raises(ValueError):validate_activation(new)


def test_behavior_envelope_required_and_state_paired():
    asset=dict(activation_rule=ACTIVATION_RULE,paired_e021_control_lock=DIRECT_LOCKS['c20s4'])
    validate_behavior_envelope(asset,'c20s4')
    with pytest.raises(ValueError):validate_behavior_envelope({},'c20s4')
    with pytest.raises(ValueError):validate_behavior_envelope(asset,'c60s4')


def test_native_lr_no_parameters_and_10001_rejected():
    opt=MetadataOnlyOptimizer();sched=OriginalCosineSchedule(opt)
    import warnings
    with warnings.catch_warnings(record=True):
        for k in range(1,10001):sched.before_update(k);sched.step()
    np.testing.assert_array_equal(sched.used,native_replay())
    assert sched.next_lr is None and sched.get_last_lr()==[1e-5]
    assert update_lr(10000)>1e-5
    with pytest.raises(ValueError):sched.before_update(10001)
    with pytest.raises(RuntimeError):opt.step()


def row(state,full):
    return dict(state=state,displacement_mass_rms_over_abs_Us=full,final_damage_conditional_rms=.002,final_background_conditional_rms=.0001,base_damage=.02,base_background=.0002,control_damage=.003,control_background=.0002,direct_E021_damage=.003,direct_E021_background=.0002)


def test_primary_only_and_no_partial_vacuous_pass():
    rows=[row(s,.0008) for s in DIRECT_LOCKS]
    assert summarize(rows)['verdict']=='LAST_HIDDEN_LEAK_THREE_STATE_UV_SCREEN_PASS'
    rows[-1]['displacement_mass_rms_over_abs_Us']=.0011
    assert summarize(rows)['verdict'].endswith('FAIL')
    assert summarize(rows[:2])['verdict']=='INCONCLUSIVE'
    assert summarize(rows+[rows[0]])['verdict']=='INADMISSIBLE'
    assert summarize([])['clean_damage_progress_background_preserved_vs_E021'] is None


def test_formal_native_profile_is_not_silently_replaced_by_mac():
    from s04_e022_screen import require_direct_native_profile
    root=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/producer_execution_v2/raw/runs')
    directory=root/DIRECT_LOCKS['c20s4']['run_id']
    if not directory.exists():pytest.skip('optional pinned realcontrol absent')
    formal=np.load(directory/'learning_rates.npy',allow_pickle=False)
    if np.array_equal(formal,np.asarray(native_replay())):require_direct_native_profile('c20s4',directory)
    else:
        with pytest.raises(ValueError,match='producer native LR'):require_direct_native_profile('c20s4',directory)


def test_training_step_order_and_safety_path():
    import ast
    path=Path(__file__).resolve().parents[1]/'SENS_tensile/run_s04_e022_last_leak_screen.py'
    text=path.read_text();tree=ast.parse(text)
    steps=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='optimizer' and n.func.attr=='step']
    assert len(steps)==1
    assert text.index('require_direct_native_profile(args.state') < text.index('optimizer = torch.optim.AdamW')
    assert text.index('scheduler.before_update(step)') < text.index('loss.backward()') < text.index('optimizer.step()') < text.index('scheduler.step()')
    assert 'for step in range(1, STEPS + 1)' in text
