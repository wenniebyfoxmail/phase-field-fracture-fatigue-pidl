"""Binary64 representable box/TR certification; bounded exact ambiguity checks.

No physical assembly or model changes. A finite qualification failure is typed;
nonfinite/range/identity/IO errors are never converted to optional rejection.
"""
from fractions import Fraction
from time import process_time
import numpy as np

EXACT_COMPONENT_LIMIT=64
EXACT_CPU_SECONDS=.1

class CandidateUncertified(RuntimeError):
    def __init__(self,reason,diagnostics,vectors=None):
        super().__init__(reason);self.diagnostics=dict(diagnostics,reason=reason)
        self.vectors={}if vectors is None else vectors


def directed(value,toward):
    # A zero sum of two represented normal operands is exact cancellation.
    out=value.copy();np.nextafter(value,toward,out=out,where=value!=0)
    return out


def state_intervals(x0,D,radius,lo,hi):
    from hybrid_box_residual_subproblem import divide,normal
    if any(np.asarray(a).dtype!=np.dtype('float64')for a in[x0,D,lo,hi])or not(x0.shape==D.shape==lo.shape==hi.shape):raise RuntimeError('representable interval dtype/shape identity')
    if not np.isfinite(radius)or radius<=0:raise RuntimeError('invalid representable trust radius')
    if np.isnan(lo).any()or np.isnan(hi).any()or np.any(lo>hi)or np.any(lo==np.inf)or np.any(hi==-np.inf):raise RuntimeError('invalid represented original box')
    if np.any(D<=0):raise RuntimeError('nonpositive representable trust metric')
    for a in[x0,D]:normal(a,'representable interval input')
    if np.any(x0<lo)or np.any(x0>hi):raise RuntimeError('base outside original box')
    delta=divide(radius,D,'trust interval quotient')
    try:
        with np.errstate(all='raise'):
            inner_delta=np.nextafter(delta,-np.inf);outer_delta=np.nextafter(delta,np.inf)
            il=directed(x0-inner_delta,np.inf);iu=directed(x0+inner_delta,-np.inf)
            ol=directed(x0-outer_delta,-np.inf);ou=directed(x0+outer_delta,np.inf)
    except FloatingPointError as exc:raise RuntimeError('invalid range in representable interval')from exc
    for a in[inner_delta,outer_delta,il,iu,ol,ou]:normal(a,'representable interval endpoint')
    # Zero step is exact and always legal, even when the directed interval
    # collapses below one state ulp. Intersect with exact represented box.
    il=np.maximum(lo,np.minimum(il,x0));iu=np.minimum(hi,np.maximum(iu,x0))
    ol=np.maximum(lo,ol);ou=np.minimum(hi,ou)
    if np.any(il>iu)or np.any(ol>ou):raise RuntimeError('invalid representable interval ordering')
    return il,iu,ol,ou


