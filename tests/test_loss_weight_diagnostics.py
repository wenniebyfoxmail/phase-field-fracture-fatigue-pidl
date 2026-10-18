import sys
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from loss_weight_diagnostics import gradient_probe,sign_stats,cosine


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
