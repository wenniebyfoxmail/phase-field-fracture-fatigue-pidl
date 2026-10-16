#!/usr/bin/env python3
"""E030: ONE pre-saved background location; unchanged half-depth diagnostic."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
from d01_background_anchor_diagnostic import load_inputs, load_gray, source_sample
from d01_residual_width_propagation import sample_shifted, S, STAGES, LOADS
from d01_t1_local_audit import read_csv, decompose
from d01_conditional_interface import dump_new, write_csv

ARMS = ('original_H', 'oldFIT', 'fixed_background')
PROTOCOL = 'T1-fixed-background-sampling-v1'
EXPECTED = np.array([[.04569173787228974,.493393543168934],
                     [-.8201495950481548,1.296797379131024],
                     [.4466233097393149,.5355691893447587]])


def validate_lock(lock, rows):
    if (lock['experiment_id'] != 'S03-E030-D01' or lock['protocol'] != PROTOCOL
            or lock['beam'] != 4 or lock['transect_id'] != 1
            or lock['source_numeric_commit'] != 'ae66b4f682512b41e7017afb623aea1ef36c7fdb'
            or lock['widths_read_to_create_this_file'] is not False
            or lock['alternative_positions_to_test'] is not False):
        raise ValueError('fixed lock identity changed')
    selected = [r for r in rows if r['support_name'] == 'all_available']
    if len(selected) != 3 or len(lock['positions']) != 3:
        raise ValueError('exactly three primary centres required')
    out = {}
    for index, p in enumerate(lock['positions']):
        j = STAGES[index]
        if p['stage_index'] != j or p['load_kN'] != LOADS[index]:
            raise ValueError('fixed stage/load order changed')
        shift = np.array([p['shift_n'], p['shift_t']], float)
        refs = [r for r in selected if int(r['stage_index']) == j]
        if len(refs) != 1:
            raise ValueError('primary centre source identity')
        r = refs[0]
        if r['available'] != 'True' or int(r['support']) != 17 or r['inside_hull'] != 'True':
            raise ValueError('primary centre support unavailable')
        if not np.array_equal(shift, EXPECTED[index]) or not np.array_equal(shift, [float(r['n']),float(r['t'])]):
            raise ValueError('fixed centre numeric identity changed')
        out[j] = shift
    return out


def query_summary(rows):
    out = []
    for arm in ARMS:
        pool = [r for r in rows if r['arm'] == arm]
        if len(pool) != 3 or {r['stage_index'] for r in pool} != set(STAGES):
            raise ValueError('arm stage support mismatch')
        pool.sort(key=lambda r:r['stage_index'])
        available = all(r['valid'] for r in pool)
        r = dict(arm=arm, opportunities=3, valid_profiles=sum(x['valid'] for x in pool),
                 available=available, reason='ok' if available else ';'.join(
                     f"st{x['stage_index']}:{x['reason']}" for x in pool if not x['valid']))
        r.update(decompose([x['width_px'] for x in pool]) if available else {k:None for k in decompose([1,1,1])})
        out.append(r)
    return out


def error_change(candidate, baseline):
    keys = ('delta_w30','delta_w40','delta_w50','contribution30','contribution40','contribution50',
            'delta_clip','prediction_change','reference_change','delta_error','abs_error_reduction','identity_residual')
    r = dict(available=candidate['available'] and baseline['available'])
    r.update({k:None for k in keys})
    if r['available']:
        dw = np.array([candidate[f'w{l}']-baseline[f'w{l}'] for l in LOADS])
        terms = dw*[-1,2,-1]
        clip = (candidate['secant']-candidate['secant_raw'])-(baseline['secant']-baseline['secant_raw'])
        de = candidate['secant_error']-baseline['secant_error']
        r.update(dict(zip(('delta_w30','delta_w40','delta_w50'),map(float,dw))))
        r.update(dict(zip(('contribution30','contribution40','contribution50'),map(float,terms))))
        r.update(delta_clip=clip,prediction_change=candidate['secant']-baseline['secant'],
                 reference_change=float(dw[2]),delta_error=de,
                 abs_error_reduction=abs(baseline['secant_error'])-abs(candidate['secant_error']),
                 identity_residual=float(de-terms.sum()-clip))
        if abs(r['identity_residual']) > 1e-8:raise ValueError('error identity mismatch')
    return r


def reproduce(summary, reference):
    if not summary['available']:raise ValueError('baseline unavailable')
    for key in decompose([1,1,1]):
        value = reference[key]
        if isinstance(value, bool):
            if summary[key] != value:raise ValueError('baseline logical mismatch:'+key)
        elif not np.isfinite(value) or abs(summary[key]-value)>1e-8:
            raise ValueError('baseline numeric mismatch:'+key)


def hashes(files):
    return {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--positions',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1]
    git=lambda *x:subprocess.check_output(['git',*x],cwd=repo,text=True).strip()
    if git('status','--porcelain'):raise RuntimeError('clean committed code required')
    a.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    receipt=dict(experiment_id='S03-E030-D01',run_id='S03-E030-D01-R001',protocol=PROTOCOL,
        code_commit=git('rev-parse','HEAD'),git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),
        python=sys.executable,command=sys.argv,gpu=None,started_utc=datetime.now(timezone.utc).isoformat(),
        execution='running',retrieval='pending',budget_seconds=60,output=str(a.output.resolve()))
    def budget():
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError('60s budget')
    try:
        path=lambda num:a.archive/f'S03-E{num}-D01/runs/S03-E{num}-D01-R001/outputs'
        centres=path('029');old=path('019');audit=path('026')
        sources={}
        for num,expected in (('029','ae66b4f682512b41e7017afb623aea1ef36c7fdb'),
                             ('019','ac56fdb6348f4cb3636271cee6b10e9cc5bb3212'),
                             ('026','991e5b0da054b311689f81ea4e0eb59a4f6dc979')):
            r=json.loads((path(num)/'runtime_receipt.json').read_text())
            if r['execution']!='succeeded' or r['code_commit']!=expected:raise ValueError('source receipt:'+num)
            sources[num]=r
        lock=json.loads(a.positions.read_text())
        fixed=validate_lock(lock,read_csv(centres/'full_centres.csv'))
        # This new file is closed before geometry, widths or image access.
        dump_new(a.output/'positions_before_width_access.json',dict(lock,
            validated_utc=datetime.now(timezone.utc).isoformat(),position_lock_commit='8218e32'))
        receipt['positions_saved_before_width_access']=True
        baseline_shifts={}
        for r in read_csv(old/'translations.csv'):
            j=int(r['stage_index'])
            if j in STAGES and int(r['transect_id'])==1:
                if j in baseline_shifts or r['available']!='True' or float(r['load_kN'])!=LOADS[j-1]:
                    raise ValueError('oldFIT support/identity')
                baseline_shifts[j]=np.array([float(r['shift_n']),float(r['shift_t'])])
        if set(baseline_shifts)!=set(STAGES):raise ValueError('oldFIT stage coverage')
        # Cross-check oldFIT identity also against each E029 primary row.
        for r in read_csv(centres/'full_centres.csv'):
            if r['support_name']=='all_available' and not np.array_equal(
                    baseline_shifts[int(r['stage_index'])],[float(r['old_n']),float(r['old_t'])]):
                raise ValueError('oldFIT source conflict')
        inputs=a.archive/'S03-E018-D01/runs/S03-E018-D01-R001/safe_inputs'
        g,H,_,_=load_inputs(inputs);tr=g['transects'][0]
        refs=json.loads((audit/'summary.json').read_text())['by_arm']
        files=[a.positions,centres/'full_centres.csv',old/'translations.csv',audit/'summary.json',
               inputs/'geometry.json',inputs/'Beam4_inputs.npz']+[path(num)/'runtime_receipt.json' for num in sources]
        protected=sorted(path('025').glob('*'))
        protected=[f for f in protected if f.is_file()]
        if len(protected)!=6:raise ValueError('oldscore protected inventory changed')
        before=hashes(protected)
        dump_new(a.output/'input_identity.json',dict(inputs=hashes(files),protected_oldscore_before=before))
        rows=[];arrays={'normal_offsets':S};image_ids=[]
        n=np.asarray(tr['normal']);t=np.array([-n[1],n[0]])
        strip_s=np.arange(-35.,35.01,.25);strip_t=np.arange(-8.,8.01,.25)
        nn,tt=np.meshgrid(strip_s,strip_t)
        for j,load in zip(STAGES,LOADS):
            budget();image=load_gray(g['stages'][j]);image_ids.append(g['stages'][j])
            # Context on the original n/t grid, never an extra measurement arm.
            grid=np.asarray(tr['center'])+nn[...,None]*n+tt[...,None]*t
            arrays[f'st{j}_strip']=source_sample(image,grid,H[j],g)
            for arm in ARMS:
                shift={'original_H':np.zeros(2),'oldFIT':baseline_shifts[j],'fixed_background':fixed[j]}[arm]
                try:profile,m=sample_shifted(image,H[j],g,tr,shift)
                except ValueError as e:
                    if str(e)!='sample_out_of_bounds':raise
                    profile=None;m=dict(valid=False,reason=str(e),width_px=None,left_px=None,right_px=None,
                                        peak_px=None,depth=None,noise=None)
                r=dict(arm=arm,stage_index=j,load_kN=load,shift_n=float(shift[0]),shift_t=float(shift[1]),
                    **{key:m[key] if key in ('valid','reason') or m['valid'] else None for key in
                       ('valid','reason','width_px','left_px','right_px','peak_px','depth','noise')})
                rows.append(r)
                if profile is not None:
                    for key,value in (('profile',profile),('deficit',m['deficit']),('background',m['background'])):
                        arrays[f'st{j}_{arm}_{key}']=value
            del image
        arms=query_summary(rows);by_arm={r['arm']:r for r in arms}
        for arm,refarm in (('original_H','original_H'),('oldFIT','background_aligned')):
            reproduce(by_arm[arm],next(r['nominal'] for r in refs if r['arm']==refarm))
        changes={arm:error_change(by_arm[arm],by_arm['oldFIT']) for arm in ARMS}
        after=hashes(protected)
        if before!=after:raise ValueError('protected oldscores changed')
        summary=dict(by_arm=arms,changes_vs_oldFIT=changes,decoded_images=3,measured_profiles=9,
            valid_profiles=sum(r['valid'] for r in rows),role='viewed_development_diagnostic',unit='native_first_frame_px',
            fixed_positions_source=str(a.positions.resolve()),physical_accuracy_validated=False,
            old_scores_changed=False,position_search=False,baseline_reproduction_tolerance_px=1e-8)
        write_csv(a.output/'measurements.csv',rows);write_csv(a.output/'query_diagnostics.csv',arms)
        dump_new(a.output/'summary.json',summary);dump_new(a.output/'source_images.json',image_ids)
        dump_new(a.output/'oldscore_integrity.json',dict(before=before,after=after,unchanged=True))
        arrays['strip_normal']=strip_s;arrays['strip_tangent']=strip_t
        np.savez_compressed(a.output/'profiles.npz',**arrays);budget()
        receipt.update(execution='succeeded',retrieval='verified_local',decoded_images=3,profile_rows=9,
            valid_profiles=summary['valid_profiles'],old_scores_unchanged=True)
        print(json.dumps(summary,indent=2))
    except Exception as e:
        receipt.update(execution='failed',error=repr(e));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,
            cpu_seconds=time.process_time()-cpu)
        dump_new(a.output/'runtime_receipt.json',receipt)


if __name__=='__main__':main()
