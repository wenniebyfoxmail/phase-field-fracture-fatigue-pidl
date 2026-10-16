#!/usr/bin/env python3
"""E029 table-only background centre influence; no width/pixel/error inputs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import numpy as np
from d01_nearfield_correspondence import inside_hull,candidates
from d01_t1_local_audit import read_csv
from d01_conditional_interface import dump_new,write_csv

STAGES=(1,2,3)
SUPPORTS=('all_available','flags_clear')


def fit_center(points,displacements):
    p=np.asarray(points,float).reshape(-1,2);d=np.asarray(displacements,float).reshape(-1,2)
    if len(p)!=len(d) or not np.isfinite(p).all() or not np.isfinite(d).all():raise ValueError('finite paired background data required')
    result=dict(support=len(p),available=False,reason='insufficient_support',rank=None,condition=None,inside_hull=False,n=None,t=None)
    if len(p)<4:return result,None
    X=np.column_stack((np.ones(len(p)),p[:,0]/55,p[:,1]/36));rank=int(np.linalg.matrix_rank(X));cond=float(np.linalg.cond(X))
    interior=inside_hull(p,(0,0));result.update(rank=rank,condition=cond,inside_hull=interior)
    if rank!=3 or not np.isfinite(cond) or cond>100:result['reason']='rank_or_condition';return result,None
    coef=np.linalg.lstsq(X,d,rcond=None)[0]
    if not np.isfinite(coef).all():raise ValueError('nonfinite fitted coefficients')
    w=np.linalg.pinv(X)[0];h=np.diag(X@np.linalg.pinv(X));res=d-X@coef
    info=dict(weights=w,leverage=h,residual=res)
    if not interior:result['reason']='centre_outside_hull';return result,info
    result.update(available=True,reason='centre_interpolation',n=float(coef[0,0]),t=float(coef[0,1]))
    return result,info


def analyze_pool(rows):
    points=np.array([[float(r['n']),float(r['t'])] for r in rows]);d=np.array([[float(r['dn']),float(r['dt'])] for r in rows])
    full,info=fit_center(points,d);loos=[];weights=[]
    for i,r in enumerate(rows):
        keep=np.arange(len(rows))!=i;out,_=fit_center(points[keep],d[keep])
        valid=bool(full['available'] and out['available'])
        delta_n=out['n']-full['n'] if valid else None;delta_t=out['t']-full['t'] if valid else None
        influence=(-float(info['weights'][i]*info['residual'][i,1]/(1-info['leverage'][i]))
                   if info is not None and abs(1-info['leverage'][i])>1e-12 else None)
        error=delta_t-influence if valid and influence is not None else None
        if error is not None and abs(error)>1e-10:raise ValueError('LOO influence identity mismatch')
        loos.append(dict(left_out=r['anchor_id'],remaining_ids=';'.join(x['anchor_id'] for k,x in enumerate(rows) if k!=i),removed_flags_clear=r['flags_clear']=='True',support=out['support'],
            available=valid,reason=out['reason'] if full['available'] else 'full_unavailable',rank=out['rank'],condition=out['condition'],inside_hull=out['inside_hull'],
            n=out['n'],t=out['t'],delta_n=delta_n,delta_t=delta_t,influence_t=influence,influence_identity_error=error))
        weights.append(dict(anchor_id=r['anchor_id'],weight=float(info['weights'][i]) if info is not None else None,
            leverage=float(info['leverage'][i]) if info is not None else None,residual_t=float(info['residual'][i,1]) if info is not None else None))
    return full,loos,weights


def temporal_pairs(fulls,loos):
    output=[]
    for support in SUPPORTS:
        for a,b in ((1,2),(2,3)):
            ra={r['left_out']:r for r in loos if r['support_name']==support and r['stage_index']==a}
            rb={r['left_out']:r for r in loos if r['support_name']==support and r['stage_index']==b}
            fa=next(r for r in fulls if r['support_name']==support and r['stage_index']==a)
            fb=next(r for r in fulls if r['support_name']==support and r['stage_index']==b)
            for aid in sorted(set(ra)&set(rb)):
                x,y=ra[aid],rb[aid];good=x['available'] and y['available']
                full=fb['t']-fa['t'] if fa['available'] and fb['available'] else None
                loo=y['t']-x['t'] if good else None;change=loo-full if good else None
                error=change-(y['delta_t']-x['delta_t']) if good else None
                if good and abs(error)>1e-10:raise ValueError('relative shift identity mismatch')
                output.append(dict(support_name=support,stage_a=a,stage_b=b,left_out=aid,available=good,
                    full_delta_t=full,loo_delta_t=loo,change_delta_t=change,identity_error=error,
                    reason='ok' if good else 'endpoint_unavailable'))
    return output


def summarize(fulls,loos,pairs):
    stages=[];transitions=[]
    for f in fulls:
        rr=[r for r in loos if r['support_name']==f['support_name'] and r['stage_index']==f['stage_index']];good=[r for r in rr if r['available']]
        stages.append(dict(stage_index=f['stage_index'],support_name=f['support_name'],opportunities=len(rr),valid=len(good),
            loo_t_min=min((r['t'] for r in good),default=None),loo_t_max=max((r['t'] for r in good),default=None),
            max_abs_delta_t=max((abs(r['delta_t']) for r in good),default=None),
            median_delta_t=float(np.median([r['delta_t'] for r in good])) if good else None))
    for support in SUPPORTS:
        for a,b in ((1,2),(2,3)):
            rr=[r for r in pairs if (r['support_name'],r['stage_a'],r['stage_b'])==(support,a,b)];good=[r for r in rr if r['available']]
            transitions.append(dict(support_name=support,stage_a=a,stage_b=b,opportunities=len(rr),valid=len(good),
                max_abs_change=max((abs(r['change_delta_t']) for r in good),default=None)))
    return dict(by_stage=stages,by_transition=transitions,role='background_only_viewed_development',physical_accuracy_validated=False,
        widths_read=False,old_scores_modified=False)


def validated_rows(rows):
    expected={r['anchor_id']:r for r in candidates()};accepted=set(expected)-{'N05','N09','N10'};seen=set();out=[]
    if len(rows)!=60:raise ValueError('expected60 source rows')
    for r in rows:
        j=int(r['stage_index']);aid=r['anchor_id'];key=(j,aid)
        if j not in STAGES or aid not in expected or key in seen:raise ValueError('source identity duplicate/invalid')
        seen.add(key)
        if float(r['load_kN'])!=(30,40,50)[j-1] or (float(r['n']),float(r['t']))!=(expected[aid]['n'],expected[aid]['t']):raise ValueError('load/coordinate mismatch')
        if any(r[k] not in ('True','False') for k in ('available','flags_clear','origin_accepted')):raise ValueError('malformed source boolean')
        good=r['available']=='True'
        if good!=(aid in accepted) or (r['origin_accepted']=='True')!=good:raise ValueError('source support changed')
        if good:
            if not np.isfinite([float(r[k]) for k in ('dn','dt','old_dn','old_dt')]).all():raise ValueError('nonfinite source displacement')
            if (r['flags_clear']=='True')!=(not r['flags']):raise ValueError('quality flag mismatch')
            out.append(r)
    for j,count in zip(STAGES,(8,6,5)):
        if sum(r['stage_index']==str(j) and r['flags_clear']=='True' for r in out)!=count:raise ValueError('quality support changed')
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean committed source required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E029-D01',run_id='S03-E029-D01-R001',protocol='T1-background-center-LOO-v1',
        code_commit=git('rev-parse','HEAD'),git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),python=sys.executable,command=sys.argv,
        started_utc=datetime.now(timezone.utc).isoformat(),execution='running',retrieval='pending',gpu=None,budget_seconds=60)
    try:
        source=json.loads((a.source/'runtime_receipt.json').read_text())
        if source['execution']!='succeeded' or source['code_commit']!='65e424d1f7b71b4080473853d246b8c14ee74669' or source['protocol']!='near-background-v1':raise ValueError('source receipt changed')
        rows=read_csv(a.source/'correspondences.csv');pool=validated_rows(rows);references=read_csv(a.source/'field_diagnostics.csv')
        if len(references)!=6 or len({(int(r['stage_index']),r['support_name']) for r in references})!=6:raise ValueError('fullfield reference identity')
        fulls=[];loos=[];weights=[]
        for j in STAGES:
            for support in SUPPORTS:
                selected=[r for r in pool if int(r['stage_index'])==j and (support=='all_available' or r['flags_clear']=='True')]
                f,ll,ww=analyze_pool(selected);ref=next(r for r in references if int(r['stage_index'])==j and r['support_name']==support)
                values=[float(ref[k]) for k in ('center_dn','center_dt')]
                if not np.isfinite(values).all() or not f['available'] or not np.allclose([f['n'],f['t']],values,rtol=0,atol=1e-10):raise ValueError('E027fullcentre mismatch')
                if len({(r['old_dn'],r['old_dt']) for r in selected})!=1:raise ValueError('oldFIT source inconsistency')
                f.update(stage_index=j,support_name=support,old_n=float(ref['old_dn']),old_t=float(ref['old_dt']))
                if not np.isfinite([f['old_n'],f['old_t']]).all():raise ValueError('nonfinite oldFIT')
                if not np.allclose([f['old_n'],f['old_t']],[float(selected[0]['old_dn']),float(selected[0]['old_dt'])],rtol=0,atol=1e-12):raise ValueError('oldFIT comparator mismatch')
                fulls.append(f)
                loos.extend(dict(r,stage_index=j,support_name=support) for r in ll)
                weights.extend(dict(r,stage_index=j,support_name=support) for r in ww)
        pairs=temporal_pairs(fulls,loos);summary=summarize(fulls,loos,pairs)
        write_csv(a.output/'full_centres.csv',fulls);write_csv(a.output/'leave_one_out_centres.csv',loos);write_csv(a.output/'temporal_pairs.csv',pairs)
        write_csv(a.output/'centre_weights.csv',weights);write_csv(a.output/'source_correspondences.csv',rows);dump_new(a.output/'summary.json',summary)
        files=[a.source/name for name in ('runtime_receipt.json','correspondences.csv','field_diagnostics.csv')]
        dump_new(a.output/'input_identity.json',{str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError('60s budget')
        receipt.update(execution='succeeded',retrieval='verified_local',source=str(a.source.resolve()),full_fields=len(fulls),loo_opportunities=len(loos),pair_opportunities=len(pairs),
            pixels_read=False,widths_read=False,output=str(a.output.resolve()))
    except Exception as error:receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
