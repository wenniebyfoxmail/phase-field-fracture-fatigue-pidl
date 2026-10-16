#!/usr/bin/env python3
"""E028: observed background residual scenarios, NOT certified location errors."""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
from d01_background_anchor_diagnostic import load_inputs, load_gray, source_sample
from independent_d01_halfdepth import measure, sampling_grid
from d01_conditional_interface import dump_new, write_csv
from d01_t1_local_audit import read_csv, decompose

MODES = ('normal_only', 'tangent_only', 'joint')
STAGES = (1, 2, 3)
LOADS = (30, 40, 50)
IDS = tuple(f'N{i:02d}' for i in range(1, 21) if i not in (5, 9, 10))
S = np.arange(-60., 60.01, .25)


def perturbation(residual, mode):
    r = np.asarray(residual, float)
    if r.shape != (2,) or not np.isfinite(r).all():
        raise ValueError('finite paired n/t residual required')
    if mode == 'normal_only': return r * [1, 0]
    if mode == 'tangent_only': return r * [0, 1]
    if mode == 'joint': return r.copy()
    raise ValueError('unknown coordinate mode')


def sample_shifted(image, H, g, tr, shift):
    shift = np.asarray(shift, float)
    if shift.shape != (2,) or not np.isfinite(shift).all(): raise ValueError('finite shift required')
    n = np.asarray(tr['normal']); t = np.array([-n[1], n[0]])
    center = np.asarray(tr['center']) + shift[0]*n + shift[1]*t
    p = np.median(source_sample(image, sampling_grid(center, n, S), H, g), axis=0)
    if not np.isfinite(p).all(): raise ValueError('nonfinite profile')
    return p, measure(S, p)


def validate_residuals(rows, old):
    if len(rows) != 60: raise ValueError('expected all60 anchor-stage opportunities')
    out = {}; seen = set()
    for r in rows:
        j = int(r['stage_index']); aid = r['anchor_id']; key = (j, aid)
        if key in seen or j not in STAGES or aid not in tuple(f'N{i:02d}' for i in range(1,21)):
            raise ValueError('duplicate or unexpected residual identity')
        seen.add(key)
        if float(r['load_kN']) != LOADS[j-1]: raise ValueError('residual load mismatch')
        if r['available'] not in ('True','False') or r['flags_clear'] not in ('True','False'):
            raise ValueError('malformed availability/quality')
        available = r['available'] == 'True'
        if available != (aid in IDS) or (r['origin_accepted']=='True') != (aid in IDS):
            raise ValueError('origin/availability support changed')
        if not np.allclose([float(r['old_dn']),float(r['old_dt'])], old[j], rtol=0, atol=1e-12):
            raise ValueError('oldFIT comparator mismatch')
        if available:
            d = np.array([float(r['dn']),float(r['dt'])]); residual = np.array([float(r['residual_dn']),float(r['residual_dt'])])
            if not np.isfinite([d,residual]).all() or not np.allclose(residual,d-old[j],rtol=0,atol=1e-12):
                raise ValueError('residual sign/identity mismatch')
            if (r['flags_clear']=='True') != (not r['flags']): raise ValueError('quality flags mismatch')
            out[key] = dict(r, residual=residual, clear=r['flags_clear']=='True')
    if set(out) != {(j,a) for j in STAGES for a in IDS}: raise ValueError('incomplete accepted support')
    return out


