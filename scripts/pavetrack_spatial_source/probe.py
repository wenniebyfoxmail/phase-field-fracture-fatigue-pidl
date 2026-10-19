"""Frozen-source array contracts and boundary-reference scoring; no torch."""
import importlib.util
from pathlib import Path
import numpy as np

s=importlib.util.spec_from_file_location('e027_old_metrics',Path(__file__).resolve().parent.parent/'pavetrack_translation_control/probe.py')
old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
component=old.component


def preprocess(rgb):
    a=np.asarray(rgb)
    if a.dtype!=np.uint8 or a.ndim!=3 or a.shape[0]!=3 or any(v%32 for v in a.shape[1:]):
        raise ValueError('native RGB CHW uint8/multiple32 required')
    # Official cv2 input is BGR, not RGB or ImageNet-normalized.
    return np.ascontiguousarray(a[::-1],dtype=np.float32)/255


def to32(p):
    if p.shape!=(128,128):raise ValueError('target cache grid')
    return p.reshape(32,4,32,4).mean((1,3))


def evaluate(cfd,masks,pave,regions,margin=1e-6):
    if cfd.shape!=(12,320,480) or masks.shape!=cfd.shape or pave.shape!=(16,128,128) or regions.shape!=(16,32,32):
        raise ValueError('fixed input scope')
    if masks.dtype!=np.uint8 or regions.dtype!=np.uint8 or set(np.unique(masks).tolist())!={0,1} or set(np.unique(regions).tolist())!={0,1}:
        raise ValueError('binary released reference')
    total=masks.astype(np.float64).sum(0);rows=[]
    for j,(p,y) in enumerate(zip(cfd,masks,strict=True)):
        if not 0<int(y.sum())<y.size:raise ValueError('reference support')
        # Baselines are GT-informed comparators, never prediction inputs.
        baselines=dict(zero=np.zeros_like(y,dtype=np.float32),one=np.ones_like(y,dtype=np.float32),
                       oracle_constant=np.full(y.shape,float(y.mean())),
                       leave_one_out_position=(total-y)/11,
                       fixed_identity_mismatch=cfd[(j+1)%12])
        correct=component(p,y);scores={n:component(v,y) for n,v in baselines.items()}
        gain=correct['Dice']-max(v['Dice'] for v in scores.values())
        rows.append(dict(index=j,correct=correct,baselines=scores,Dice_gain=gain,passed=bool(gain>margin),
                         Brier_gain=min(v['Brier'] for v in scores.values())-correct['Brier'],
                         pair_Dice_gain=correct['Dice']-scores['fixed_identity_mismatch']['Dice']))
    target=[]
    for j,(p,y) in enumerate(zip(pave,regions,strict=True)):
        values=component(to32(p),y)
        for key,new in [('Brier','envelope_Brier'),('Dice','envelope_Dice'),('TP','inside_envelope_predictions'),('FP','outside_envelope_predictions'),('FN','missed_envelope_cells')]:values[new]=values.pop(key)
        target.append(dict(index=j,**values,reference='region envelope; outside not verified negatives; descriptive only'))
    passed=sum(r['passed'] for r in rows)
    return dict(cfd=dict(rows=rows,passed_images=passed,primary_pass=bool(passed>=7),
                         mean_Dice=float(np.mean([r['correct']['Dice'] for r in rows])),
                         median_Dice=float(np.median([r['correct']['Dice'] for r in rows])),
                         mean_Brier=float(np.mean([r['correct']['Brier'] for r in rows])),
                         scope='released boundary reference on12 exposed development images only'),
                pavetrack=dict(rows=target,qualification=None,reference='partial region envelopes, no exact pixel truth'),
                level='L2' if passed>=7 else 'L1' if passed or any(r['Brier_gain']>margin or r['pair_Dice_gain']>margin for r in rows) else 'L0',
                OOF=None,net_GT=None,retention=None,selector=False)


def repeat_difference(first,second):
    if first.shape!=second.shape or first.dtype!=np.float32 or second.dtype!=np.float32 or not np.isfinite(first).all() or not np.isfinite(second).all() or (first<0).any() or (first>1).any() or (second<0).any() or (second>1).any():
        raise ValueError('probability arrays')
    return float(np.max(np.abs(first.astype(np.float64)-second)))
