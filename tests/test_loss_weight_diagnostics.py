import sys
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from loss_weight_diagnostics import gradient_probe,sign_stats,cosine,GradientDecompositionError


def test_full_parameter_chain_and_inactive_penalty():
    p=torch.tensor([.1,.2],dtype=torch.float64,requires_grad=True)
    energies=((p+1).square().sum(),p.square().sum(),torch.relu(-p).square().sum())
    info,g=gradient_probe(energies,p.square().sum(),[p])
    assert info['zero_Eh_parameter_gradient']
    assert info['same_snapshot_beta_signs']['bitwise_equal']
    assert torch.equal(g[1.],g[25.])
    assert all(row['chain_error_Linf']<1e-12 for row in info['rows'])


def test_active_penalty_can_change_sign_without_updates():
    p=torch.tensor([.1,-.1],dtype=torch.float64,requires_grad=True)
    energies=((p+1).square().sum(),.01*p.square().sum(),torch.relu(-p).square().sum())
    info,g=gradient_probe(energies,p.square().sum(),[p])
    assert not info['zero_Eh_parameter_gradient']
    assert info['same_snapshot_beta_signs']['opposite_sign_count']==1
    assert all(row['chain_error_Linf']<1e-12 for row in info['rows'])


def test_zero_sign_and_nearzero_diagnostics_do_not_mutate_gradients():
    a=torch.tensor([0.,1.,-1.,1e-14]);b=torch.tensor([1.,-1.,-1.,-1e-14])
    aa=a.clone();bb=b.clone();s=sign_stats(a,b)
    assert s['one_sided_zero_count']==1 and s['opposite_sign_count']==2
    assert s['nearzero_threshold']==1e-12
    assert torch.equal(a,aa) and torch.equal(b,bb)
    assert cosine(torch.zeros(2),torch.ones(2)) is None


def test_failed_decomposition_preserves_original_guard_and_diagnostics():
    import loss_weight_diagnostics as module
    from unittest.mock import patch
    import pytest
    original=module.flatten_grad;calls=0
    def corrupt_direct(value,params):
        nonlocal calls
        calls+=1;result=original(value,params)
        if calls==5:
            result=result.clone();result[0]+=1
        return result
    p=torch.tensor([.1,.2],dtype=torch.float64,requires_grad=True)
    energies=((p+1).square().sum(),p.square().sum(),torch.relu(-p).square().sum())
    with patch.object(module,'flatten_grad',side_effect=corrupt_direct):
        with pytest.raises(GradientDecompositionError) as caught:
            gradient_probe(energies,p.square().sum(),[p])
    error=caught.value
    assert error.diagnostics['guard_relaxed'] is False
    assert error.diagnostics['failing_components']==1
    assert error.diagnostics['largest_difference_flat_index']==0
    assert error.diagnostics['difference_Linf']>.99
    assert set(error.vectors)=={'Eel','Ed','Eh','R','expected','direct'}


def test_incorrect_manual_chain_seed_still_fails_original_tolerance():
    import loss_weight_diagnostics as module
    from unittest.mock import patch
    import pytest
    original=module.flatten_vjp
    def wrong_seed(outputs,params,seeds):
        seeds=list(seeds);seeds[2]=seeds[2]*.5
        return original(outputs,params,tuple(seeds))
    p=torch.tensor([.1,-.1],dtype=torch.float64,requires_grad=True)
    energies=((p+1).square().sum(),.01*p.square().sum(),torch.relu(-p).square().sum())
    with patch.object(module,'flatten_vjp',side_effect=wrong_seed):
        with pytest.raises(GradientDecompositionError):gradient_probe(energies,p.square().sum(),[p])


def test_joint_manual_vjp_is_independent_of_complete_loss_construction():
    from loss_weight_diagnostics import flatten_vjp
    p=torch.tensor([.1,-.2],dtype=torch.float64,requires_grad=True)
    a=(p*p).sum();b=(3*p).sum()
    got=flatten_vjp((a,b),[p],(a.new_tensor(2.),b.new_tensor(-.5)))
    assert torch.allclose(got,4*p.detach()-1.5,atol=1e-14,rtol=1e-14)