def scenario(measurements, mode, ids, temporal, baseline):
    selected = [measurements[j,aid,mode] for j,aid in zip(STAGES,ids)]
    good = all(r['valid'] for r in selected)
    r = dict(mode=mode, temporal=temporal, anchor30=ids[0], anchor40=ids[1], anchor50=ids[2],
             flags_clear=all(x['flags_clear'] for x in selected), valid=good,
             reason='ok' if good else ';'.join(f"st{j}:{x['reason']}" for j,x in zip(STAGES,selected) if not x['valid']))
    keys = tuple(decompose([1,1,1])) + ('delta_w30','delta_w40','delta_w50','contribution30','contribution40',
            'contribution50','clip_change','delta_error','decomposition_residual')
    r.update({k:None for k in keys})
    if good:
        q = decompose([x['width_px'] for x in selected]); r.update(q)
        dw = np.array([q[f'w{l}']-baseline[f'w{l}'] for l in LOADS])
        terms = dw * [-1,2,-1]
        clip = (q['secant']-q['secant_raw'])-(baseline['secant']-baseline['secant_raw'])
        r.update(delta_w30=float(dw[0]),delta_w40=float(dw[1]),delta_w50=float(dw[2]),
                 contribution30=float(terms[0]),contribution40=float(terms[1]),contribution50=float(terms[2]),
                 clip_change=clip,delta_error=q['secant_error']-baseline['secant_error'],
                 decomposition_residual=float(q['secant_error']-baseline['secant_error']-sum(terms)-clip))
        if abs(r['decomposition_residual'])>1e-8: raise ValueError('error decomposition mismatch')
    return r


