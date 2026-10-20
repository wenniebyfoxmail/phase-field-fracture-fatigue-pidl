"""Pure callback algebra for a proposed profiled hidden update.

No data/model loading, network adapter, CLI, producer execution or IO. All field
vectors are FREE displacement coordinates; parameter coordinates may be an
explicitly invertible scaling of hidden parameters. Exact profile derivatives
refer to a fixed-rank local head chart, not differentiated adaptive SVD code.
"""
from dataclasses import dataclass
from typing import Callable
import numpy as np

Action=Callable[[np.ndarray],np.ndarray]


def vec(x,n):
    x=np.asarray(x,dtype=np.float64)
    if x.shape!=(n,) or not np.isfinite(x).all():raise ValueError('shape_or_nonfinite')
    return x


def scalar(x):
    x=float(x)
    if not np.isfinite(x):raise ValueError('nonfinite_derived_scalar')
    return x


def inner(x,y):return scalar(np.einsum('i,i->',x,y,optimize=False))


def norm(x):return scalar(np.sqrt(inner(x,x)))


def budget(steps,tolerance):
    if isinstance(steps,bool) or not isinstance(steps,(int,np.integer)) or steps<1 or not np.isfinite(tolerance) or tolerance<=0:
        raise ValueError('invalid_iteration_budget_or_tolerance')


def strict_spd_solver(h):
    """Artificial/reference backend; future producer reuses its head Cholesky.

    No pseudoinverse, ridge, numerical rank selection or eigenvalue floor.
    A positive but ill-conditioned factor is not certified by this function;
    the adapter must pass the prescribed adjoint/finite-profile checks.
    """
    h=np.asarray(h,dtype=np.float64)
    if h.ndim!=2 or h.shape[0]!=h.shape[1] or not np.isfinite(h).all():raise ValueError('invalid_head_matrix')
    if not np.allclose(h,h.T,rtol=1e-13,atol=0):raise ValueError('head_not_symmetric')
    factor=np.linalg.cholesky(h)
    def solve(rhs):
        rhs=vec(rhs,len(h));x=np.linalg.solve(factor.T,np.linalg.solve(factor,rhs))
        if not np.isfinite(x).all():raise ValueError('nonfinite_head_solve')
        error=norm(h@x-rhs)
        if error>1e-6*max(norm(rhs),np.finfo(float).tiny):raise ValueError('head_solve_residual')
        return x
    return solve


@dataclass
class Profiled:
    parameters:int
    fields:int
    heads:int
    J:Action
    JT:Action
    B:Action
    BT:Action
    K:Action
    KT:Action
    C:Action
    CT:Action
    solve_head:Action

    def j(self,v):return vec(self.J(vec(v,self.parameters)),self.fields)
    def jt(self,w):return vec(self.JT(vec(w,self.fields)),self.parameters)
    def b(self,z):return vec(self.B(vec(z,self.heads)),self.fields)
    def bt(self,w):return vec(self.BT(vec(w,self.fields)),self.heads)
    def k(self,w):return vec(self.K(vec(w,self.fields)),self.fields)
    def kt(self,w):return vec(self.KT(vec(w,self.fields)),self.fields)
    def c(self,v):return vec(self.C(vec(v,self.parameters)),self.heads)
    def ct(self,z):return vec(self.CT(vec(z,self.heads)),self.parameters)
    def solve(self,z):return vec(self.solve_head(vec(z,self.heads)),self.heads)

    def u(self,v):return self.bt(self.k(self.j(v)))+self.c(v)
    def ut(self,z):return self.jt(self.kt(self.b(z)))+self.ct(z)
    def q(self,v):return self.j(v)-self.b(self.solve(self.u(v)))
    def qt(self,w):return self.jt(w)-self.ut(self.solve(self.bt(w)))
    def z(self,v):
        jv=self.j(v)
        return jv-self.b(self.solve(self.bt(self.k(jv))))
    def zt(self,w):return self.jt(vec(w,self.fields)-self.kt(self.b(self.solve(self.bt(w)))))
    def metric(self,v,damping):
        if not np.isfinite(damping) or damping<=0:raise ValueError('positive_hidden_damping_required')
        v=vec(v,self.parameters)
        return self.zt(self.k(self.z(v)))+damping*v
    def gradients(self,force):
        force=vec(force,self.fields)
        return self.qt(force),self.qt(self.kt(force))


