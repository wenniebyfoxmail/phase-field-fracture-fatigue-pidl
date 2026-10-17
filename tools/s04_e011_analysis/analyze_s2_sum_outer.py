#!/usr/bin/env python3
"""Exact stop-only prefix replay of observed strict-inner S2UJ states; no solves."""
import argparse
import datetime as dt
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize, SymLogNorm
from analyze_s2_isolation import sha, dump, table, jsonfile
from analyze_c1_commit import a, v, scalar, state, same
from run_multicycle_cross_replay import q4_geometry, amor_raw
from audit_phase_tangent import assemble
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient

PROTOCOL = 'S04-E011-S2SO-r1'
PRODUCER = '383a77827d3f60be6bcc0326c6923451df94a96d'


def rel(x, y):
    return float(np.max(abs(x-y)/np.maximum(1, abs(y))))


def limits(s, vv):
    return (4e-6 if s else 4e-4, 1e-8 if vv else 4e-4)


def first_stop(rows, s, vv):
    """Respect complete-block acceptance before exact-stagnation, like controller."""
    jt, ut = limits(s, vv)
    for r in rows:
        if r['outer'] < 1:
            continue
        if max((r['u_l2']+r['d_l2'])/jt, r['u_l2']/ut) <= 1:
            return r['outer'], 'policy_tolerance'
        if r['u_delta_max'] == r['d_delta_max'] == 0:
            return None, 'exact_stagnation'
    return None, 'unobserved_beyond_saved_horizon'


def selftest():
    def row(k, u, d, du=1, dd=1):
        return dict(outer=k, u_l2=u, d_l2=d, u_delta_max=du, d_delta_max=dd)
    # A mechanical-only acceptable initial state must not terminate at outer0.
    assert first_stop([row(0, 0, 0)], 0, 0)[0] is None
    # Separate branches: joint passes but outer u fails, then both pass.
    q = [row(1, 1e-7, 1e-6), row(2, 1e-9, 1e-6)]
    assert first_stop(q, 1, 0)[0] == 1 and first_stop(q, 0, 1)[0] == 2
    # Outer u passes but joint fails, then both pass.
    q = [row(1, 0, 1e-5), row(2, 0, 1e-6)]
    assert first_stop(q, 0, 1)[0] == 1 and first_stop(q, 1, 0)[0] == 2
    # Equality accepted; no made-up extension when actual horizon is exhausted.
    assert first_stop([row(1, 0, 4e-6)], 1, 1)[0] == 1
    assert first_stop([row(1, 1e-4, 1e-6)], 1, 1)[0] is None
    # Exact stagnation precedes later recorded states unless already accepted.
    q = [row(1, 1e-4, 1e-6, 0, 0), row(2, 0, 1e-6)]
    assert first_stop(q, 1, 1) == (None, 'exact_stagnation')
    assert first_stop([row(1, 0, 1e-6, 0, 0)], 1, 1)[0] == 1
    return dict(status='passed', groups=6)


