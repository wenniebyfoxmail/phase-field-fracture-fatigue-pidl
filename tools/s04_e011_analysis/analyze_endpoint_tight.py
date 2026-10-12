#!/usr/bin/env python3
"""Compare accepted c83 tight-control endpoints with verified baseline and PIDL."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import h5py
import matplotlib.pyplot as plt
import numpy as np
from run_multicycle_cross_replay import q4_geometry, interp, amor_raw, comp


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def endpoint(path, state_key, oracle_key, n, cells, shape, deriv, weights):
    with h5py.File(path) as h:
        state = h[state_key]; oracle = h[oracle_key]
        uv=np.asarray(state['displ']).reshape(-1); d=np.asarray(state['p_field']).reshape(-1)
        raw=np.asarray(state['strain_en_undgr']).T
        ru=np.asarray(oracle['R_u_free']).reshape(-1); rd=np.asarray(oracle['R_d_free']).reshape(-1)
        idx=np.asarray(oracle['free_dof_d']).reshape(-1).astype(int)-1
        lower=np.asarray(h['frozen/p_field_old']).reshape(-1)
        history=np.asarray(h['frozen/history_vars_old'])
        load=np.asarray(h['frozen/load_factor'])
        iteration=None if state_key=='converged' else int(np.asarray(h['metrics/iteration']).item())
    for a in (uv,d,raw,ru,rd,lower):
        if not np.all(np.isfinite(a)): raise ValueError('Nonfinite native data: '+str(path))
    if uv.size!=2*n or d.size!=n: raise ValueError('Node identity/size mismatch')
    if np.any(d<lower-1e-12) or np.any(d>1+1e-12): raise ValueError('Damage bounds mismatch')
    projected=rd.copy(); lo=d[idx]<=lower[idx]+1e-10; hi=d[idx]>=1-1e-10
    projected[lo]=np.minimum(projected[lo],0);projected[hi]=np.maximum(projected[hi],0);projected[lo&hi]=0
    replay_raw=amor_raw(uv[:n],uv[n:],cells,deriv)
    raw_rel=float(np.sqrt(np.sum(weights*(raw-replay_raw)**2)/np.sum(weights*raw**2)))
    if raw_rel>1e-10: raise ValueError('Native GP raw/common operator mismatch')
    active=raw*(1-interp(d,cells,shape))**2
    return {'uv':uv,'d':d,'active':active,'lower':lower,'history':history,'load':load,'iteration':iteration,'raw_replay_relative_l2':raw_rel,
            'ru_l2':float(np.linalg.norm(ru)),'feasible_d_l2':float(np.linalg.norm(projected)),
            'raw_d_l2':float(np.linalg.norm(rd))}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--mesh',type=Path,required=True);ap.add_argument('--pidl',type=Path,required=True)
    args=ap.parse_args(); out=args.run/'analysis';out.mkdir(exist_ok=True); data=args.run/'retrieved'
    result=json.loads((data/'tight_result.json').read_text(encoding='utf-8-sig'))
    baseline_result=json.loads((data/'result.json').read_text(encoding='utf-8-sig'))
    if not baseline_result['baseline_pass']: raise ValueError('Baseline not admitted')
    with h5py.File(args.mesh) as h:
        points=np.asarray(h['node_coords']).T;cells=np.asarray(h['connectivity_q4']).T.astype(int)-1
    shape,deriv,w,xy=q4_geometry(points,cells);n=len(points)
    with np.load(args.pidl) as z:
        top=z['topology'].reshape(-1)[0];top=top.decode() if isinstance(top,bytes) else str(top)
        if top!='q4': raise ValueError('PIDL topology mismatch')
        i=np.flatnonzero(z['cycles']==83)
        if len(i)!=1 or int(z['steps'][i[0]])!=414: raise ValueError('PIDL state mismatch')
        if not np.allclose(z['node_coords'],points,atol=2e-8,rtol=0): raise ValueError('Coordinates mismatch')
        i=int(i[0]); pd=z['d_node'][i];pu=z['u_node'][i];pv=z['v_node'][i]
    if not all(np.all(np.isfinite(a)) for a in (pd,pu,pv)): raise ValueError('Nonfinite PIDL fields')
    pidl_active=amor_raw(pu,pv,cells,deriv)*(1-interp(pd,cells,shape))**2
    b=endpoint(data/'baseline_endpoint.mat','converged','oracle',n,cells,shape,deriv,w)
    paths=[data/'baseline_endpoint.mat']+sorted(data.glob('tight_outer_*.mat'))
    if len(paths)-1!=result['completed_extra_iterations']: raise ValueError('Endpoint count mismatch')
    rows=[]
    for i,path in enumerate(paths):
        if i and path.name!=f'tight_outer_{i:02d}.mat': raise ValueError('Noncontiguous extra endpoint files')
        e=b if i==0 else endpoint(path,'candidate','candidate_oracle',n,cells,shape,deriv,w)
        if i and e['iteration']!=20+i: raise ValueError('Iteration label mismatch')
        if not all(np.array_equal(e[k],b[k]) for k in ('lower','history','load')): raise ValueError('Predecessor changed')
        active_delta=comp(b['active'],e['active'],w);gap=comp(e['active'],pidl_active,w)
        row={'extra_iteration':i,'outer_iteration':20+i,'ru_l2':e['ru_l2'],
             'feasible_d_l2':e['feasible_d_l2'],'projected_sum':e['ru_l2']+e['feasible_d_l2'],
             'raw_d_l2':e['raw_d_l2'],'raw_replay_relative_l2':e['raw_replay_relative_l2'],
             'uv_relative_change':float(np.linalg.norm(e['uv']-b['uv'])/np.linalg.norm(b['uv'])),
             'damage_relative_change':float(np.linalg.norm(e['d']-b['d'])/np.linalg.norm(b['d'])),
             'uv_max_abs_change':float(np.max(np.abs(e['uv']-b['uv']))),
             'damage_max_abs_change':float(np.max(np.abs(e['d']-b['d']))),
             'active_relative_change':active_delta['relative_l2'],
             'active_gap_weighted_l2':float(np.sqrt(np.sum(w*(pidl_active-e['active'])**2))),
             'active_gap_relative_to_baseline_fem':float(np.sqrt(np.sum(w*(pidl_active-e['active'])**2)/np.sum(w*b['active']**2))),
             'active_integral':gap['fem_integral'],'pidl_integral':gap['pidl_integral'],
             'pidl_over_fem_integral':gap['pidl_over_fem'],'active_gap_relative_l2':gap['relative_l2'],
             'active_gap_correlation':gap['correlation']}
        rows.append(row)
    with (out/'metrics.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    final=rows[-1];initial=rows[0]
    summary={'schema':'c83-tight-control-sensitivity-v1','status':result['status'],
        'history_commits':result['history_commits'],'completed_extra_iterations':len(rows)-1,
        'state_labels':{'FEM':'c83s4 peak, fully completed outer iterate; screen convergence recorded separately; frozen accepted c83s3 history; zero history commits',
                        'PIDL':'original paired Q4 cycle83 peak model step414; unchanged'},
        'residual_ratio':final['projected_sum']/initial['projected_sum'],
        'active_gap_ratio':final['active_gap_relative_l2']/initial['active_gap_relative_l2'],
        'active_gap_absolute_norm_ratio':final['active_gap_weighted_l2']/initial['active_gap_weighted_l2'],
        'baseline':initial,'last_completed':final,'rows':rows,
        'provenance':{str(p):digest(p) for p in paths+[args.mesh,args.pidl,data/'tight_result.json',data/'result.json']},
        'scope':'combined inner accuracy and fresh nodal-monotone outer monitoring; descriptive numerical sensitivity, not teacher or physical validity'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(10,4));x=[r['outer_iteration'] for r in rows]
    for key,label in [('ru_l2','free displacement'),('feasible_d_l2','feasible damage'),('projected_sum','sum')]:
        axes[0].semilogy(x,[r[key] for r in rows],'-o',label=label)
    axes[0].axhline(4e-6,color='gray',linestyle='--',label='new absolute screen');axes[0].set_ylabel('native residual L2');axes[0].legend(fontsize=8)
    axes[1].plot(x,[r['active_gap_relative_l2'] for r in rows],'-o',color='#0072B2');axes[1].set_ylabel('Q4 PIDL vs FEM weighted active relative L2')
    for ax in axes:ax.set_xlabel('outer iteration (20 = original baseline)');ax.grid(alpha=.25)
    fig.suptitle('c83s4 bounded solver-control sensitivity: '+result['status']);fig.tight_layout();fig.savefig(out/'endpoint_tight_comparison.png',dpi=200);plt.close(fig)
    note=f'''# c83 endpoint solver-control comparison\n\nQuestion: does bounded refinement change residuals and the original paired PIDL field gap?\n\nData provenance: run {args.run}; source endpoint SHA256s and exact PIDL/mesh hashes are in summary.json. FEM baseline is original20-iteration c83s4 endpoint reproduced from accepted s3. Every plotted point is a fully completed extra outer endpoint; failed inner trial is excluded. PIDL is unchanged original Q4 c83 step414.\n\nHow to read: left panel shows native free displacement, nodal-monotone feasible damage and sum (log residual L2); dashed4e-6 is a numerical sensitivity screen, not physical qualification. Right: native Q4 GP4 weighted active-field relative L2, FEM denominator, vs unchanged PIDL. x=20 denotes verified baseline.\n\nOutcome: {result['status']}; completed extra iterations {len(rows)-1}. Projected residual ratio {summary['residual_ratio']:.8g}, active-gap ratio {summary['active_gap_ratio']:.8g}; baseline active-gap {initial['active_gap_relative_l2']:.8g}, final {final['active_gap_relative_l2']:.8g}. Fixed baseline-denominator absolute gap norm ratio {summary['active_gap_absolute_norm_ratio']:.8g}. Exact integral/correlation and nodal changes are in summary.json and metrics.csv.\n\nLimitations and claim boundary: combined inner accuracy and monitor sensitivity at this one peak state; frozen accepted predecessor, no history commits. Nodal projection is not a GP-constrained KKT or fatigue fixed-point certificate. A failure/cap cannot establish a tighter converged endpoint. No claim that this removes fixed committed-f/trial-f or joint Deep-Ritz/staggered algorithm differences.\n'''
    (out/'endpoint_tight_comparison.md').write_text(note);(out/'README_analysis.md').write_text(note)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('provenance','rows')},indent=2))

if __name__=='__main__':main()
