"""Native-Q4 AMOR equilibrium and AT1 penalty physics, independent of S09 means.

Q4 utility copied unchanged from ad749c8 (renamed for isolated S09 use).
Equilibrium matches GRIPHFiTH b680bb0 mod_equilibrium_amor.
Phase coefficients match mod_pf_at1_penalty_fatigue; psi/f are frozen in a
phase subproblem. No reconstruction from element averages is allowed.
"""
import torch
from s09_q4_quadrature import q4_shape_data, q4_interpolate, q4_gradient


def amor_fields(u, d, conn, shape, dshape, young=1., nu=.3, eta=0.):
    ux = q4_gradient(u[:, 0], conn, dshape)
    uy = q4_gradient(u[:, 1], conn, dshape)
    ex, ey, gam = ux[..., 0], uy[..., 1], ux[..., 1]+uy[..., 0]
    tr = ex+ey
    mu, bulk = young/(2*(1+nu)), young/(3*(1-2*nu))
    dev = ex.square()+ey.square()-tr.square()/3+gam.square()/2
    psi = bulk/2*tr.clamp_min(0).square()+mu*dev
    neg = bulk/2*tr.clamp_max(0).square()
    dg = q4_interpolate(d, conn, shape)
    g = (1-dg).square()+eta
    sx = g*(bulk*tr.clamp_min(0)+2*mu*(ex-tr/3))+bulk*tr.clamp_max(0)
    sy = g*(bulk*tr.clamp_min(0)+2*mu*(ey-tr/3))+bulk*tr.clamp_max(0)
    tau = g*mu*gam
    return {'psi':psi, 'g':g, 'energy':g*psi+neg,
            'strain':torch.stack((ex,ey,gam),-1), 'stress':torch.stack((sx,sy,tau),-1)}


def equilibrium(u, d, conn, shape, dshape, det, young=1., nu=.3, eta=0.):
    fields=amor_fields(u,d,conn,shape,dshape,young,nu,eta)
    s=fields['stress']; dx,dy=dshape[:,:,0,:],dshape[:,:,1,:]
    fx=((dx*s[...,0,None]+dy*s[...,2,None])*det[...,None]).sum(1)
    fy=((dy*s[...,1,None]+dx*s[...,2,None])*det[...,None]).sum(1)
    local=torch.stack((fx,fy),-1)
    force=torch.zeros_like(u).index_add(0,conn.reshape(-1),local.reshape(-1,2))
    return force,fields


def trial_fatigue(d_gp, psi, old_alpha, old_q, alpha_t=.5, p=2., eta=0.):
    # All trial evaluations start from immutable accepted old state.
    q=((1-d_gp).square()+eta)*psi
    alpha=old_alpha+torch.relu(q-old_q)
    f=torch.minimum(torch.ones_like(alpha),(2*alpha_t/(alpha+alpha_t)).pow(p))
    return alpha,q,f


def phase_penalty(d, old_d, psi, fatigue, conn, shape, dshape, det,
                  gc=.01, ell=.01, penalty_irrev=0., penalty_recov=0.):
    """Assembled phase residual for prescribed/frozen GP psi,f.

    Caller supplies nodal old_d from the correct accepted previous substep.
    No autograd through a substituted trial f in the phase partial derivative.
    Residual-loss derivatives through this explicit residual remain available.
    """
    dg=q4_interpolate(d,conn,shape); old=q4_interpolate(old_d,conn,shape)
    grad=q4_gradient(d,conn,dshape)
    local_term=2*psi*(dg-1)+(3/8)*gc/ell*fatigue
    local_term=local_term+penalty_irrev*torch.minimum(dg-old,torch.zeros_like(dg))
    local_term=local_term+penalty_recov*torch.minimum(dg,torch.zeros_like(dg))
    local=torch.einsum('eg,gn,eg->en',local_term,shape,det)
    local=local+(3/4)*gc*ell*torch.einsum('eg,egi,egin,eg->en',fatigue,grad,dshape,det)
    return torch.zeros_like(d).index_add(0,conn.reshape(-1),local.reshape(-1))


def boundary(points):
    y=points[:,1]; bottom=torch.isclose(y,y.min(),atol=1e-10,rtol=0)
    top=torch.isclose(y,y.max(),atol=1e-10,rtol=0)
    return ~(bottom|top)[:,None].expand(-1,2)


class DisplacementPINN(torch.nn.Module):
    """One-state physics diagnostic, NOT a trained function-to-function map."""
    def __init__(self):
        super().__init__()
        self.net=torch.nn.Sequential(torch.nn.Linear(2,64),torch.nn.Tanh(),
          torch.nn.Linear(64,64),torch.nn.Tanh(),torch.nn.Linear(64,64),
          torch.nn.Tanh(),torch.nn.Linear(64,2))
        torch.nn.init.zeros_(self.net[-1].weight);torch.nn.init.zeros_(self.net[-1].bias)
    def forward(self,xy,load):
        t=(xy[:,1]-xy[:,1].min())/(xy[:,1].max()-xy[:,1].min())
        base=torch.stack((torch.zeros_like(t),load*t),-1)
        return base+load*(t*(1-t))[:,None]*self.net(xy)