def main(args):
    assert not args.out.exists(), 'Use a fresh analysis Run directory'
    args.out.mkdir(parents=True)
    out = args.out/'analysis'
    out.mkdir()
    root = args.source/'retrieved'
    code = Path(__file__).resolve()
    repo = code.parents[2]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
    ready = jsonfile(args.review)
    assert ready['status'] == 'passed' and ready['commit'] == commit
    assert ready['analysis_sha256'] == sha(code) and ready['protocol'] == PROTOCOL
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    dump(args.out/'run_receipt.json', dict(run_id=args.out.name, kind='offline_exact_stop_policy_replay',
         protocol=PROTOCOL, commit=commit, dirty=False, pid=os.getpid(), host=platform.node(),
         python=sys.executable, command=sys.argv, started_utc=started, source_run=str(args.source),
         source_producer_commit=PRODUCER, new_native_solve=False, remote_mutation=False))
    dump(out/'selftest.json', selftest())
    retrieval = jsonfile(args.source/'retrieval_verification.json')
    assert retrieval['all_hashes_and_sizes_match'] and retrieval['files'] == 97
    assert retrieval['bytes'] == 1716819024
    assert len(retrieval['manifest']) == retrieval['files']
    assert sum(t['bytes'] for t in retrieval['manifest']) == retrieval['bytes']
    for t in retrieval['manifest']:
        p = root/t['relative'].replace('\\', '/')
        assert p.stat().st_size == t['bytes'] and sha(p) == t['sha256']
    oldreview = jsonfile(args.source/'analysis/independent_review.json')
    assert oldreview['status'] == 'passed' and oldreview['producer_commit'] == PRODUCER
    manifest = jsonfile(root/'input_manifest.json')
    assert manifest['source_commit'] == PRODUCER
    inputs = {t['role']:root/'inputs'/Path(t['target'].replace('\\', '/')).name for t in manifest['staging']}
    for t in manifest['staging']:
        assert sha(inputs[t['role']]) == t['sha256']
    # The executed snapshot is immutable and independently reviewed. These
    # executable checks bind the manually reviewed stopping-only dataflow.
    texts = {p.name:p.read_text() for p in root.glob('*.m')}
    coupled = texts['e011_s2ra_coupled.m']
    stop = texts['e011_s2ra_stop.m']
    assert coupled.count('next.policy_pass') == 1
    assert 'if next.policy_pass,stop="policy_tolerance";break;end' in coupled
    assert 'if du==0 && dd==0,stop="exact_stagnation";break;end' in coupled
    assert 'ur/limits.outer_u_tol' in stop and '(ur+dr)/limits.joint_tol' in stop
    assert 'eligible=outer>=1 && value<=1' in stop
    for name in ['e011_s2ra_coupled.m', 'e011_s2ra_mechanical.m', 'e011_damage_solve.m', 'e011_s2uj_case.m']:
        assert 'joint_tol' not in texts[name] and 'outer_u_tol' not in texts[name]
    dump(out/'dataflow_certificate.json', dict(protocol=PROTOCOL, source_producer_commit=PRODUCER,
         reviewed_snapshot=str(root), threshold_consumption='Only e011_s2ra_stop -> complete-block exit',
         modules={k:sha(root/k) for k in texts}, independent_design_review=ready,
         prefix_invariance_scope='Same pre/start/predictor/inner settings/caps; no earlier nonpolicy exit'))
    with h5py.File(inputs['common']) as h:
        nodes=a(h, 'node_coords').T
        c=a(h, 'connectivity').T.astype(int)-1
        fu=v(h, 'free_dof_u').astype(int)-1
        fd=v(h, 'free_dof_d').astype(int)-1
    n=len(nodes)
    N,B,w,xy=q4_geometry(nodes,c)
    assert n == 86756 and len(c) == 86408
    with h5py.File(inputs['O1']) as h:
        pre=state(h['proposed'])
    with h5py.File(inputs['R1']) as h:
        rpre=state(h['proposed'])
    start=dict(u=pre['u'], d=np.maximum(pre['d'], rpre['d']))
    fixedu=np.setdiff1d(np.arange(2*n),fu)
    fixedd=np.setdiff1d(np.arange(n),fd)
    folder=root/'output/s2uj/U1J1'
    result=jsonfile(folder/'result.json')
    assert result['accepted'] and result['outer']==19 and result['history_commits']==0 and not result['fatal']
    with h5py.File(folder/'case.mat') as h:
        same(state(h['pre']),pre)
        same({k:v(h['start'],k) for k in ['u','d']},start)
        predictor={k:v(h['predictor'],k) for k in ['u','d','r']}
        assert scalar(h['out'],'history_commits')==0
        assert scalar(h['limits'],'u_tol')==1e-8 and scalar(h['limits'],'d_tol')==4e-6
    def audit(g):
        u=v(g,'u');d=v(g,'d');raw=a(g,'raw').T
        assert np.isfinite(u).all() and np.isfinite(d).all()
        assert np.all(d>=pre['lower']-1e-12) and np.all(d<=1+1e-12)
        assert np.array_equal(u[fixedu],predictor['u'][fixedu]) and np.array_equal(d[fixedd],start['d'][fixedd])
        expected=amor_raw(u[:n],u[n:],c,B)
        rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n)
        ru=mechanics_force(u,d,c,N,B,w,n)
        hh=np.stack([t['alpha'],t['active'],t['f']],axis=2)
        errs=dict(raw=rel(raw,expected), residual=max(rel(rd,v(g,'rd')),rel(ru,v(g,'ru'))), history=rel(hh,a(g,'history234').transpose(2,1,0)))
        assert max(errs.values()) <= 1e-10 and np.all(t['f']==1)
        ur=float(np.linalg.norm(ru[fu]));dr=float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])))
        assert abs(ur-scalar(g,'u_l2')) <= 1e-12 and abs(dr-scalar(g,'d_feasible_l2')) <= 1e-12
        return u,d,t['active'],ur,dr,errs
    with h5py.File(inputs['scale_reference']) as h:
        same(state(h['pre']),pre)
        same({k:v(h['start'],k) for k in ['u','d']},start)
        same({k:v(h['predictor'],k) for k in ['u','d','r']},predictor)
        _,_,parent,_,_,perr=audit(h['current'])
        parent_norm=float(np.sum(w*parent**2))
    fields={};rows=[];previous=None
    files=sorted(folder.glob('outer_*.mat'))
    assert [int(p.stem.split('_')[1]) for p in files]==list(range(20))
    for k,p in enumerate(files):
        with h5py.File(p) as h:
            g=h['point'];assert scalar(g,'outer')==k
            u,d,field,ur,dr,errs=audit(g)
            cc=g['controls'];ll=cc['limits']
            assert scalar(cc,'U')==scalar(cc,'J')==scalar(cc,'refresh')==1
            for key,value in dict(u_tol=1e-8,d_tol=4e-6,joint_tol=4e-6,outer_u_tol=1e-8,max_u=248,max_d=248,max_outer=20).items():
                assert scalar(ll,key)==value
            cu=int(scalar(h['calls'],'u'));cd=int(scalar(h['calls'],'d'))
            assert cu+1<=250 and cd<=250
            if k:
                pp=g['phase_input']
                assert np.array_equal(v(pp,'d_before'),previous[1])
                assert np.array_equal(v(pp,'u_returned'),u) and np.array_equal(v(pp,'u_evaluated'),u)
                assert scalar(pp,'cached_u_residual_l2')<1e-8
                assert previous[2]<=245 and previous[3]<=245
                du=float(np.max(abs(u-previous[0])));dd=float(np.max(abs(d-previous[1])))
            else:
                assert np.array_equal(u,predictor['u']) and np.array_equal(d,start['d'])
                du=dd=None
            r=dict(outer=k,u_l2=ur,d_l2=dr,u_delta_max=du,d_delta_max=dd,
                   u_calls_including_cache=cu+1,phase_calls=cd,active_integral=float(np.sum(w*field)),
                   raw_scaled_error=errs['raw'],residual_scaled_error=errs['residual'],history_scaled_error=errs['history'])
            for s,vv in [(0,0),(1,0),(0,1),(1,1)]:
                jt,ut=limits(s,vv);key=f'S{s}V{vv}'
                r[key+'_sum_component']=(ur+dr)/jt;r[key+'_u_component']=ur/ut
                r[key+'_eligible']=bool(k>=1 and max((ur+dr)/jt,ur/ut)<=1)
                r[key+'_sum_margin']=jt-(ur+dr);r[key+'_u_margin']=ut-ur
            rows.append(r);fields[k]=field;previous=(u,d,cu,cd)
            print('AUDITED',k,ur,dr,flush=True)
    # Independently executed loose-policy anchor must be identical in all state channels.
    with h5py.File(root/'output/s2uj/U1J0/case.mat') as anchor, h5py.File(folder/'outer_01.mat') as first:
        same(state(anchor['pre']),pre);same({k:v(anchor['start'],k) for k in ['u','d']},start)
        same({k:v(anchor['predictor'],k) for k in ['u','d','r']},predictor)
        for key in ['u','d','raw','ru','rd','history234']:
            assert np.array_equal(a(anchor['current'],key),a(first['point'],key))
    chosen=[];endpoint={};policy_fields={}
    base_norm=float(np.sum(w*fields[1]**2))
    for s,vv in [(0,0),(1,0),(0,1),(1,1)]:
        key=f'S{s}V{vv}';k,reason=first_stop(rows,s,vv)
        endpoint[key]=k
        if k is None:
            chosen.append(dict(policy=key,first_outer=None,status=reason));continue
        r=rows[k];jt,ut=limits(s,vv);policy_fields[key]=fields[k]
        chosen.append(dict(policy=key,joint_tol=jt,outer_u_tol=ut,first_outer=k,status='derived_policy_endpoint',
             u_l2=r['u_l2'],d_l2=r['d_l2'],sum_component=(r['u_l2']+r['d_l2'])/jt,u_component=r['u_l2']/ut,
             u_calls_including_cache=r['u_calls_including_cache'],phase_calls=r['phase_calls'],
             active_integral=r['active_integral'],source_point=str(folder/f'outer_{k:02d}.mat')))
    contrasts=[]
    for label,left,right in [('S_at_V0','S0V0','S1V0'),('S_at_V1','S0V1','S1V1'),('V_at_S0','S0V0','S0V1'),('V_at_S1','S1V0','S1V1'),('diagonal','S0V0','S1V1')]:
        if left not in policy_fields or right not in policy_fields:continue
        gap=policy_fields[right]-policy_fields[left];sq=float(np.sum(w*gap**2));ij=np.unravel_index(np.argmax(abs(gap)),gap.shape)
        contrasts.append(dict(contrast=label,left=left,right=right,parent_relative_L2=float(np.sqrt(sq/parent_norm)),
          baseline_relative_L2=float(np.sqrt(sq/base_norm)),weighted_squared_gap=sq,signed_integral=float(np.sum(w*gap)),
          wake_squared_share=float(np.sum((w*gap**2)[xy[:,:,0]<=0])/sq) if sq else None,
          max_abs_gap=float(abs(gap[ij])),x=float(xy[ij][0]) if sq else None,y=float(xy[ij][1]) if sq else None))
    for r in rows:r['active_gap_to_first_parent_relative_L2']=float(np.sqrt(np.sum(w*(fields[r['outer']]-fields[1])**2)/parent_norm))
    table(out/'policies.csv',chosen);table(out/'crossings.csv',rows);table(out/'contrasts.csv',contrasts)
    summary=dict(protocol=PROTOCOL,run_id=args.out.name,analysis_commit=commit,analysis_sha256=sha(code),
      source_run=str(args.source),source_producer_commit=PRODUCER,retrieval_files=97,retrieval_bytes=retrieval['bytes'],
      new_native_solve=False,policy_class='offline exact stop-only prefix endpoints, not four fresh producer arms',
      endpoints=endpoint,policies=chosen,contrasts=contrasts,history_commits=0,f_min=1,
      parent_squared_norm=parent_norm,new_baseline_squared_norm=base_norm,parent_replay_errors=perr,
      max_replay_errors={k:max(r[k] for r in rows) for k in ['raw_scaled_error','residual_scaled_error','history_scaled_error']},
      independently_replayed_source_points=len(rows),anchor_first_block_bitwise_equal=True,
      interpretation='Two individual stopping gates are redundantly sufficient on this observed strict-inner path; no unique main gate or physical contribution split.' if endpoint=={'S0V0':1,'S1V0':19,'S0V1':19,'S1V1':19} else 'Inspect derived endpoints; no presupposed winner.',
      limitations=['One fixed synthetic c1s2, frozen history/f1; no physical/teacher/multicycle qualification',
                   'Policies select actual observed prefixes; no new native producer arms or extrapolation',
                   'Redundancy here is not proof either gate can be removed elsewhere',
                   'L2 field differences are not additive causal percentages; no 50/50 physical attribution'])
    dump(out/'s2so_analysis.json',summary)
    draw(out,nodes,c,w,fields,rows,chosen,contrasts,args.out.name)
    (out/'README_analysis.md').write_text('# c1s2: joint sum versus outer-u stopping\n\nQuestion: fixed fresh/constrained/strict inneru1e-8 and innerd4e-6, separate the two outer stopping thresholds.\n\nEvidence: '+str(args.source)+'; actual native producer '+PRODUCER+'. All97files verified again. Twenty actual strict-inner points outer0..19 independently recomputed with native Q4/2x2GP operators and frozen O1 history. U1J0 first-block state exactly matches U1J1 outer1. New analysis is offline stop-only replay, not four fresh FEM runs.\n\nRead s2so_decision.png for separate thresholds, first crossing and conditional contrasts; s2so_fields.png for actual outer1/19 maps and their signed difference. Policies/crossings/contrasts.csv and s2so_analysis.json are authoritative. Scalar metrics use unaveraged GP/Jacobian weights; plotted fields use weighted Q4 cell means. Both original parent and new baseline norms are retained.\n\nStop thresholds only enter complete-block acceptance, not updates. Prefix invariance applies until first eligible stopping point or an original nonpolicy exit. No initial acceptance, new solve, history commit, absent state interpolation or budget increase.\n\nInterpretation: use actual policy endpoints. If both singleton gates reproduce the strict endpoint, neither can be named the unique driver. Their effects overlap; do not add the two conditional L2 values or assign50/50 physical contributions.\n\nAllowed conclusion: bounded numerical stopping-policy sensitivity in this single synthetic c1s2. Blocked: physical validity, unique equilibrium, teacher, c83/trajectory or universal gate deletion. Next: retain both fresh joint checks with compatible strict inner tolerances; use separately reviewed early/late states for transfer. Spatial/Carrara alignment leaves committed-f/trial-f and Deep-Ritz/staggered differences.\n')
    for leaf in ['s2so_decision','s2so_fields']:
        (out/(leaf+'.md')).write_text('# '+leaf+'\n\nQuestion: separate jointsum and outeru stop thresholds with strict inner tolerances.\n\nSource: '+str(args.source)+'; producer '+PRODUCER+'; offline analysis '+args.out.name+' commit '+commit+'. Exact s2so_analysis.json and policies/crossings/contrasts.csv; no new solve.\n\nDecision panels: top left shows normalized strict sum/u components against1 at every actual complete outer; top right gives first derived stop for all four policies. Bottom left gives conditional native GP weighted field gap in percent of original S2DJ00 norm; zero bars explicitly marked. Bottom right shows active integral along observed complete blocks. Outer index is numerical iteration, not physical time.\n\nField panels: original native outer1 field, native outer19 field selected by both singleton and both-tight policies, signed19-minus1 gap. Two absolute maps share log10 colour limits/floor1e-12; signed gap uses symmetric symlog. Q4/Jacobian weighted cell means for display only; scalar gap metrics use unaveraged GP. Coordinates are native x/y.\n\nTakeaway and limitation: read exact endpoint/contrast table. Coincident first crossings support redundant sufficient restrictions only on this path, not a uniquely dominant gate or50/50 physical split. One fixed synthetic c1s2/frozen history/f1; no new Windows arms, physical teacher or multicycle claim.\n')
    dump(args.out/'completion.json',dict(status='completed',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),new_native_solve=False))
    print(json.dumps(summary,indent=2))


