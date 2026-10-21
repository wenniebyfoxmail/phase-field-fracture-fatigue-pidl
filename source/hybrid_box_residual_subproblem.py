"""Box/inf-TR residual LS: certified feasible Cauchy + bounded improvements.

No normal matrix, dense Gram, spectral estimate, regularization or physical
equation change. Certificates use fixed r0=fl(w*F), J, w, D; q(p)=.5||r0+diag(w)Jp||².
"""
import numpy as np
from scipy import sparse

EPS=np.finfo(float).eps;TINY=np.finfo(float).tiny
def up(x):return float(np.nextafter(float(x),np.inf))
def down(x):return float(np.nextafter(float(x),-np.inf))
def gamma(n):
    a=n*EPS
    if not 0<=a<.01:raise RuntimeError('unsupported rounding-bound operation count')
    return up(a/(1-a))
def normal(a,name):
    x=np.asarray(a);v=abs(x[x!=0])
    if not np.isfinite(x).all()or(v.size and np.min(v)<TINY):
        raise RuntimeError('nonfinite/subnormal '+name)
def product_range(a,b,name):
    normal(a,name);normal(b,name)
    x=abs(np.asarray(a));y=abs(np.asarray(b));x=x[x!=0];y=y[y!=0]
    if x.size and y.size:
        if np.log(np.min(x))+np.log(np.min(y))<np.log(TINY):
            raise RuntimeError('unbounded underflow in '+name)
        if np.log(np.max(x))+np.log(np.max(y))>np.log(np.finfo(float).max)-2*EPS:
            raise RuntimeError('unbounded overflow in '+name)
def divide(a,b,name):
    normal(a,name);normal(b,name)
    try:
        with np.errstate(all='raise'):value=np.asarray(a)/b
    except FloatingPointError as exc:raise RuntimeError('invalid range in '+name)from exc
    normal(value,name)
    if np.any((np.asarray(a)!=0)&(value==0)):raise RuntimeError('underflow in '+name)
    return value

def multiply(a,b,name):
    product_range(a,b,name)
    try:
        with np.errstate(all='raise'):value=np.asarray(a)*b
    except FloatingPointError as exc:raise RuntimeError('invalid range in '+name)from exc
    normal(value,name)
    if np.any((np.asarray(a)!=0)&(np.asarray(b)!=0)&(value==0)):raise RuntimeError('underflow in '+name)
    return value

def mul_upper(a,b):
    product_range(np.array([a]),np.array([b]),'bound product')
    return up(a*b)if a and b else 0.
def sum_upper(*args):
    out=0.
    for x in args:out=up(out+x)if out or x else 0.
    return out
def dot_bound(a,b):
    a=np.asarray(a);b=np.asarray(b);product_range(a,b,'dot')
    value=float(a@b);s=float(np.sum(abs(a*b)));g=gamma(2*len(a)+8)
    error=up(g*s/(1-g))if s else 0.
    normal(np.array([value,error]),'dot interval')
    return value,error
def positive_dot_upper(a,b):
    v,e=dot_bound(np.asarray(a),np.asarray(b));return sum_upper(v,e)


def original_natural_jacobian(model,scale):
    I=model['inactive'].astype(float);active=1-I
    C=sparse.diags(I/scale)@model['C']
    D=sparse.diags(I/scale)@model['D']+sparse.diags(active)
    J=sparse.bmat([[model['A'],model['B']],[C,D]],format='csc')
    J.sum_duplicates();J.eliminate_zeros();J.sort_indices();normal(J.data,'original Jacobian')
    return J


class Budget:
    def __init__(self,actions=100,updates=16):
        if type(actions)is not int or not 1<=actions<=100 or type(updates)is not int or not 1<=updates<=16:
            raise ValueError('unbounded box subproblem budget')
        self.limit=actions;self.update_limit=updates;self.updates=0
        self.exact_comparisons=0;self.exact_CPU_seconds=0.
        self.counts=dict(J=0,JT=0,abs_J=0,abs_JT=0,norm_scans=0,metric_scan=0,legacy_Newton_action_upper=12)
        if self.used>actions:raise RuntimeError('subproblem action budget exhausted')
    @property
    def used(self):return sum(self.counts.values())
    def action(self,key,n=1):
        if self.used+n>self.limit:raise RuntimeError('subproblem action budget exhausted')
        self.counts[key]+=n
    def update(self):
        if self.updates>=self.update_limit:raise RuntimeError('subproblem update budget exhausted')
        self.updates+=1


