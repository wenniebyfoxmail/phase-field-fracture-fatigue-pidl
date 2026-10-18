"""E030 isolation: retain exact E029 smooth damage map, freeze physical UV0."""
import torch
from torch import nn
import s04_e027 as old
from s04_e029 import BoundedIncrement,EPS,STEPS

PROTOCOL='S04-E030/v1-fixed-physical-UV0-damage-isolation-20261018'


class FixedDisplacement(nn.Module):
    """Native ordered zero-step physical displacement, never FEM target UV."""
    def __init__(self,coordinates,initial_physical_uv):
        super().__init__()
        if coordinates.ndim!=2 or coordinates.shape[1]!=2 or initial_physical_uv.shape!=coordinates.shape:
            raise ValueError('same-node xy and physical u/v required')
        if coordinates.dtype!=initial_physical_uv.dtype or coordinates.device!=initial_physical_uv.device:
            raise ValueError('same dtype/device required')
        if not coordinates.is_floating_point():raise ValueError('floating fields required')
        old.finite(coordinates,'ordered xy');old.finite(initial_physical_uv,'physical UV0')
        self.register_buffer('coordinates',coordinates.detach().clone())
        self.register_buffer('physical_uv',initial_physical_uv.detach().clone())

    def get_extra_state(self):return {'schema':'s04_e030_fixed_physical_uv0_v1','origin':'original_S1500_physical_UV_not_FEM_target'}
    def set_extra_state(self,value):
        if value!=self.get_extra_state():raise ValueError('fixed UV checkpoint identity mismatch')

    def forward(self,coordinates):
        if coordinates.requires_grad or coordinates.dtype!=self.coordinates.dtype or coordinates.device!=self.coordinates.device or not torch.equal(coordinates,self.coordinates):
            raise ValueError('identical native coordinate order required')
        return self.physical_uv


def fields(model,problem,mapper,fixed_uv):
    raw=model(problem.xy)[:,2]
    damage=mapper(problem.xy,raw)
    return torch.cat((fixed_uv(problem.xy),damage[:,None]),1)


def assert_fixed_uv(q,fixed_uv):
    if not torch.equal(q[:,:2],fixed_uv.physical_uv):raise ValueError('physical UV0 changed')
