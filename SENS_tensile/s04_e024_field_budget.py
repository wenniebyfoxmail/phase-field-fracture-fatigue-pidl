"""D013 physical-field trust region. Pure algebra; no model loading or training."""
from dataclasses import dataclass
import hashlib
import math
import time
import numpy as np
from scipy.optimize import minimize, nnls
from scipy.linalg.blas import dgemm

REGIONS = ('full', 'damage', 'background', 'inside_background')
GUARDS = ('uv_full', 'uv_damage', 'uv_background', 'uv_inside_background',
          'weak_squared', 'driver_background', 'driver_inside_background',
          'strain_full', 'strain_damage', 'strain_background',
          'strain_inside_background', 'driver_full', 'driver_damage')
BUDGETS = ('uv_change', 'strain_change', 'driver_change', 'force_change')
PROFILES = (('strict_eta_0.1', .1, True), ('strict_eta_0.3', .3, True),
            ('strict_eta_1.0', 1., True), ('seven_guard_eta_0.3', .3, False))
STATES = ('c20s4', 'c60s4', 'c83s4')
PLAN_SHA = '0441e6cc847c501b822c5bb1fbf0ed816bd8a97bc5c526178a0d88aa50280d32'
CONTRACT_SHA = '8bc35175839dc69ee4fcab618903a5043401d871f45cdfc104c88f6527834236'


class InvalidEvidence(ValueError):
    """Global stop: identity, numerical or realizability failure."""


class ResourceStop(RuntimeError):
    """Global stop: no later profile/state."""


def finite(*arrays):
    if not all(np.isfinite(a).all() for a in arrays):
        raise InvalidEvidence('nonfinite input, field or numerical result')


