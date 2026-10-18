"""E029 one-factor repair of E028's flat hard projection.

True differentiable bounded increments, frozen S1500 raw origin. No STE, history
update, target lower, prediction clipping, or import-time IO.
"""
import torch
from torch import nn
import s04_e027 as old
import s04_e028 as parent

PROTOCOL='S04-E029/v1-smooth-current-lower-increment-20261018'
EPS=1e-4
STEPS=200


class BoundedIncrement(nn.Module):
    def __init__(self,coordinates,lower,fixed,raw_origin,physical_seed):
        super().__init__()
        n=len(coordinates)
        if coordinates.shape!=(n,2) or not coordinates.is_floating_point() or fixed.shape!=(n,) or fixed.dtype!=torch.bool or fixed.device!=coordinates.device:
            raise ValueError('ordered native coordinates and fixed mask required')
        for name,value in [('coordinates',coordinates),('lower',lower),('raw_origin',raw_origin),('physical_seed',physical_seed)]:
            if value.dtype!=coordinates.dtype or value.device!=coordinates.device:raise ValueError('same dtype/device required')
            old.finite(value,name)
            if name!='coordinates' and value.shape!=(n,):raise ValueError('same-node vector required')
        if not bool(((lower>=0)&(lower<=1)&(physical_seed>=lower)&(physical_seed<=1)).all()):
            raise ValueError('seed and current lower must be feasible')
        if not bool((lower[fixed]==1).all()):raise ValueError('precrack lower must equal1')
        variable=(~fixed)&(lower<1)
        if not bool(variable.any()):raise ValueError('nonempty variable damage support required')
        denominator=torch.where(variable,1-lower,torch.ones_like(lower))
        # This one-time finite interior seed changes at most EPS per node.
        # It is derived only from original S1500 and the true c20s3 lower.
        probability=((physical_seed-lower)/denominator).clamp(EPS,1-EPS)
        for name,value in [('coordinates',coordinates),('lower',lower),('fixed',fixed),('variable',variable),
                           ('raw_origin',raw_origin),('seed_logit',torch.log(probability)-torch.log1p(-probability))]:
            self.register_buffer(name,value.detach().clone())

    def get_extra_state(self):return {'schema':'s04_e029_current_lower_increment_v1','epsilon':EPS,'raw_origin':'immutable_original_S1500','relative_transform':'asinh'}
    def set_extra_state(self,value):
        if value!=self.get_extra_state():raise ValueError('mapping checkpoint identity mismatch')

    def forward(self,coordinates,raw):
        if coordinates.requires_grad or coordinates.dtype!=self.coordinates.dtype or coordinates.device!=self.coordinates.device or not torch.equal(coordinates,self.coordinates):raise ValueError('identical native node order required')
        if raw.shape!=self.lower.shape or raw.dtype!=self.lower.dtype or raw.device!=self.lower.device:raise ValueError('raw node identity mismatch')
        old.finite(raw,'raw increment')
        delta=raw-self.raw_origin
        logit=self.seed_logit+torch.asinh(delta)
        old.finite(logit,'increment logit')
        probability=torch.sigmoid(logit)
        with torch.no_grad():
            derivative=(1-self.lower[self.variable])*probability[self.variable]*(1-probability[self.variable])/torch.hypot(torch.ones_like(delta[self.variable]),delta[self.variable])
            if not bool((derivative>0).any()):raise ValueError('all variable damage derivatives numerically zero; stop, no retry')
        damage=self.lower+(1-self.lower)*probability
        return torch.where(self.fixed|(~self.variable),torch.ones_like(damage),damage)

    def diagnostics(self,raw,growth_mask=None):
        with torch.no_grad():
            delta=raw.detach()-self.raw_origin
            logit=self.seed_logit+torch.asinh(delta)
            probability=torch.sigmoid(logit)
            derivative=torch.where(self.variable,(1-self.lower)*probability*(1-probability)/torch.hypot(torch.ones_like(delta),delta),torch.zeros_like(probability))
            out={}
            for name,mask in [('variable',self.variable),('target_growth',growth_mask)]:
                if mask is None:continue
                v=derivative[mask];z=logit[mask]
                out[name]=dict(nodes=int(mask.sum()),nonzero_true_derivative_fraction=float((v!=0).double().mean()),
                    derivative_gt_1e_minus8_fraction=float((v>1e-8).double().mean()),derivative_min=float(v.min()),derivative_max=float(v.max()),
                    logit_min=float(z.min()),logit_max=float(z.max()))
            return out


def fields(model,problem,mapper):
    raw=model(problem.xy);y=problem.xy[:,1];bubble=(y+.5)*(.5-y)
    d=mapper(problem.xy,raw[:,2])
    return torch.stack((old.US*bubble*raw[:,0],old.US*(bubble*raw[:,1]+y+.5),d),1)


def representation_stats(model,problem,mapper):
    with torch.no_grad():raw=model(problem.xy)[:,2]
    growth=mapper.variable&(problem.ref[:,2]>problem.previous+1e-10)
    return mapper.diagnostics(raw,growth)


def check_flow(mapper,raw):
    stats=mapper.diagnostics(raw)['variable']
    if stats['nonzero_true_derivative_fraction']==0:raise ValueError('all variable damage derivatives numerically zero; stop, no retry')