def freeze_variable_metric(J,w,budget):
    budget.action('metric_scan');product_range(J.data,w,'metric row scaling')
    M=J.multiply(w[:,None]).tocsc();product_range(M.data,M.data,'metric squares')
    D=np.sqrt(np.asarray(M.multiply(M).sum(axis=0)).ravel())
    normal(D,'frozen variable metric')
    if np.any(D<=0):raise RuntimeError('zero initial variable metric column')
    return D


class Model:
    def __init__(self,J,F,w,D,budget):
        self.J=J.tocsc();self.absJ=abs(self.J);self.F=np.asarray(F);self.w=np.asarray(w);self.D=np.asarray(D);self.budget=budget
        for a in [self.F,self.w,self.D]:normal(a,'model input')
        if np.any(self.w<=0)or np.any(self.D<=0):raise RuntimeError('nonpositive model scale')
        product_range(self.w,self.F,'weighted residual');self.r=self.w*self.F
        self.q0=.5*dot_bound(self.r,self.r)[0]
        rowdegree=np.diff(self.J.tocsr().indptr);coldegree=np.diff(self.J.indptr)
        self.gr=gamma(int(rowdegree.max(initial=0))+4);self.gf=gamma(2*int(rowdegree.max(initial=0))+8);self.gc=gamma(int(coldegree.max(initial=0))+4)
        budget.action('norm_scans',2)
        product_range(J.data,w,'model row scaling');M=J.multiply(w[:,None]).tocsc()
        inv=divide(1.,self.D,'inverse variable metric');product_range(M.data,inv,'model column scaling');M=M.multiply(inv[None,:]).tocsc()
        normal(M.data,'scaled Jacobian')
        row=float(np.max(np.asarray(abs(M).sum(axis=1)),initial=0.));col=float(np.max(np.asarray(abs(M).sum(axis=0)),initial=0.))
        # Covers sums and represented row/column scaling, including reciprocal.
        row=up(row/(1-self.gr)/(1-gamma(4)));col=up(col/(1-self.gc)/(1-gamma(4)))
        self.L=mul_upper(row,col)
        if not np.isfinite(self.L)or self.L<=0:raise RuntimeError('zero/nonfinite model Lipschitz bound')
        self.h,self.herror=self.gradient(self.r,with_error=True)
        self.g=divide(self.h,self.D,'scaled model gradient')
    def gradient(self,residual,with_error=False):
        product_range(self.w,residual,'transpose row scaling');v=self.w*residual
        product_range(self.J.data,v,'transpose action');self.budget.action('JT');h=np.asarray(self.J.T@v)
        normal(h,'transpose result')
        if not with_error:return divide(h,self.D,'scaled LS gradient')
        self.budget.action('abs_JT');s=np.asarray(self.absJ.T@abs(v))
        # Input w*r multiplication and the subsequent sparse transpose dot.
        coefficient=up((self.gc+(1+self.gc)*EPS/(1-EPS))/(1-self.gc)/(1-gamma(8)))
        error=np.nextafter(coefficient*s,np.inf);error[s==0]=0.;normal(error,'transpose error bound')
        return h,error
    def evaluate(self,p,tail=None):
        p=np.asarray(p);tail=np.zeros_like(p)if tail is None else np.asarray(tail)
        product_range(self.J.data,p,'Jacobian action');self.budget.action('J')
        raw=np.asarray(self.J@p)
        if np.any(tail):
            product_range(self.J.data,tail,'Jacobian exact-step tail');self.budget.action('J')
            raw=raw+np.asarray(self.J@tail)
        normal(raw,'combined actual Jacobian action')
        product_range(self.w,raw,'model residual scaling');v=self.w*raw;res=self.r+v
        normal(res,'linearized model residual')
        rv,erv=dot_bound(self.r,v);vv,evv=dot_bound(v,v)
        pred=-rv-.5*vv;q=.5*dot_bound(res,res)[0]
        self.budget.action('abs_J');s=np.asarray(self.absJ@abs(p))
        if np.any(tail):
            self.budget.action('abs_J');s=s+np.asarray(self.absJ@abs(tail))
        s=s/(1-self.gf)
        error_v=np.nextafter((self.w*(self.gf*s)+EPS/(1-EPS)*abs(v))/(1-gamma(8)),np.inf);error_v[(s==0)&(v==0)]=0.
        normal(error_v,'forward error bound')
        propagated=sum_upper(positive_dot_upper(abs(self.r),error_v),positive_dot_upper(abs(v),error_v),.5*positive_dot_upper(error_v,error_v))
        err=sum_upper(erv,.5*evv,propagated,mul_upper(gamma(8),abs(rv)+.5*abs(vv)))
        lo=down(pred-err);hi=up(pred+err)
        if not np.isfinite([pred,q,lo,hi]).all():raise RuntimeError('nonfinite model decrease interval')
        return dict(p=p,residual=res,model_value=q,predicted_reduction=pred,pred_lower=lo,pred_upper=hi,pred_error=err)
    def cauchy_certificate(self,p,evaluation,tail=None):
        tail=np.zeros_like(p)if tail is None else tail
        y=scaled_abs_upper(self.D,p,tail)
        n,en=dot_bound(y,y);norm_upper=up(n+en)
        hd,ehd=dot_bound(self.h,p);ht,eht=dot_bound(self.h,tail)
        he=sum_upper(positive_dot_upper(self.herror,abs(p)),positive_dot_upper(self.herror,abs(tail)))
        quad=mul_upper(.5,mul_upper(self.L,norm_upper))
        lower=down(-hd-ht)
        for error in [ehd,eht,he,quad]:lower=down(lower-error)
        required=mul_upper(.25,mul_upper(self.L,norm_upper))
        if not(required>0 and lower>=required and evaluation['pred_lower']>=required):
            raise RuntimeError('cannot certify sufficient feasible Cauchy model decrease')
        return dict(cauchy_model_lower_bound=lower,cauchy_required_bound=required,
            cauchy_quadratic_upper=mul_upper(.5,mul_upper(self.L,norm_upper)),
            cauchy_scaled_step_squared=n,model_L_upper=self.L,
            certificate_object='fixed r0=fl(w*originalF), represented J/w/D; exact actual state difference=high+tail; outward rounding bounds; subnormal/underflow stops')


