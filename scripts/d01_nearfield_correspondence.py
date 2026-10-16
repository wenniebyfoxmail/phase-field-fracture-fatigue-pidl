#!/usr/bin/env python3
"""E027 near-background correspondence, independent of width values."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from d01_background_anchor_diagnostic import load_inputs,load_gray,local_grid,source_sample
from d01_conditional_interface import dump_new,write_csv
from d01_t1_local_audit import read_csv

RADII=(7,11)
SEARCH=6


def candidates():
    return [dict(anchor_id=f"N{k+1:02d}",n=n,t=t) for k,(n,t) in
            enumerate((n,t) for n in (-55,-35,35,55) for t in (-36,-18,0,18,36))]


def refined_peak(scores):
    if scores.shape!=(13,13) or not np.isfinite(scores).all():raise ValueError("13x13 finite NCC scores required")
    y,x=np.unravel_index(np.argmax(scores),scores.shape)
    peak=float(scores[y,x]);other=scores.copy()
    other[max(0,y-1):y+2,max(0,x-1):x+2]=-np.inf
    out=dict(available=False,reason="search_boundary",peak=peak,separation=peak-float(np.max(other)),dn=None,dt=None)
    if y in (0,12) or x in (0,12):return out
    def refine(a,b,c):
        den=a-2*b+c
        return float(np.clip(.5*(a-c)/den,-.5,.5)) if den < -1e-12 else 0.
    out.update(available=True,reason="candidate_match",dn=float(x-SEARCH+refine(scores[y,x-1],peak,scores[y,x+1])),
               dt=float(y-SEARCH+refine(scores[y-1,x],peak,scores[y+1,x])))
    return out


def match(template,search):
    template=np.asarray(template,np.float32);search=np.asarray(search,np.float32)
    if template.ndim!=2 or template.shape[0]!=template.shape[1] or template.shape[0] not in (15,23) or search.shape!=tuple(v+12 for v in template.shape):
        raise ValueError("frozen template/search shape mismatch")
    if not np.isfinite(template).all() or not np.isfinite(search).all():raise ValueError("nonfinite match input")
    if float(np.std(template,dtype=np.float64))<=1:
        return dict(available=False,reason="weak_template",peak=None,separation=None,dn=None,dt=None)
    scores=cv2.matchTemplate(np.ascontiguousarray(search),np.ascontiguousarray(template),cv2.TM_CCOEFF_NORMED)
    return refined_peak(scores)


def inside_hull(points,point):
    points=np.asarray(points,np.float32)
    if len(points)<3:return False
    hull=cv2.convexHull(points)
    return bool(cv2.contourArea(hull)>1e-9 and cv2.pointPolygonTest(hull,tuple(map(float,point)),False)>=0)


def affine_diagnostic(points,shifts):
    points=np.asarray(points,float).reshape(-1,2);shifts=np.asarray(shifts,float).reshape(-1,2)
    if len(points)!=len(shifts) or not np.isfinite(points).all() or not np.isfinite(shifts).all():
        raise ValueError("finite aligned field points required")
    result=dict(support=len(points),field_available=False,center_interpolation_available=False,
                reason="insufficient_support",rank=None,condition=None,origin_inside_hull=False,
                center_dn=None,center_dt=None,fit_RMS_px=None,loo_inside_count=0,loo_outside_count=0,
                loo_inside_RMS_px=None,loo_outside_RMS_px=None)
    loo=[]
    if len(points)<4:return result,loo
    design=np.column_stack((np.ones(len(points)),points[:,0]/55,points[:,1]/36))
    rank=int(np.linalg.matrix_rank(design));condition=float(np.linalg.cond(design))
    result.update(rank=rank,condition=condition,origin_inside_hull=inside_hull(points,(0,0)))
    if rank!=3 or not np.isfinite(condition) or condition>100:
        result['reason']='rank_or_condition';return result,loo
    coeff=np.linalg.lstsq(design,shifts,rcond=None)[0]
    result.update(field_available=True,reason="center_interpolation" if result['origin_inside_hull'] else "center_extrapolation_not_qualified",
                  center_interpolation_available=result['origin_inside_hull'],
                  center_dn=float(coeff[0,0]) if result['origin_inside_hull'] else None,
                  center_dt=float(coeff[0,1]) if result['origin_inside_hull'] else None,
                  fit_RMS_px=float(np.sqrt(np.mean(np.sum((design@coeff-shifts)**2,axis=1)))))
    for i in range(len(points)):
        mask=np.arange(len(points))!=i;x=design[mask]
        valid=np.linalg.matrix_rank(x)==3 and np.linalg.cond(x)<=100
        interior=inside_hull(points[mask],points[i])
        error=float(np.linalg.norm(design[i]@np.linalg.lstsq(x,shifts[mask],rcond=None)[0]-shifts[i])) if valid else None
        loo.append(dict(index=i,inside_remaining_hull=interior,available=bool(valid),error_px=error))
    for name,interior in (("inside",True),("outside",False)):
        values=[r['error_px'] for r in loo if r['available'] and r['inside_remaining_hull']==interior]
        result[f'loo_{name}_count']=len(values)
        result[f'loo_{name}_RMS_px']=float(np.sqrt(np.mean(np.square(values)))) if values else None
    return result,loo


def pair_match(reference,target,H_ref,H_target,g,tr,c,radius,template):
    # Local n = columns, t = rows. Reverse search is centred at original p.
    target_search=source_sample(target,local_grid(tr,c['n'],c['t'],radius+SEARCH),H_target,g)
    forward=match(template,target_search)
    empty=dict(available=False,reason="forward_unavailable",peak=None,separation=None,dn=None,dt=None)
    reverse=empty;matched=None
    if forward['available']:
        matched=source_sample(target,local_grid(tr,c['n']+forward['dn'],c['t']+forward['dt'],radius),H_target,g)
        ref_search=source_sample(reference,local_grid(tr,c['n'],c['t'],radius+SEARCH),H_ref,g)
        reverse=match(matched,ref_search)
    fb=float(np.hypot(reverse['dn'],reverse['dt'])) if reverse['available'] else None
    return forward,reverse,fb,matched


def combine(primary,secondary,c,old):
    available=primary['forward_available']
    size_difference=float(np.hypot(primary['dn']-secondary['dn'],primary['dt']-secondary['dt'])) if available and secondary['forward_available'] else None
    flags=[]
    if available:
        for label,r in (('primary',primary),('secondary',secondary)):
            if not r['forward_available']:flags.append(label+'_forward_unavailable');continue
            if r['peak']<.8:flags.append(label+'_low_ncc')
            if r['separation']<.02:flags.append(label+'_ambiguous_peak')
            if not r['reverse_available'] or r['roundtrip_px']>.5:flags.append(label+'_roundtrip')
        if size_difference is None or size_difference>.5:flags.append('template_size')
    else:flags.append(primary['reason'])
    dn,dt=primary['dn'],primary['dt']
    rn=dn-old[0] if available else None;rt=dt-old[1] if available else None
    return dict(anchor_id=c['anchor_id'],n=c['n'],t=c['t'],available=available,flags=';'.join(flags),
                flags_clear=available and not flags,template_difference_px=size_difference,
                dn=dn,dt=dt,old_dn=float(old[0]),old_dt=float(old[1]),residual_dn=rn,residual_dt=rt,
                before_norm_px=float(np.hypot(dn,dt)) if available else None,
                after_norm_px=float(np.hypot(rn,rt)) if available else None,
                roundtrip_px=primary['roundtrip_px'],peak=primary['peak'],separation=primary['separation'])


def load_selection(path):
    selection=json.loads(Path(path).read_text());decisions=selection['decisions']
    if selection['protocol']!='near-background-v1' or not selection['locked_before_new_target_matching'] or selection['future_images_or_match_outputs_viewed'] or selection['width_values_viewed']:
        raise ValueError('selection exposure/protocol mismatch')
    if len(decisions)!=20 or [r['anchor_id'] for r in decisions]!=[c['anchor_id'] for c in candidates()]:
        raise ValueError('selection candidate identities/order mismatch')
    if any(r['decision'] not in ('accept','exclude','uncertain') for r in decisions):raise ValueError('selection decision malformed')
    return selection,{r['anchor_id']:r for r in decisions}


def side_subset(rows,side):
    if side=='both':return list(rows)
    if side=='negative_n':return [r for r in rows if r['n']<0]
    if side=='positive_n':return [r for r in rows if r['n']>0]
    raise ValueError('unknown side')


def run_matching(inputs,prepared,selection_path,old_path,output):
    repo=Path(__file__).resolve().parents[1];receipt=receipt_base(repo,'S03-E027-D01-R001',output)
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    try:
        selection,decisions=load_selection(selection_path)
        if Path(selection['origin_directory']).resolve()!=prepared.resolve():raise ValueError('selection/preparation directory mismatch')
        prep_receipt=json.loads((prepared/'runtime_receipt.json').read_text())
        if prep_receipt['execution']!='succeeded' or not prep_receipt['origin_only'] or prep_receipt['code_commit']!=selection['origin_code_commit']:
            raise ValueError('origin preparation identity mismatch')
        g,H,_,_=load_inputs(inputs);tr=g['transects'][0];reference=load_gray(g['stages'][0])
        bg_receipt=json.loads((old_path.parent/'runtime_receipt.json').read_text())
        if bg_receipt['execution']!='succeeded' or bg_receipt['code_commit']!='ac56fdb6348f4cb3636271cee6b10e9cc5bb3212':raise ValueError('old FIT provenance mismatch')
        shifts=read_csv(old_path)
        old={}
        for r in shifts:
            if int(r['transect_id'])!=1 or int(r['stage_index']) not in (1,2,3):continue
            j=int(r['stage_index'])
            if j in old or r['available']!='True' or float(r['load_kN'])!=g['stages'][j]['nominal_load_kN']:raise ValueError('old FIT shift identity')
            old[j]=np.array([float(r['shift_n']),float(r['shift_t'])])
            if not np.isfinite(old[j]).all():raise ValueError('nonfinite old FIT')
        if set(old)!={1,2,3}:raise ValueError('old FIT stages incomplete')
        templates=np.load(prepared/'templates.npz',allow_pickle=False)
        # Verify R000 template content against the same reference before target reads.
        for c in candidates():
            for radius in RADII:
                re=source_sample(reference,local_grid(tr,c['n'],c['t'],radius),H[0],g)
                if not np.array_equal(re,templates[f"{c['anchor_id']}_r{radius}"]):raise ValueError('origin template changed')
        all_matches=[];combined=[];fields=[];loos=[];stage_stats=[];arrays={'context_st0':templates['context']};source_images=[g['stages'][0]]
        n=np.array(tr['normal']);tangent=np.array([-n[1],n[0]])
        nn,tt=np.meshgrid(np.arange(-85,86),np.arange(-60,61))
        context_grid=np.asarray(tr['center'])+nn[...,None]*n+tt[...,None]*tangent
        for j in (1,2,3):
            if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError('60s matching budget')
            target=load_gray(g['stages'][j]);source_images.append(g['stages'][j])
            arrays[f'context_st{j}']=source_sample(target,context_grid,H[j],g)
            for c in candidates():
                local=[]
                accepted=decisions[c['anchor_id']]['decision']=='accept'
                for radius in RADII:
                    row=dict(stage_index=j,load_kN=g['stages'][j]['nominal_load_kN'],anchor_id=c['anchor_id'],n=c['n'],t=c['t'],radius=radius,
                             origin_accepted=accepted,forward_available=False,reason='origin_'+decisions[c['anchor_id']]['decision'],dn=None,dt=None,
                             peak=None,separation=None,reverse_available=False,reverse_reason='not_attempted',reverse_dn=None,reverse_dt=None,reverse_peak=None,reverse_separation=None,
                             roundtrip_px=None)
                    if accepted:
                        template=templates[f"{c['anchor_id']}_r{radius}"]
                        f,b,fb,matched=pair_match(reference,target,H[0],H[j],g,tr,c,radius,template)
                        row.update(forward_available=f['available'],reason=f['reason'],dn=f['dn'],dt=f['dt'],peak=f['peak'],separation=f['separation'],
                                   reverse_available=b['available'],reverse_reason=b['reason'],reverse_dn=b['dn'],reverse_dt=b['dt'],
                                   reverse_peak=b['peak'],reverse_separation=b['separation'],roundtrip_px=fb)
                        if radius==7:
                            arrays[f"{c['anchor_id']}_reference"]=template
                            arrays[f"st{j}_{c['anchor_id']}_uncorrected"]=source_sample(target,local_grid(tr,c['n'],c['t'],7),H[j],g)
                            arrays[f"st{j}_{c['anchor_id']}_old"]=source_sample(target,local_grid(tr,c['n']+old[j][0],c['t']+old[j][1],7),H[j],g)
                            if matched is not None:arrays[f"st{j}_{c['anchor_id']}_matched"]=matched
                    local.append(row);all_matches.append(row)
                result=combine(local[0],local[1],c,old[j]);result.update(stage_index=j,load_kN=g['stages'][j]['nominal_load_kN'],origin_accepted=accepted)
                combined.append(result)
            rr=[r for r in combined if r['stage_index']==j]
            for support in ('all_available','flags_clear'):
                subset=[r for r in rr if r['available'] and (support=='all_available' or r['flags_clear'])]
                points=[[r['n'],r['t']] for r in subset];d=[[r['dn'],r['dt']] for r in subset]
                field,loo=affine_diagnostic(points,d)
                field.update(stage_index=j,support_name=support,old_dn=float(old[j][0]),old_dt=float(old[j][1]))
                field['center_difference_from_old_px']=float(np.hypot(field['center_dn']-old[j][0],field['center_dt']-old[j][1])) if field['center_interpolation_available'] else None
                fields.append(field)
                for l in loo:loos.append(dict(stage_index=j,support_name=support,anchor_id=subset[l['index']]['anchor_id'],**l))
                for side in ('both','negative_n','positive_n'):
                    pool=side_subset(rr,side);ss=side_subset(subset,side)
                    stats=dict(stage_index=j,load_kN=g['stages'][j]['nominal_load_kN'],support_name=support,side=side,nominal=len(pool),
                               origin_accepted=sum(r['origin_accepted'] for r in pool),available=len(ss))
                    for key in ('before_norm_px','after_norm_px','dn','dt','residual_dn','residual_dt','roundtrip_px','template_difference_px'):
                        v=[r[key] for r in ss if r[key] is not None]
                        stats['median_'+key]=float(np.median(v)) if v else None
                    stats['median_paired_norm_change_px']=float(np.median([r['after_norm_px']-r['before_norm_px'] for r in ss])) if ss else None
                    stage_stats.append(stats)
        write_csv(output/'matches.csv',all_matches);write_csv(output/'correspondences.csv',combined)
        write_csv(output/'field_diagnostics.csv',fields);write_csv(output/'stage_statistics.csv',stage_stats)
        if loos:write_csv(output/'leave_one_out.csv',loos)
        np.savez_compressed(output/'display_arrays.npz',**arrays)
        summary=dict(origin_candidates=20,origin_accepted=sum(r['decision']=='accept' for r in decisions.values()),
                     template_stage_opportunities=len(all_matches),combined_opportunities=len(combined),
                     primary_available=sum(r['available'] for r in combined),flags_clear=sum(r['flags_clear'] for r in combined),
                     by_stage=[r for r in stage_stats if r['support_name']=='all_available' and r['side']=='both'],
                     center_fields=fields,physical_coordinate_accuracy_certified=False,width_or_old_score_modified=False)
        dump_new(output/'summary.json',summary);dump_new(output/'source_images.json',source_images)
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError('60s matching budget')
        receipt.update(execution='succeeded',retrieval='verified_local',selection_file=str(selection_path.resolve()),prepared=str(prepared.resolve()),
                       old_shift_file=str(old_path.resolve()),source_image_count=4,template_stage_rows=len(all_matches),combined_rows=len(combined))
        print(json.dumps(summary,indent=2))
    except Exception as error:
        receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(output/'runtime_receipt.json',receipt)


def receipt_base(repo,run_id,output):
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"):raise RuntimeError("clean committed code required")
    return dict(experiment_id="S03-E027-D01",protocol="near-background-v1",run_id=run_id,
                code_commit=git("rev-parse","HEAD"),git_dirty=False,hostname=socket.gethostname(),pid=os.getpid(),
                python=sys.executable,command=sys.argv,gpu=None,started_utc=datetime.now(timezone.utc).isoformat(),
                execution="running",retrieval="pending",output=str(output.resolve()))


def prepare(inputs,output):
    repo=Path(__file__).resolve().parents[1];receipt=receipt_base(repo,"S03-E027-D01-R000",output)
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();cpu=time.process_time()
    try:
        g,H,_,_=load_inputs(inputs);tr=g["transects"][0];image=load_gray(g["stages"][0])
        templates={};manifest=[]
        for c in candidates():
            for radius in RADII:
                patch=source_sample(image,local_grid(tr,c["n"],c["t"],radius),H[0],g)
                source_sample(image,local_grid(tr,c["n"],c["t"],radius+SEARCH),H[0],g)
                templates[f"{c['anchor_id']}_r{radius}"]=patch
            manifest.append(dict(c,primary_radius=7,secondary_radius=11,search_radius=6,
                                 origin_only=True,selection="pending_origin_visual_review"))
        # Clean reference frame plus unselected fixed candidate footprints, no widths/future result.
        nn,tt=np.meshgrid(np.arange(-85,86),np.arange(-60,61))
        n=np.asarray(tr["normal"]);t=np.array([-n[1],n[0]])
        grid=np.asarray(tr["center"])+nn[...,None]*n+tt[...,None]*t
        context=source_sample(image,grid,H[0],g)
        np.savez_compressed(output/"templates.npz",context=context,**templates)
        write_csv(output/"candidates.csv",manifest)
        fig,axes=plt.subplots(1,2,figsize=(13,6))
        for ax in axes:
            ax.imshow(context,origin="lower",extent=(-85.5,85.5,-60.5,60.5),cmap="gray",vmin=0,vmax=255,interpolation="nearest")
            ax.set_xlabel("First-frame normal coordinate n (px)");ax.set_ylabel("First-frame tangent coordinate t (px)")
        axes[0].set_title("10 kN first frame: clean context, no width boundary")
        axes[1].set_title("Fixed candidates: solid23x23 template / dashed35x35 search")
        for c in candidates():
            for radius,style in ((11,"-"),(17,"--")):
                axes[1].add_patch(Rectangle((c["n"]-radius-.5,c["t"]-radius-.5),2*radius+1,2*radius+1,
                                          fill=False,edgecolor="#0072B2",lw=.7,ls=style))
            axes[1].text(c["n"],c["t"],c["anchor_id"],fontsize=8,color="#D55E00",ha="center",va="center")
        fig.tight_layout();fig.savefig(output/"origin_context.png",dpi=200);plt.close(fig)
        fig,axes=plt.subplots(4,5,figsize=(12,10))
        for ax,c in zip(axes.flat,candidates()):
            ax.imshow(templates[f"{c['anchor_id']}_r11"],cmap="gray",vmin=0,vmax=255,interpolation="nearest")
            ax.set_title(f"{c['anchor_id']} | n{c['n']},t{c['t']}",fontsize=10);ax.set_xticks([]);ax.set_yticks([])
        fig.suptitle("First-frame maximum templates only; no target images or match outputs")
        fig.tight_layout(rect=(0,0,1,.96));fig.savefig(output/"origin_template_atlas.png",dpi=200);plt.close(fig)
        dump_new(output/"origin_source.json",dict(source=g["stages"][0],geometry_inputs=str(inputs.resolve()),
                                                candidate_count=20,reference_only=True))
        if time.monotonic()-start>60 or time.process_time()-cpu>60:raise TimeoutError("60s origin preparation")
        receipt.update(execution="succeeded",retrieval="verified_local",source_images=1,origin_only=True)
    except Exception as error:
        receipt.update(execution="failed",error=repr(error));raise
    finally:
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        dump_new(output/"runtime_receipt.json",receipt)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("prepare","match"),required=True)
    p.add_argument("--inputs",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--prepared",type=Path);p.add_argument("--selection",type=Path);p.add_argument("--old-shifts",type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.inputs,a.output)
    else:
        if any(x is None for x in (a.prepared,a.selection,a.old_shifts)):p.error('match needs prepared/selection/old-shifts')
        run_matching(a.inputs,a.prepared,a.selection,a.old_shifts,a.output)


if __name__=="__main__":main()