def digest_array(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256(str((a.shape, a.dtype.str)).encode()+a.tobytes()).hexdigest()


def safe_json(x):
    """Infinity only represents an explicit zero-scale diagnostic, never a field."""
    if isinstance(x, dict): return {k: safe_json(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)): return [safe_json(v) for v in x]
    if isinstance(x, np.ndarray): return safe_json(x.tolist())
    if isinstance(x, np.generic): return safe_json(x.item())
    if isinstance(x, float):
        if math.isnan(x): raise InvalidEvidence('NaN record')
        if math.isinf(x): return 'Infinity' if x > 0 else '-Infinity'
    return x


def ratio_norm(squared, scale_squared):
    finite(squared, scale_squared)
    if squared < 0 or scale_squared < 0: raise InvalidEvidence('negative squared norm')
    if scale_squared == 0: return 0. if squared == 0 else math.inf
    return float(np.sqrt(squared/scale_squared))


def squared(a, weight):
    a = np.asarray(a); w = np.asarray(weight)
    finite(a, w)
    if a.shape[:w.ndim] != w.shape or np.any(w < 0):
        raise InvalidEvidence('weighted field schema')
    return float(np.sum(w.reshape(w.shape+(1,)*(a.ndim-w.ndim))*a*a))


class Metrics:
    """Immutable origin centre and FEM errors; all actual fields supplied by raw forward."""
    def __init__(self, origin, reference, node_weights, gp_weights):
        self.origin = {k: np.array(origin[k], copy=True) for k in ('uv','strain','driver','force')}
        self.reference = {k: np.array(reference[k], copy=True) for k in ('uv','strain','driver')}
        self.node_weights = {k: np.array(node_weights[k], copy=True) for k in REGIONS}
        self.gp_weights = {k: np.array(gp_weights[k], copy=True) for k in REGIONS}
        for d in (self.origin, self.reference, self.node_weights, self.gp_weights):
            for a in d.values(): finite(a); a.flags.writeable = False
        for d in (self.node_weights, self.gp_weights):
            if any(np.any(w < 0) or w.sum() <= 0 for w in d.values()):
                raise InvalidEvidence('empty/negative fixed region')
        self.ceilings = self.errors(self.origin)
        self.scales_sq = self.ceilings[[0,7,11,4]].copy()
        self.scales_sq.flags.writeable = False
        self.centre_digest = {k:digest_array(v) for k,v in self.origin.items()}

    def errors(self, f):
        if any(np.shape(f[k]) != np.shape(v) for k,v in self.origin.items()):
            raise InvalidEvidence('actual field shape drift')
        finite(*(f[k] for k in self.origin))
        u = [squared(f['uv']-self.reference['uv'], self.node_weights[r]) for r in REGIONS]
        e = [squared(f['strain']-self.reference['strain'], self.gp_weights[r]) for r in REGIONS]
        p = [squared(f['driver']-self.reference['driver'], self.gp_weights[r]) for r in REGIONS]
        return np.array(u+[float(np.sum(f['force']**2)),p[2],p[3]]+e+[p[0],p[1]])

    def evaluate(self, f):
        errors = self.errors(f)
        changes = np.array([squared(f['uv']-self.origin['uv'], self.node_weights['full']),
                            squared(f['strain']-self.origin['strain'], self.gp_weights['full']),
                            squared(f['driver']-self.origin['driver'], self.gp_weights['full']),
                            float(np.sum((f['force']-self.origin['force'])**2))])
        finite(changes, errors)
        q = [ratio_norm(x,s) for x,s in zip(changes,self.scales_sq)]
        return dict(guards=dict(zip(GUARDS,errors.tolist())), changes_sq=changes.tolist(),
                    budget_components=dict(zip(BUDGETS,q)), budget_q=max(q))

    def violations(self, evaluation, eta, strict):
        if eta not in (.1,.3,1.): raise InvalidEvidence('unregistered physical radius')
        values = evaluation['guards']
        if tuple(values) != GUARDS: raise InvalidEvidence('13 guard schema/order')
        finite(list(values.values()))
        failures = [k for i,k in enumerate(GUARDS) if (strict or i < 7) and values[k] > self.ceilings[i]]
        if evaluation['budget_q'] > eta: failures.append('physical_budget')
        return failures

    def report(self, f):
        ev = self.evaluate(f); result = {}
        for prefix,field,weights in [('uv','uv',self.node_weights),('strain','strain',self.gp_weights),('driver','driver',self.gp_weights)]:
            for region in REGIONS:
                error = squared(f[field]-self.reference[field],weights[region])
                reference = squared(self.reference[field],weights[region])
                result[prefix+'_'+region] = dict(error_integral=error,
                    error_RMS=float(np.sqrt(error/weights[region].sum())),
                    relative_L2=None if reference==0 else float(np.sqrt(error/reference)),
                    reference_integral=reference)
        return dict(**ev,region_metrics=result,rho_u=float(np.linalg.norm(f['force'])))


@dataclass
class Quadratics:
    """Raw squared fields: c + 2*b.p + p.H.p. 13 errors, then4 changes."""
    c: np.ndarray
    b: np.ndarray
    h: np.ndarray

    @classmethod
    def empty(cls,n): return cls(np.zeros(17),np.zeros((17,n)),np.zeros((17,n,n)))

    def add(self,index,residual,jacobian,weight,constant=True):
        residual=np.asarray(residual); j=np.asarray(jacobian)
        w=np.broadcast_to(np.asarray(weight).reshape(np.shape(weight)+(1,)*(residual.ndim-np.ndim(weight))),residual.shape).ravel()
        x=residual.ravel();j=j.reshape(len(x),-1)
        finite(x,j,w)
        if constant:self.c[index]+=float(np.dot(w,x*x))
        self.b[index]+=np.einsum('n,ni,n->i',w,j,x)
        a=np.asarray(j*np.sqrt(w)[:,None],order='F')
        self.h[index]+=dgemm(1.,a,a,trans_a=True)

    def values(self,p):
        finite(p)
        return self.c+2*np.einsum('ki,i->k',self.b,p)+np.einsum('i,kij,j->k',p,self.h,p)

    def jacobian(self,p): return 2*self.b+2*np.einsum('kij,j->ki',self.h,p)

    def fingerprint(self):return dict(c=digest_array(self.c),b=digest_array(self.b),h=digest_array(self.h))


def preconditioner(pack, scales):
    """Invertible field-only change of coordinates. No parameter ball/penalty."""
    p=pack.h[13]/scales[0]
    if scales[1]>0:p=p+pack.h[14]/scales[1]
    finite(p)
    eig,v=np.linalg.eigh((p+p.T)/2)
    if eig[-1] <= 0 or eig[0] < -1e-12*max(1.,eig[-1]):
        raise InvalidEvidence('field Gram not PSD/resolved')
    floor=1e-10*eig[-1]
    t=v/np.sqrt(np.maximum(eig,floor))[None,:]
    finite(t)
    return t,dict(spectrum=eig.tolist(),floor=float(floor),all_coordinates_retained=len(eig),
                  rank_rtol_1e12=int(np.sum(eig>1e-12*eig[-1])),
                  rank_rtol_1e14=int(np.sum(eig>1e-14*eig[-1])),
                  condition=None if eig[0]<=0 else float(eig[-1]/eig[0]))


def solve_proxy(pack,metrics,eta,strict,check=lambda:None):
    if metrics.ceilings[0]==0:raise InvalidEvidence('exact UV origin must bypass solver')
    finite(pack.c,pack.b,pack.h)
    if pack.h.shape!=(17,len(pack.b[0]),len(pack.b[0])) or pack.b.shape!=(17,pack.h.shape[-1]) or pack.c.shape!=(17,):
        raise InvalidEvidence('17-quadratic schema')
    np.testing.assert_allclose(pack.h,pack.h.transpose(0,2,1),rtol=1e-12,atol=1e-25)
    spectra=np.linalg.eigvalsh(pack.h)
    if np.any(spectra[:,0]<-1e-12*np.maximum(1.,spectra[:,-1])):
        raise InvalidEvidence('nonconvex physical proxy')
    check()
    t,spectrum=preconditioner(pack,metrics.scales_sq)
    check()
    b=np.einsum('ki,ij->kj',pack.b,t)
    h=np.stack([dgemm(1.,dgemm(1.,np.asarray(t,order='F'),np.asarray(hh,order='F'),trans_a=True),np.asarray(t,order='F')) for hh in pack.h])
    active=list(range(1,13 if strict else 7))+list(range(13,17))
    limits=np.r_[metrics.ceilings,eta*eta*metrics.scales_sq]
    # A zero ceiling is an exact squared-norm-zero condition, never an epsilon floor.
    scale=np.where(limits>0,limits,1.)
    def values(y):
        check();return pack.c+2*np.einsum('ki,i->k',b,y)+np.einsum('i,kij,j->k',y,h,y)
    def jac(y):return 2*b+2*np.einsum('kij,j->ki',h,y)
    def fun(y):return float(values(y)[0]/metrics.ceilings[0])
    def grad(y):return jac(y)[0]/metrics.ceilings[0]
    def cons(y):return (limits-values(y))[active]/scale[active]
    def cjac(y):return -jac(y)[active]/scale[active,None]
    trace=[]
    def cb(y):check();trace.append(dict(objective=fun(y),max_proxy_violation=float(np.max(-cons(y)))))
    try:
        r=minimize(fun,np.zeros(t.shape[0]),jac=grad,method='SLSQP',
            constraints=[dict(type='ineq',fun=cons,jac=cjac)],callback=cb,
            options=dict(maxiter=200,ftol=1e-10))
    except (ResourceStop,InvalidEvidence):raise
    except Exception as e:return None,dict(feasible=False,solver_exception=type(e).__name__+': '+str(e),trace=trace)
    p=np.einsum('ij,j->i',t,r.x);finite(p)
    vals=pack.values(p);normalized=(vals-limits)/scale
    feasible=bool(np.max(normalized[active])<=1e-8)
    # KKT diagnostics are for the returned proxy witness only; not a global physics bound.
    tight=[i for i in active if normalized[i]>=-1e-7]
    j=pack.jacobian(p)/scale[:,None];objective_j=pack.jacobian(p)[0]/metrics.ceilings[0]
    kkt_error=None
    try:
        if tight:
            lam,_=nnls(j[tight].T,-objective_j,maxiter=10*len(tight)+100)
            finite(lam)
            residual=float(np.linalg.norm(objective_j+np.einsum('ki,k->i',j[tight],lam)))
        else:lam=np.array([]);residual=float(np.linalg.norm(objective_j))
    except RuntimeError as e:
        lam=np.array([]);residual=None;kkt_error=str(e)
    return p,dict(success=bool(r.success),message=str(r.message),iterations=int(r.nit),
        function_evaluations=int(r.nfev),feasible=feasible,proxy_values=vals.tolist(),
        normalized_violations=normalized.tolist(),active_constraint_indices=active,
        tight_indices=tight,nonnegative_multipliers=lam.tolist(),stationarity_norm=None if residual is None else float(residual),kkt_error=kkt_error,
        gram_spectra_extremes=np.stack([spectra[:,0],spectra[:,-1]],axis=1).tolist(),
        preconditioner=spectrum,trace=trace,model_sha256=pack.fingerprint(),
        scope='finite convex proxy return only; no nonlinear/full-head optimum claim')


def quantize_head(head,dtype):
    finite(head)
    q=np.asarray(head,dtype=dtype)
    finite(q)
    return q.copy()


def run_profile(adapter,metrics,eta,strict,check,emit,solver=solve_proxy):
    """Up to3 models/9 halvings; authoritative forward precedes every actual test."""
    theta0=adapter.theta.copy();current=theta0.copy();fields=adapter.origin
    current_ev=metrics.evaluate(fields)
    if metrics.ceilings[0]==0:
        return current,fields,dict(stop='NO_CORRECTION_ALREADY_EXACT',solves=0,trials=0,accepted_steps=0)
    accepted=0;visited=0;solves=0;stop='MAX_RELINEARIZATIONS'
    for outer in range(3):
        check();adapter.check_identity()
        t0=time.monotonic();pack=adapter.proxy(fields,metrics,check)
        build_wall=time.monotonic()-t0
        check();solves+=1;t0=time.monotonic()
        direction,info=solver(pack,metrics,eta,strict,check)
        solve_wall=time.monotonic()-t0
        emit(dict(kind='solver',outer=outer,incumbent=current,direction=direction,info=info,model_sha256=pack.fingerprint(),build_wall_seconds=build_wall,solve_wall_seconds=solve_wall))
        if direction is None or not info['feasible']:stop='NO_PROXY_FEASIBLE_RETURN';break
        chosen=False
        for k in range(9):
            check()
            head=quantize_head(current+2.**(-k)*direction.reshape(current.shape),theta0.dtype)
            step=(head.astype(np.float64)-current.astype(np.float64)).ravel()
            predicted=float((pack.c[0]-pack.values(step)[0])/metrics.ceilings[0])
            # All actual measurements come from quantized raw-network head, never affine UV.
            t0=time.monotonic();f=adapter.realize(head);adapter.check_identity();check()
            raw_wall=time.monotonic()-t0;t0=time.monotonic()
            realization=adapter.check_realization(head,f,metrics)
            ev=metrics.evaluate(f);failures=metrics.violations(ev,eta,strict)
            score_wall=time.monotonic()-t0
            actual=(current_ev['guards']['uv_full']-ev['guards']['uv_full'])/metrics.ceilings[0]
            ratio=actual/predicted if predicted>0 else -math.inf
            if predicted<=1e-8 or actual<=1e-8 or ratio<.1:failures.append('insufficient_actual_or_predicted_gain')
            ok=not failures;visited+=1
            emit(dict(kind='trial',outer=outer,k=k,head=head,actual=ev,
                proxy_values=pack.values(step),predicted_reduction=predicted,
                actual_reduction=float(actual),agreement_ratio=float(ratio),accepted=ok,
                realization=realization,raw_wall_seconds=raw_wall,score_wall_seconds=score_wall,
                failures=failures,relative_head_change=float(np.linalg.norm(head-theta0)/np.linalg.norm(theta0))
                if np.linalg.norm(theta0)>0 else None))
            if ok:
                current=head;fields=f;current_ev=ev;accepted+=1;chosen=True;break
        if not chosen:stop='ALL_NINE_REJECTED';break
    adapter.check_identity();check()
    return current,fields,dict(stop=stop,solves=solves,trials=visited,accepted_steps=accepted)