def conjugate_gradient(action,rhs,max_steps=64,relative_tolerance=1e-4):
    """Finite SPD reference CG; an unfinished solve is not a usable metric."""
    rhs=np.asarray(rhs,dtype=np.float64);n=rhs.size;rhs=vec(rhs,n)
    budget(max_steps,relative_tolerance)
    x=np.zeros(n);r=rhs.copy();p=r.copy();rr=inner(r,r);base=np.sqrt(rr)
    if base==0:return x,dict(status='zero_rhs',steps=0,relative_residual=0.)
    for step in range(1,max_steps+1):
        ap=vec(action(p),n);curvature=inner(p,ap)
        if curvature<=0:raise ValueError('nonpositive_metric_curvature_no_repair')
        alpha=rr/curvature;x+=alpha*p;r-=alpha*ap;new=inner(r,r)
        if np.sqrt(new)<=relative_tolerance*base:
            actual=rhs-vec(action(x),n);rel=float(norm(actual)/base)
            if rel<=relative_tolerance:return x,dict(status='converged',steps=step,relative_residual=rel)
            r=actual;new=inner(r,r);p=r.copy();rr=new;continue
        p=r+(new/rr)*p;rr=new
    return x,dict(status='budget_unresolved',steps=max_steps,relative_residual=float(norm(rhs-vec(action(x),n))/base))


def common_descent(g_energy,g_residual,solve_metric):
    """One fixed metric-normalized bisector, no weight/step/damping scan.

    Each solve returns (vector, status). Exact solves guarantee both slopes
    negative unless the gradients oppose; actual slopes are always checked.
    """
    ge=np.asarray(g_energy,dtype=np.float64);gr=vec(g_residual,ge.size);ge=vec(ge,ge.size)
    if norm(ge)==0 or norm(gr)==0:return None,dict(status='zero_gradient_no_claim')
    u,eu=solve_metric(ge);v,er=solve_metric(gr)
    if eu['status'] not in ['converged','exact'] or er['status'] not in ['converged','exact']:
        return None,dict(status='metric_solve_unresolved',energy_solve=eu,residual_solve=er)
    u=vec(u,ge.size);v=vec(v,ge.size);aa=inner(ge,u);bb=inner(gr,v)
    if aa<=0 or bb<=0:raise ValueError('nonpositive_dual_metric_norm')
    a,b=np.sqrt(aa),np.sqrt(bb);p=-(u/a+v/b)
    se,sr=inner(ge,p),inner(gr,p)
    info=dict(status='common_descent' if se<0 and sr<0 else 'no_verified_common_descent',energy_slope=se,residual_half_squared_slope=sr,
              metric_cosine_symmetric=(inner(ge,v)+inner(gr,u))/(2*a*b),energy_solve=eu,residual_solve=er)
    return (p if info['status']=='common_descent' else None),info


def limit_step(p,profile,physical_mass,physical_radius,parameter_radius):
    """Fixed joint physical/parameter TR; neither radius is an error margin."""
    p=vec(p,profile.parameters);mass=vec(physical_mass,profile.fields)
    if np.any(mass<=0) or not np.isfinite([physical_radius,parameter_radius]).all() or min(physical_radius,parameter_radius)<=0:raise ValueError('positive_TR_scales_required')
    qp=profile.q(p);physical=norm(vec(np.sqrt(mass)*qp,profile.fields));param=float(norm(p))
    scale=min(1.,physical_radius/physical if physical else 1.,parameter_radius/param if param else 1.)
    # Stay just inside a radius after scalar rounding; this is not guard slack.
    if scale<1:scale=float(np.nextafter(scale,0.))
    return p*scale,dict(scale=scale,predicted_physical_norm=physical*scale,parameter_norm=param*scale)


