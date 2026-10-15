"""E021 nontraining prototype: one bounded teacher-residual coordinate rule."""
import numpy as np
import torch

from s04_e019_frozen_residual import FrozenResidualUV
from s04_e018_global_local import compact_window

RULE = "core-damage-residual-moments-3std-cap4-v1"


def coordinate_rule(data, base_uv, geometry):
    xy, mass, damage = (np.asarray(data[k], dtype=float) for k in ("xy", "mass", "damage"))
    target = np.asarray(data["equilibrated_uv"], dtype=float)
    base_uv = np.asarray(base_uv, dtype=float)
    if xy.shape != target.shape or target.shape != base_uv.shape or xy.ndim != 2 or xy.shape[1] != 2:
        raise ValueError("coordinate/UV schema")
    if mass.shape != (len(xy),) or damage.shape != mass.shape or np.any(mass<=0):
        raise ValueError("mass/damage schema")
    if not all(np.isfinite(v).all() for v in (xy,mass,damage,target,base_uv)):
        raise ValueError("nonfinite coordinate-rule input")
    original = np.asarray(geometry["scale"], dtype=float)
    if original.shape != (2,) or not np.isfinite(original).all() or np.any(original<=0):
        raise ValueError("invalid original coordinate scale")
    core = np.all((xy >= geometry["lower"]) & (xy <= geometry["upper"]),axis=1)
    energy = mass*np.sum((target-base_uv)**2,axis=1)
    selected = core & (damage>.1)
    weights = energy*selected
    if not np.isfinite(weights.sum()) or weights.sum()<=0:
        raise ValueError("no positive core damage residual energy")
    weights /= weights.sum()
    center = np.sum(weights[:,None]*xy,axis=0)
    std = np.sqrt(np.sum(weights[:,None]*(xy-center)**2,axis=0))
    scale = np.minimum(original,np.maximum(original/4,3*std))
    return dict(rule=RULE,local_center=center.tolist(),local_scale=scale.tolist(),
        residual_std=std.tolist(),original_scale=original.tolist(),
        core_damage_error_energy_fraction=float(np.sum(energy[selected])/np.sum(energy[damage>.1])),
        coordinate_zoom=(original/scale).tolist(),teacher_target_used=True)


class CoordinateResidualUV(FrozenResidualUV):
    """Keep original physical geometry buffers; separate local coordinate buffers."""
    def __init__(self, backbone, residual, geometry, mapping):
        super().__init__(backbone,residual,"localized",geometry)
        if mapping.get("rule") != RULE:
            raise ValueError("coordinate rule identity")
        for name in ("local_center","local_scale"):
            value=torch.tensor(mapping[name],dtype=torch.float64)
            if value.shape!=(2,) or not torch.isfinite(value).all():raise ValueError("invalid local map")
            self.register_buffer(name,value)
        if torch.any(self.local_scale<self.scale/4) or torch.any(self.local_scale>self.scale):
            raise ValueError("coordinate zoom outside frozen bound")

    def components_physical(self,xy):
        coords=(xy-self.local_center)/self.local_scale
        window=compact_window(xy,self.lower,self.upper)
        return dict(global_raw=self.backbone(2*xy),local_raw=window*self.residual(coords),
                    window=window,local_coords=coords)

    def correction_physical(self,xy):
        coords=(xy-self.local_center)/self.local_scale
        factor=((xy[:,1]+.5)*(.5-xy[:,1]))[:,None]
        return factor*compact_window(xy,self.lower,self.upper)*self.residual(coords)