def summarize(rows):
    output=[]
    for mode,temporal,support in itertools.product(MODES,('coherent','independent_stage'),('all_available','flags_clear')):
        pool=[r for r in rows if r['mode']==mode and r['temporal']==temporal and (support=='all_available' or r['flags_clear'])]
        good=[r for r in pool if r['valid']]
        d=dict(mode=mode,temporal=temporal,support=support,opportunities=len(pool),valid=len(good),invalid=len(pool)-len(good))
        for key in ('secant_error','delta_error'):
            values=[r[key] for r in good]
            d[key+'_min']=min(values,default=None);d[key+'_max']=max(values,default=None)
            d[key+'_median']=float(np.median(values)) if values else None
        errors=[r['secant_error'] for r in good]
        d.update(min_abs_error=min(map(abs,errors),default=None),
                 extrema_bracket_zero=(min(errors)<=0<=max(errors)) if errors else None,
                 negative=sum(e<0 for e in errors),zero=sum(e==0 for e in errors),positive=sum(e>0 for e in errors),
                 clip_active=sum(r['clip_active'] for r in good))
        output.append(d)
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();repo=Path(__file__).resolve().parents[1]
    git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean committed code required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E028-D01',run_id='S03-E028-D01-R001',protocol='T1-residual-propagation-v1',
        code_commit=git('rev-parse','HEAD'),git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),python=sys.executable,
        command=sys.argv,gpu=None,started_utc=datetime.now(timezone.utc).isoformat(),execution='running',retrieval='pending',budget_seconds=60)
    def budget():
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError('60s budget')
    try:
        paths={name:a.archive/f'S03-E{num}-D01/runs/S03-E{num}-D01-R001/outputs' for name,num in (('old','019'),('audit','026'),('near','027'))}
        expected={'old':'ac56fdb6348f4cb3636271cee6b10e9cc5bb3212','audit':'991e5b0da054b311689f81ea4e0eb59a4f6dc979','near':'65e424d1f7b71b4080473853d246b8c14ee74669'}
        for name,path in paths.items():
            r=json.loads((path/'runtime_receipt.json').read_text())
            if r['execution']!='succeeded' or r['code_commit']!=expected[name]:raise ValueError('source receipt mismatch:'+name)
        inputs=a.archive/'S03-E018-D01/runs/S03-E018-D01-R001/safe_inputs'
        g,H,_,_=load_inputs(inputs);tr=g['transects'][0];old={}
        for r in read_csv(paths['old']/'translations.csv'):
            if int(r['transect_id'])!=1 or int(r['stage_index']) not in STAGES:continue
            j=int(r['stage_index'])
            if j in old or r['available']!='True' or float(r['load_kN'])!=LOADS[j-1]:raise ValueError('oldFIT identity')
            old[j]=np.array([float(r['shift_n']),float(r['shift_t'])])
        if set(old)!=set(STAGES) or not np.isfinite(list(old.values())).all():raise ValueError('oldFIT support')
        source_rows=read_csv(paths['near']/'correspondences.csv');residuals=validate_residuals(source_rows,old)
        files=[inputs/'geometry.json',inputs/'Beam4_inputs.npz']+[path/'runtime_receipt.json' for path in paths.values()]+[paths['old']/'translations.csv',paths['near']/'correspondences.csv',paths['audit']/'summary.json']
        dump_new(a.output/'input_identity.json',{str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
        reference=next(r['nominal'] for r in json.loads((paths['audit']/'summary.json').read_text())['by_arm'] if r['arm']=='background_aligned')
        baselines=[];measurements={};arrays={'normal_offsets':S};sources=[]
        for j,load in zip(STAGES,LOADS):
            budget();image=load_gray(g['stages'][j]);sources.append(g['stages'][j])
            profile,m=sample_shifted(image,H[j],g,tr,old[j])
            if not m['valid'] or abs(m['width_px']-reference[f'w{load}'])>1e-8:raise ValueError('E026 baseline width mismatch')
            baselines.append(dict(stage_index=j,load_kN=load,width_px=m['width_px'],left_px=m['left_px'],right_px=m['right_px']))
            arrays[f'st{j}_baseline_profile']=profile;arrays[f'st{j}_baseline_deficit']=m['deficit']
            for aid,mode in itertools.product(IDS,MODES):
                src=residuals[j,aid];delta=perturbation(src['residual'],mode)
                try:prof,m=sample_shifted(image,H[j],g,tr,old[j]+delta)
                except ValueError as error:
                    if str(error)!='sample_out_of_bounds':raise
                    prof=None;m=dict(valid=False,reason='sample_out_of_bounds',width_px=None,left_px=None,right_px=None)
                rec=dict(stage_index=j,load_kN=load,anchor_id=aid,mode=mode,flags_clear=src['clear'],flags=src['flags'],
                    residual_n=float(src['residual'][0]),residual_t=float(src['residual'][1]),
                    perturb_n=float(delta[0]),perturb_t=float(delta[1]),old_n=float(old[j][0]),old_t=float(old[j][1]),
                    valid=m['valid'],reason=m['reason'],width_px=m['width_px'],left_px=m['left_px'],right_px=m['right_px'])
                measurements[j,aid,mode]=rec
                if prof is not None:arrays[f'st{j}_{aid}_{mode}_profile']=prof;arrays[f'st{j}_{aid}_{mode}_deficit']=m['deficit']
            del image
        baseline=decompose([r['width_px'] for r in baselines])
        if abs(baseline['secant_error']-reference['secant_error'])>1e-8:raise ValueError('E026 baseline error mismatch')
        cases=[]
        for mode in MODES:
            for aid in IDS:cases.append(scenario(measurements,mode,(aid,aid,aid),'coherent',baseline))
            for ids in itertools.product(IDS,repeat=3):cases.append(scenario(measurements,mode,ids,'independent_stage',baseline))
            budget()
        stats=summarize(cases)
        summary=dict(baseline=baseline,by_support=stats,origin_accepted=len(IDS),origin_nominal=20,
            per_stage_flags_clear={str(j):sum(residuals[j,aid]['clear'] for aid in IDS) for j in STAGES},
            common_flags_clear_ids=[aid for aid in IDS if all(residuals[j,aid]['clear'] for j in STAGES)],
            measured_scenario_profiles=len(measurements),valid_profiles=sum(r['valid'] for r in measurements.values()),
            position_transfer_assumed_not_verified=True,role='posthoc_viewed_development',old_scores_changed=False)
        write_csv(a.output/'source_residuals.csv',source_rows);write_csv(a.output/'baseline_measurements.csv',baselines)
        write_csv(a.output/'profile_measurements.csv',list(measurements.values()));write_csv(a.output/'coherent_cases.csv',[r for r in cases if r['temporal']=='coherent'])
        write_csv(a.output/'all_scenarios.csv',cases);write_csv(a.output/'support_statistics.csv',stats)
        dump_new(a.output/'summary.json',summary);dump_new(a.output/'source_images.json',sources)
        np.savez_compressed(a.output/'profiles.npz',**arrays);budget()
        receipt.update(execution='succeeded',retrieval='verified_local',decoded_images=3,profile_rows=len(measurements),scenario_rows=len(cases),
            output=str(a.output.resolve()),source_paths={k:str(v.resolve()) for k,v in paths.items()})
    except Exception as error:
        receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