def certify_state(x,x0,D,radius,lo,hi,*,intervals=None,exact_limit=EXACT_COMPONENT_LIMIT,
                  exact_cpu_seconds=EXACT_CPU_SECONDS):
    from hybrid_box_residual_subproblem import exact_difference,scaled_abs_upper,normal
    if exact_limit!=64 or exact_cpu_seconds!=.1:raise ValueError('exact qualification policy differs')
    if any(np.asarray(a).dtype!=np.dtype('float64')for a in[x,x0,D])or not(x.shape==x0.shape==D.shape):raise RuntimeError('candidate dtype/shape identity')
    for a in[x,x0,D]:normal(a,'candidate certification input')
    if np.any(D<=0)or not np.isfinite(radius)or radius<=0:raise RuntimeError('invalid candidate metric/radius')
    il,iu,ol,ou=state_intervals(x0,D,radius,lo,hi)if intervals is None else intervals
    p,tail=exact_difference(x,x0);raw_upper=scaled_abs_upper(D,p,tail)
    certified=raw_upper.copy();inner=(x>=il)&(x<=iu)
    certified[inner]=np.minimum(certified[inner],radius)
    ambiguous=(~inner)&(raw_upper>radius)
    indices=np.flatnonzero(ambiguous);records=[];used=0;started=process_time()
    diag=dict(dtype=str(x.dtype),predicate='abs(Fraction.from_float(D)*(Fraction.from_float(x)-Fraction.from_float(base)))<=Fraction.from_float(radius)',
        exact_limit=64,exact_cpu_limit_seconds=.1,exact_comparisons=0,exact_CPU_seconds=0.,
        inner_interval_certified_components=int(inner.sum()),ambiguous_components=int(indices.size),
        raw_max_upper=float(raw_upper.max(initial=0.)),radius=float(radius),exact_records=records)
    vectors=dict(candidate_x=x,candidate_p=p,candidate_tail=tail)
    def fail(reason,index=None):
        diag.update(exact_comparisons=used,exact_CPU_seconds=process_time()-started)
        if index is not None:diag.update(trigger_index=int(index),trigger_upper=float(raw_upper[index]),
            trigger_x_hex=float(x[index]).hex(),trigger_base_hex=float(x0[index]).hex(),trigger_D_hex=float(D[index]).hex(),
            trigger_inner_interval_hex=[float(il[index]).hex(),float(iu[index]).hex()],
            trigger_enclosing_interval_hex=[float(ol[index]).hex(),float(ou[index]).hex()],
            trigger_original_box_hex=[float(lo[index]).hex(),float(hi[index]).hex()])
        raise CandidateUncertified(reason,diag,vectors)
    box_bad=np.flatnonzero((x<lo)|(x>hi))
    if box_bad.size:fail('finite candidate outside original box',box_bad[0])
    outer_bad=np.flatnonzero((x<ol)|(x>ou))
    if outer_bad.size:fail('finite candidate outside enclosing trust interval',outer_bad[0])
    for i in indices:
        if used>=64:fail('exact component qualification budget exhausted',i)
        if process_time()-started>.1:fail('exact CPU qualification budget exhausted',i)
        # No decimal/text conversion or rounded D*p enters this predicate.
        exact=abs(Fraction.from_float(float(D[i]))*(Fraction.from_float(float(x[i]))-Fraction.from_float(float(x0[i]))))
        margin=Fraction.from_float(float(radius))-exact;used+=1
        records.append(dict(index=int(i),D_hex=float(D[i]).hex(),x_hex=float(x[i]).hex(),base_hex=float(x0[i]).hex(),radius_hex=float(radius).hex(),
            margin_numerator=str(margin.numerator),margin_denominator=str(margin.denominator),inside=margin>=0))
        if process_time()-started>.1:fail('exact CPU qualification budget exhausted',i)
        if margin<0:fail('finite candidate exactly outside trust domain',i)
        certified[i]=min(certified[i],radius)
    spent=process_time()-started
    if spent>.1:fail('exact CPU qualification budget exhausted')
    diag.update(exact_comparisons=used,exact_CPU_seconds=spent,
        certified_max_upper=float(certified.max(initial=0.)),certification='directed representable inner interval or sparse-action upper or exact binary64 comparison')
    if np.any(certified>radius):raise RuntimeError('unresolved representable trust certification')
    return p,tail,certified,diag


def representable_candidate(y,base,D,free,dofs,values,lower,crack,radius):
    from hybrid_box_residual_subproblem import divide,normal
    nu=len(free);u0=base['u'];d0=base['d'];x0=np.r_[u0[free],d0]
    if not np.array_equal(u0[dofs],values)or np.any(d0[crack]!=1)or np.any(lower[crack]!=1):raise RuntimeError('original base BC/precrack identity')
    lo=np.r_[np.full(nu,-np.inf),lower];hi=np.r_[np.full(nu,np.inf),np.ones(len(d0))]
    intervals=state_intervals(x0,D,radius,lo,hi);il,iu,_,_=intervals
    normal(y,'projected candidate coordinate');increment=divide(y,D,'candidate coordinate conversion')
    with np.errstate(all='raise'):proposed=x0+increment
    normal(proposed,'candidate represented state')
    x=np.clip(proposed,il,iu);x[nu:][crack]=1.
    p,tail,certified,diag=certify_state(x,x0,D,radius,lo,hi,intervals=intervals)
    u=u0.copy();u[free]=x[:nu];u[dofs]=values;d=x[nu:].copy()
    if not np.array_equal(u[dofs],values)or np.any(d[crack]!=1):raise RuntimeError('fixed domain identity changed')
    actual=D*p+D*tail;normal(actual,'actual scaled coordinate')
    diag['interval_projected_components']=int(np.count_nonzero(x!=proposed))
    return dict(u=u,d=d,p=p,p_tail=tail,y=actual,actual_TR_norm=float(certified.max(initial=0.)),
        raw_TR_upper=diag['raw_max_upper'],inward_ulp_corrections=0,
        interval_projected_components=diag['interval_projected_components'],feasibility=diag)