def draw(out,nodes,c,w,fields,rows,policies,contrasts,runid):
    q=[r for r in rows if r['outer']>=1];x=[r['outer'] for r in q]
    fig,axs=plt.subplots(2,2,figsize=(13,8))
    axs[0,0].semilogy(x,[(r['u_l2']+r['d_l2'])/4e-6 for r in q],'.-',label='strict joint sum / 4e-6')
    axs[0,0].semilogy(x,[r['u_l2']/1e-8 for r in q],'.-',label='strict outer u / 1e-8')
    firstsum=next((r['outer'] for r in q if r['u_l2']+r['d_l2']<=4e-6),None)
    firstu=next((r['outer'] for r in q if r['u_l2']<=1e-8),None)
    axs[0,0].axhline(1,color='black',ls='--');axs[0,0].set_title(f'First strict pass: sum outer{firstsum}, u outer{firstu}');axs[0,0].set_ylabel('Normalized stopping component (log)');axs[0,0].legend(fontsize=8)
    axs[0,1].bar([r['policy'] for r in policies],[r['first_outer'] or 0 for r in policies])
    for i,r in enumerate(policies):axs[0,1].text(i,(r['first_outer'] or 0)+.4,str(r['first_outer']),ha='center')
    axs[0,1].set_ylim(0,22);axs[0,1].set_ylabel('First eligible complete outer');axs[0,1].set_title('Four offline policies; no new FEM runs')
    vals=[100*r['parent_relative_L2'] for r in contrasts];axs[1,0].bar(range(len(vals)),vals)
    axs[1,0].set_xticks(range(len(vals)),[r['contrast'].replace('_at_','\nat ') for r in contrasts],fontsize=9)
    for i,z in enumerate(vals):axs[1,0].text(i,z+1,f'{z:.2f}%',ha='center',fontsize=9)
    axs[1,0].set_ylim(0,max(vals+[1])*1.22);axs[1,0].set_ylabel('Active weighted L2 gap / parent norm (%)');axs[1,0].set_title('Overlapping effects; do not sum as contributions')
    axs[1,1].plot(x,[r['active_integral'] for r in q],'.-');axs[1,1].set_title('Observed native active integral');axs[1,1].set_ylabel('GP/Jacobian integral')
    for ax in [axs[0,0],axs[1,1]]:ax.set_xlabel('Complete outer (not physical time)')
    fig.suptitle('Synthetic FEM c1s2 | fresh/constrained/strict inner u,d | '+runid,fontsize=9);fig.tight_layout();fig.savefig(out/'s2so_decision.png',dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,4.8));gap=fields[19]-fields[1]
    logs=[np.log10(np.maximum(np.sum(w*fields[k],axis=1)/w.sum(1),1e-12)) for k in [1,19]]
    absolute=Normalize(-12,max(float(z.max()) for z in logs))
    pc=None
    selected={k:' / '.join(r['policy'] for r in policies if r['first_outer']==k) or 'No policy selects' for k in [1,19]}
    for ax,z,title in zip(axs[:2],logs,[selected[k]+f' | native outer{k}' for k in [1,19]]):
        pc=PolyCollection(nodes[c],array=z,norm=absolute,cmap='viridis',edgecolors='none');ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(title,fontsize=10)
    cell=np.sum(w*gap,axis=1)/w.sum(1);vm=float(abs(cell).max())
    dc=PolyCollection(nodes[c],array=cell,norm=SymLogNorm(max(vm*.001,1e-15),vmin=-vm,vmax=vm),cmap='RdBu_r',edgecolors='none');axs[2].add_collection(dc);axs[2].autoscale();axs[2].set_aspect('equal');axs[2].set_title('Signed native outer19 - outer1',fontsize=10)
    for ax in axs:ax.set_xlabel('native x');ax.set_ylabel('native y')
    fig.colorbar(pc,ax=list(axs[:2]),label='log10 active cell mean (floor1e-12)',shrink=.75)
    fig.colorbar(dc,ax=axs[2],label='Signed active cell gap (symlog)',shrink=.75)
    fig.suptitle('Exact observed fields selected by stop-only replay | '+runid,fontsize=9);fig.savefig(out/'s2so_fields.png',dpi=165,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--review',type=Path);ap.add_argument('--selftest',action='store_true');args=ap.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    else:
        assert args.source and args.out and args.review
        main(args)