def exact_difference(x,base):
    # Knuth TwoDiff: exact real difference of represented states = high+tail.
    high=x-base;bvirtual=x-high;avirtual=high+bvirtual
    bround=bvirtual-base;around=x-avirtual;tail=around+bround
    for a in [high,bvirtual,avirtual,bround,around,tail]:normal(a,'two-difference intermediate')
    return high,tail


def scaled_abs_upper(D,p,tail):
    product_range(D,p,'actual scaled step');product_range(D,tail,'actual scaled tail')
    a=abs(D*p);b=abs(D*tail)
    a=np.where(a==0,0.,np.nextafter(a,np.inf));b=np.where(b==0,0.,np.nextafter(b,np.inf))
    result=np.nextafter(a+b,np.inf);result[(a==0)&(b==0)]=0.
    normal(result,'actual scaled-step upper bound')
    return result


def feasible_candidate(y,base,D,free,dofs,values,lower,crack,radius):
    from hybrid_representable_box import representable_candidate
    return representable_candidate(y,base,D,free,dofs,values,lower,crack,radius)


def box_bounds(base,D,nu,lower,radius):
    lo=np.r_[np.full(nu,-radius),np.maximum(multiply(D[nu:],lower-base['d'],'lower bound scaling'),-radius)]
    hi=np.r_[np.full(nu,radius),np.minimum(multiply(D[nu:],1-base['d'],'upper bound scaling'),radius)]
    if np.any(lo>0)or np.any(hi<0)or np.any(lo>hi):raise RuntimeError('trust box must contain zero')
    return lo,hi