def tangent_bounds(A,AT,b,p,radius):
    """Numerical primal/dual bounds for min_{||p||<=radius} .5||A p-b||².

    Bounds concern only this declared linear chart and ball. The roundoff
    allowance is a numerical annotation, not physical acceptance slack.
    """
    p=np.asarray(p,dtype=np.float64);b=np.asarray(b,dtype=np.float64);p=vec(p,p.size);b=vec(b,b.size)
    if not np.isfinite(radius) or radius<=0 or norm(p)>radius:raise ValueError('infeasible_witness_ball')
    r=vec(A(p),b.size)-vec(b,b.size);g=vec(AT(r),p.size)
    upper=.5*inner(r,r);lower=scalar(-inner(b,r)-.5*inner(r,r)-scalar(radius*norm(g)))
    allowance=scalar(64*np.finfo(float).eps*scalar(max(abs(upper)+abs(lower)+radius*norm(g),np.finfo(float).tiny)))
    if upper-lower < -allowance:raise ValueError('invalid_primal_dual_pair')
    return dict(primal_upper=upper,dual_lower=lower,raw_gap=upper-lower,numerical_lower=lower-allowance,numerical_upper=upper+allowance,
        normal_residual=float(norm(g)),roundoff_annotation=float(allowance),bounded_parameter_radius=radius,
        scope='Local linear chart and explicit parameter ball only; not architecture capacity or NN realization.')


def bounded_tangent_witness(A,AT,b,parameters,radius,max_steps=96,relative_gap=1e-3):
    """Bounded Frank-Wolfe witness, fixed budget, exact quadratic line step."""
    budget(max_steps,relative_gap)
    b=np.asarray(b,dtype=np.float64);p=np.zeros(parameters)
    for step in range(max_steps+1):
        bounds=tangent_bounds(A,AT,b,p,radius)
        if bounds['raw_gap']<=relative_gap*max(.5*inner(b,b),np.finfo(float).tiny):return p,dict(status='bounded_numeric_gap',steps=step,**bounds)
        if step==max_steps:break
        r=vec(A(p),b.size)-b;g=vec(AT(r),parameters);gn=norm(g)
        if gn==0:break
        s=-radius*g/gn;d=s-p;ad=vec(A(d),b.size);den=inner(ad,ad)
        if den==0:break
        alpha=float(np.clip(-inner(r,ad)/den,0,1));p=(1-alpha)*p+alpha*s
        if norm(p)>radius:p*=np.nextafter(radius/norm(p),0.)
    return p,dict(status='bounded_gap_unresolved',steps=step,**tangent_bounds(A,AT,b,p,radius))


def finite_trial_decision(old,new):
    """Candidate acceptance only: numerical E nonincrease and strict Ru decrease.

    This is not strict energy gain or a scientific success label. No IO."""
    required=['E','Ru','head_gradient_inf','realization_maxabs','finite','fixed_state','actual_nn']
    if any(k not in new for k in required):raise ValueError('missing_finite_trial_observable')
    if not np.isfinite([old['E'],old['Ru']]).all() or old['Ru']<0:raise ValueError('invalid_old_endpoint')
    nums=[new[k] for k in ['E','Ru','head_gradient_inf','realization_maxabs']]
    if not np.isfinite(nums).all() or min(new['Ru'],new['head_gradient_inf'],new['realization_maxabs'])<0 or any(new[k] is not True for k in ['finite','fixed_state','actual_nn']):return 'rejected_contract'
    if new['head_gradient_inf']>1e-10 or new['realization_maxabs']>1e-10:return 'rejected_head_or_realization'
    energy_tol=128*np.finfo(float).eps*max(abs(old['E']),abs(new['E']),1e-30)
    return 'accepted' if new['E']<=old['E']+energy_tol and new['Ru']<old['Ru'] else 'rejected_physical_joint_step'
