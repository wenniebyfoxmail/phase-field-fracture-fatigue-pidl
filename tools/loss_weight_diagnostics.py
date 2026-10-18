"""Read-only full-parameter gradient diagnostics; no optimizer updates."""
import itertools
import math
import torch


def flatten_grad(value, params):
    gg = torch.autograd.grad(value, params, retain_graph=True, allow_unused=True)
    result = torch.cat([(torch.zeros_like(p) if g is None else g).reshape(-1)
                        for p,g in zip(params,gg)])
    if not bool(torch.isfinite(result).all()):
        raise RuntimeError('nonfinite diagnostic parameter gradient')
    return result.detach()


def norm(g):
    return float(g.double().norm())


def cosine(a,b):
    na,nb=norm(a),norm(b)
    return float(torch.dot(a.double(),b.double())/(na*nb)) if na and nb else None


def sign_stats(g1,g25):
    assert g1.shape==g25.shape and g1.numel()>0
    tau=1e-12*max(1.,float(g1.abs().max()),float(g25.abs().max()))
    n=g1.numel();s1=g1.sign();s25=g25.sign()
    flips=(s1*s25<0)
    return dict(parameters=n,opposite_sign_count=int(flips.sum()),opposite_sign_fraction=float(flips.sum())/n,
        any_sign_difference_count=int((s1!=s25).sum()),one_sided_zero_count=int(((s1==0)^(s25==0)).sum()),
        both_zero_count=int(((s1==0)&(s25==0)).sum()),nearzero_threshold=tau,
        nearzero1_fraction=float((g1.abs()<=tau).sum())/n,
        nearzero25_fraction=float((g25.abs()<=tau).sum())/n,
        cosine=cosine(g1,g25),difference_Linf=float((g1-g25).abs().max()),
        bitwise_equal=bool(torch.equal(g1,g25)))


def gradient_probe(energies,reg,params):
    eel,ed,eh=energies
    raw={key:flatten_grad(e,params) for key,e in zip(('Eel','Ed','Eh','R'),(*energies,reg))}
    direct={};rows=[]
    for beta in (1.,25.):
        total=eel+ed+beta*eh
        if not bool(torch.isfinite(total)) or float(total.detach())<=0:
            raise RuntimeError('invalid probe log domain')
        coeff=1/(math.log(10)*total.detach())
        terms={'Eel':raw['Eel']*coeff,'Ed':raw['Ed']*coeff,
               'Eh':raw['Eh']*(beta*coeff),'R':raw['R']*1e-5}
        expected=sum(terms.values())
        direct[beta]=flatten_grad(torch.log10(total)+1e-5*reg,params)
        discrepancy=float((expected-direct[beta]).abs().max())
        if not torch.allclose(expected,direct[beta],atol=1e-6,rtol=1e-4):
            raise RuntimeError('fullNN gradient decomposition mismatch')
        rows.append(dict(beta=beta,energy=float(total.detach()),total_gradient_L2=norm(direct[beta]),
            raw_gradient_L2={k:norm(v) for k,v in raw.items()},
            weighted_log_gradient_L2={k:norm(v) for k,v in terms.items()},
            weighted_log_component_cosine={f'{a}:{b}':cosine(terms[a],terms[b])
                for a,b in itertools.combinations(terms,2)},
            chain_error_Linf=discrepancy))
    result=dict(space='all requires_grad network parameters in named order; no mapping buffers',
        energies=[float(q.detach()) for q in energies],rows=rows,
        same_snapshot_beta_signs=sign_stats(direct[1.],direct[25.]),
        zero_Eh_parameter_gradient=bool(torch.count_nonzero(raw['Eh'])==0))
    return result,direct


def rprop_state_summary(opt):
    steps=[s['step_size'].detach().reshape(-1) for s in opt.state.values() if 'step_size' in s]
    prev=[s['prev'].detach().reshape(-1) for s in opt.state.values() if 'prev' in s]
    if not steps:return dict(state_entries=len(opt.state),fresh=True)
    v=torch.cat(steps);g=torch.cat(prev)
    return dict(state_entries=len(opt.state),fresh=False,step_min=float(v.min()),
                step_max=float(v.max()),step_mean=float(v.double().mean()),
                stored_prev_zero_fraction=float((g==0).sum())/g.numel())