def solve_box_model(model,base,free,dofs,values,lower,crack,radius,newton_p,subspace_steps=2,stage_observer=None):
    from hybrid_representable_box import CandidateUncertified
    b=model.budget;lo,hi=box_bounds(base,model.D,len(free),lower,radius)
    exact_total=b.exact_comparisons;exact_cpu=b.exact_CPU_seconds;certificate={};best=None
    def stage(name,point=None,**extra):
        if stage_observer is not None:stage_observer(name,point,best,dict(certificate,
            exact_comparisons_cumulative=exact_total,exact_CPU_seconds_cumulative=exact_cpu,**extra))
    def feasible(name,y):
        nonlocal exact_total,exact_cpu
        stage(name+'_start')
        try:
            point=feasible_candidate(y,base,model.D,free,dofs,values,lower,crack,radius)
        except CandidateUncertified as exc:
            exact_total+=exc.diagnostics['exact_comparisons'];exact_cpu+=exc.diagnostics['exact_CPU_seconds']
            b.exact_comparisons=exact_total;b.exact_CPU_seconds=exact_cpu
            stage(name+'_unqualified',qualification=exc.diagnostics,failure_vectors=exc.vectors)
            raise
        exact_total+=point['feasibility']['exact_comparisons'];exact_cpu+=point['feasibility']['exact_CPU_seconds']
        b.exact_comparisons=exact_total;b.exact_CPU_seconds=exact_cpu
        return point
    if b.updates>=b.update_limit-1:raise RuntimeError('subproblem update budget exhausted')
    b.update();stage('Cauchy_scaling_start');yc=np.clip(divide(-model.g,model.L,'Cauchy scaled step'),lo,hi)
    if not np.any(yc):raise RuntimeError('zero projected model gradient with nonzero physical residual')
    best=feasible('Cauchy',yc)
    if not np.any(best['p']):raise RuntimeError('Cauchy step lost to represented-state rounding')
    stage('Cauchy_before_model',best)
    best.update(model.evaluate(best['p'],best['p_tail']));stage('Cauchy_model_evaluated',best)
    certificate=model.cauchy_certificate(best['p'],best,best['p_tail'])
    cauchy_p=best['p'].copy();cauchy_tail=best['p_tail'].copy();cauchy_lower=best['pred_lower'];best['selection']='certified_projected_Cauchy'
    stage('Cauchy_certified',best)
    for i in range(subspace_steps):
        if b.updates>=b.update_limit-1:break
        b.update();stage('PG'+str(i+1)+'_gradient_start');gradient=model.gradient(best['residual'])
        y=np.clip(best['y']-divide(gradient,model.L,'projected LS gradient step'),lo,hi)
        candidate=feasible('PG'+str(i+1),y)
        stage('PG'+str(i+1)+'_before_model',candidate)
        candidate.update(model.evaluate(candidate['p'],candidate['p_tail']))
        improved=candidate['pred_lower']>=best['pred_upper']
        if improved:best=candidate;best['selection']='projected_LS_gradient_improvement'
        stage('PG'+str(i+1)+'_complete',candidate,retained_as_best=improved)
    optional_status='not_attempted_finite_update_budget'
    if b.updates<b.update_limit-1:
        b.update();stage('optional_Newton_scaling_start');yn=np.clip(multiply(model.D,newton_p,'Newton scaled step'),lo,hi)
        try:candidate=feasible('optional_Newton',yn)
        except CandidateUncertified:
            # Only typed finite qualification failure is optional. Range,
            # data/identity, model, direction-quality and IO errors propagate.
            optional_status='finite_feasibility_qualification_not_obtained'
        else:
            stage('optional_Newton_before_model',candidate)
            candidate.update(model.evaluate(candidate['p'],candidate['p_tail']))
            improved=candidate['pred_lower']>=best['pred_upper']
            if improved:best=candidate;best['selection']='qualified_Newton_model_comparison'
            optional_status='selected'if improved else'model_not_proven_better'
            stage('optional_Newton_complete',candidate,retained_as_best=improved)
    if best['pred_lower']<cauchy_lower:raise RuntimeError('subproblem worse than certified Cauchy point')
    best.update(certificate,cauchy_p=cauchy_p,cauchy_tail=cauchy_tail,cauchy_pred_lower=cauchy_lower,
        subproblem_updates=b.updates,action_counts=dict(b.counts),action_count_upper=b.used,
        exact_comparisons_cumulative=exact_total,exact_CPU_seconds_cumulative=exact_cpu,
        optional_Newton_status=optional_status,original_nonlinear_acceptance=False)
    return best
