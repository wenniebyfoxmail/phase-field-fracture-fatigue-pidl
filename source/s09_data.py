"""Dataset identity, train-only statistics, graph quadrature and diagnostic gates."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

CHANNELS = ['damage_clipped_0_1', 'alpha_bar_nonnegative',
            'fatigue_degradation_clipped_0_1', 'log10_peak_raw_tensile_driver']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def load_data(root, config):
    root = Path(root)
    manifest_path = root / 'RUN_MANIFEST.json'
    if sha256(manifest_path) != config['manifest_sha256']:
        raise ValueError('dataset manifest identity mismatch')
    m = json.loads(manifest_path.read_text())
    if m['dataset_id'] != 'hard5_loao_fem_states_v1' or m['state_channels'] != CHANNELS:
        raise ValueError('unexpected dataset/fields')
    ids = config['train_ids'] + config['development_ids']
    if len(ids) != len(set(ids)):
        raise ValueError('train/development overlap or duplicate trajectories')
    table = {x['trajectory_id']: x for x in m['trajectories']}
    trajectories = {}
    for tid in ids:
        row = table[tid]
        f = root / 'trajectories' / row['data_file']
        if sha256(f) != row['data_sha256']:
            raise ValueError(f'trajectory identity mismatch: {tid}')
        with np.load(f, allow_pickle=False) as a:
            s = a['states']
            cycles = a['cycles']
            if str(a['trajectory_id']) != tid or not np.array_equal(cycles, np.arange(1, len(s)+1)):
                raise ValueError('trajectory identity/cadence mismatch')
            if s.shape != (row['cycle_count'], 86408, 4) or not np.isfinite(s).all():
                raise ValueError('invalid state shape/finiteness')
            if (s[:, :, 0] < 0).any() or (s[:, :, 0] > 1).any() or (s[:, :, 1] < 0).any():
                raise ValueError('invalid constrained channel')
            if (np.diff(s[:, :, :2], axis=0) < 0).any():
                raise ValueError('reference violates proposed irreversible state; do not repair labels')
            trajectories[tid] = {'raw': s, 'cycles': cycles, 'umax': float(a['umax'])}
    # graph.npz contains old U0.12 state fields: deliberately never deserialize them.
    if sha256(root / 'graph.npz') != config['graph_sha256']:
        raise ValueError('graph identity mismatch')
    with np.load(root / 'graph.npz', allow_pickle=False) as a:
        mesh = {k: a[k] for k in ('centroids', 'areas', 'connectivity')}
    if not np.isfinite(mesh['centroids']).all() or not np.all(mesh['areas'] > 0):
        raise ValueError('invalid geometry/quadrature')
    return trajectories, mesh


def transform(raw, psi_scale):
    out = np.empty((*raw.shape[:-1], 3), dtype=np.float32)
    out[..., :2] = raw[..., :2]
    # logaddexp is stable even for extreme finite log10 inputs.
    out[..., 2] = np.logaddexp(0, raw[..., 3].astype(np.float64)*np.log(10)-np.log(psi_scale))
    return out


def statistics(trajectories, train_ids):
    # Deterministic spatial stride only for robust scales, never for loss/evaluation.
    samples = [trajectories[k]['raw'][:, ::64] for k in train_ids]
    psi_scale = float(10**np.median(np.concatenate([a[..., 3].ravel() for a in samples])))
    states = [transform(a, psi_scale).astype(np.float64) for a in samples]
    pooled = np.concatenate(states)
    mean = pooled.mean(axis=(0, 1)); scale = np.maximum(pooled.std(axis=(0, 1)), 1e-6)
    increments = np.concatenate([np.diff(a, axis=0).reshape(-1, 3) for a in states])
    inc = []
    for j in range(3):
        values = np.abs(increments[:, j]);values = values[values > 1e-8]
        inc.append(float(max(np.median(values) if len(values) else 0, 1e-6)))
    return {'psi_scale': psi_scale, 'state_mean': mean.tolist(), 'state_scale': scale.tolist(),
            'increment_scale': inc, 'source_ids': list(train_ids), 'statistics_spatial_stride': 64}


def weighted_abs(v, area):
    # Explicit reductions avoid platform BLAS warnings and large temporary matmul buffers.
    return np.sum(np.abs(v).astype(np.float64) * area, axis=-1) / np.sum(area)


def legal_origins(n, horizon=3):
    # zero-based origin; window contains origin-2,...,origin+horizon.
    return list(range(2, n-horizon))


def inventory(trajectories, area, config):
    tau = config['tau']
    rows = [];training_growth = [];p1_growth = [];p1_stagnant = []
    for tid, tr in trajectories.items():
        d = tr['raw'][..., 0]
        for origin in legal_origins(len(d)):
            g1 = float(weighted_abs(d[origin+1]-d[origin], area))
            g3 = float(weighted_abs(d[origin+3]-d[origin], area))
            row = {'trajectory_id':tid,'origin_index':origin,'origin_cycle':origin+1,
                   'damage_growth_1':g1,'damage_growth_3':g3,
                   'split':'train' if tid in config['train_ids'] else 'development'}
            rows.append(row)
            if row['split']=='train':
                if g3>tau: training_growth.append(g3)
                (p1_growth if g1>tau else p1_stagnant).append([tid,origin])
    if not training_growth or not p1_growth:
        raise ValueError('no identifiable training growth')
    def spaced(items,n):
        if not items:return []
        return [items[i] for i in np.linspace(0,len(items)-1,min(n,len(items)),dtype=int)]
    # Deterministic balanced windows; when true stagnant windows are absent use more growth,
    # not low-quantile relabelling or fabricated labels.
    selected = (spaced(p1_growth,8)+spaced(p1_stagnant,8)) if p1_stagnant else spaced(p1_growth,16)
    if len(selected)<16:
        selected += [x for x in spaced(p1_growth,16) if x not in selected][:16-len(selected)]
    return {'tau':tau,'g_ref':float(np.median(training_growth)), 'windows':rows,
            'p1_windows':selected,'p1_growth_available':len(p1_growth),
            'p1_stagnant_available':len(p1_stagnant),
            'claim_boundary':'processed archive imitation; no physical qualification'}


def build_graph(mesh, radius=.005, bins=16):
    xy = np.asarray(mesh['centroids'], dtype=np.float64)
    area = np.asarray(mesh['areas'], dtype=np.float64)
    # This family is a solid rectangular mesh with diffuse precrack; no void-crossing edges.
    neighbors = cKDTree(xy).query_ball_point(xy, radius, return_sorted=True)
    counts = np.fromiter(map(len, neighbors),dtype=np.int64)
    if int(counts.sum())>2_000_000:
        raise ValueError('local edge budget exceeded; amend graph contract, do not silently truncate')
    src = np.concatenate(neighbors).astype(np.int64);dst=np.repeat(np.arange(len(xy)),counts)
    weight = area[src] / (np.pi * radius**2)
    rel = (xy[src]-xy[dst])/radius
    rel = np.column_stack([rel,np.linalg.norm(rel,axis=1)])
    lo=xy.min(0);extent=np.maximum(xy.max(0)-lo,1e-12)
    lattice=np.minimum(((xy-lo)/extent*bins).astype(int),bins-1)
    _,cluster=np.unique(lattice[:,0]*bins+lattice[:,1],return_inverse=True)
    ca=np.bincount(cluster,weights=area)
    cx=np.column_stack([np.bincount(cluster,weights=area*xy[:,j])/ca for j in range(2)])
    cs=np.tile(np.arange(len(ca)),len(ca));cd=np.repeat(np.arange(len(ca)),len(ca))
    cr=(cx[cs]-cx[cd])/max(extent);cr=np.column_stack([cr,np.linalg.norm(cr,axis=1)])
    conn=mesh['connectivity']; sides=np.stack([conn,np.roll(conn,-1,axis=1)],-1).reshape(-1,2)
    _,inverse,freq=np.unique(np.sort(sides,axis=1),axis=0,return_inverse=True,return_counts=True)
    boundary=(freq[inverse].reshape(-1,4)==1).any(1).astype(np.float32)
    arrays={'xy':xy,'area':area,'boundary':boundary,'edges':np.stack([src,dst]),
            'relative':rel,'weight':weight,'cluster':cluster,'coarse_area':ca,
            'coarse_edges':np.stack([cs,cd]),'coarse_relative':cr,'coarse_weight':ca[cs]/ca.sum()}
    return {k:v.astype(np.int64 if k in ['edges','cluster','coarse_edges'] else np.float32) for k,v in arrays.items()}


def evaluate_damage(predictions, references, currents, area, tau, g_ref):
    growth = [];error=[];predicted=[];false_growth=[]
    for pred,ref,current in zip(predictions,references,currents):
        true_g=float(weighted_abs(ref-current,area));pg=float(weighted_abs(pred-current,area))
        if true_g>tau:
            growth.append(true_g);error.append(float(weighted_abs(pred-ref,area)));predicted.append(pg)
        else:false_growth.append(pg)
    if not growth:return {'verdict':'not_evaluable','growth_origins':0}
    r=sum(error)/sum(growth);ratio=sum(predicted)/sum(growth)
    growth_pass=r<=.95 and ratio>=.25
    false_max=max(false_growth) if false_growth else None;bound=.25*g_ref+2*tau
    passed=growth_pass and (false_max is None or false_max<=bound)
    return {'verdict':('pass' if false_growth else 'growth_only_pass') if passed else 'fail',
            'r3':r,'growth_ratio':ratio,'false_growth_max':false_max,'false_growth_bound':bound,
            'growth_origins':len(growth),'stagnant_origins':len(false_growth)}
