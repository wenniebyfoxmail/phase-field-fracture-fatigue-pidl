#!/usr/bin/env python3
"""E016-D01: distinct edge operator, local sensitivity and repeated-view spread."""
import argparse
import base64
import csv
from datetime import datetime, timezone
import io
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
import numpy as np
from PIL import Image

from d01_crack_profile_diagnostic import S, forecast, measure, native_gray, native_homography, sample_profile
from d01_directional_scale_repeatability import crc32_file
from d01_stage_forecast_diagnostic import ARMS, dump

VARIANTS=(("centered",0.,0.),("tangent_minus2",-2.,0.),("tangent_plus2",2.,0.),
          ("normal_minus2",0.,-2.),("normal_plus2",0.,2.))


def table(path,rows):
    if not rows: return
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def edge_pair(profile):
    """Never receives half-depth crossings/widths or other operator outputs."""
    smoothed=cv2.GaussianBlur(np.asarray(profile,np.float32)[None,:],(0,0),sigmaX=4)[0]
    gradient=np.gradient(smoothed,S)
    center=np.flatnonzero(np.abs(S)<=15)
    peak=int(center[np.argmin(smoothed[center])])
    left=np.flatnonzero((S<S[peak])&(S>=S[peak]-35))
    right=np.flatnonzero((S>S[peak])&(S<=S[peak]+35))
    l=int(left[np.argmin(gradient[left])]); r=int(right[np.argmax(gradient[right])])
    valid=bool(gradient[l]<=-2 and gradient[r]>=2 and r>l and l>0 and r<len(S)-1)
    return {"valid":valid,"reason":"ok" if valid else "weak_or_censored_edge",
            "left_px":float(S[l]) if valid else None,"right_px":float(S[r]) if valid else None,
            "width_px":float(S[r]-S[l]) if valid else None,
            "left_gradient":float(gradient[l]),"right_gradient":float(gradient[r])},smoothed


def resize_map(native_shape):
    h,w=native_shape; scale=min(1.,2000/max(h,w)); wh,ww=round(h*scale),round(w*scale)
    sx=ww/w; sy=wh/h
    return np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])


def repeatview_h(h_first,h_view,canonical_shape,source_shape):
    return np.linalg.inv(resize_map(canonical_shape))@np.linalg.inv(h_first)@h_view@resize_map(source_shape)


def sample_strip(image,h,center,normal):
    x=np.arange(-60,61); y=np.arange(-24,25)
    n=np.array(normal); tangent=np.array([-n[1],n[0]])
    points=np.array(center)+x[None,:,None]*n+y[:,None,None]*tangent
    hp=np.concatenate([points,np.ones((*points.shape[:2],1))],axis=2)@np.linalg.inv(h).T
    xy=hp[...,:2]/hp[...,2:]
    if xy[...,0].min()<1 or xy[...,1].min()<1 or xy[...,0].max()>image.shape[1]-2 or xy[...,1].max()>image.shape[0]-2:
        raise ValueError("blind strip leaves source support")
    return cv2.remap(image,xy[...,0].astype(np.float32),xy[...,1].astype(np.float32),cv2.INTER_LINEAR).astype(np.uint8)


def prepare_blind(tasks,output):
    public=output/"blind_packet"; public.mkdir()
    # Six known repeat tasks for intra-annotator consistency; key stays local.
    candidates=tasks+[dict(tasks[i],repeat_of=i) for i in (0,4,8,12,16,20)]
    order=np.random.default_rng(1613).permutation(len(candidates))
    public_tasks=[]; key=[]
    for index,i in enumerate(order):
        task=candidates[int(i)]; name=f"task_{index+1:03d}"
        image=Image.fromarray(task["strip"]); buffer=io.BytesIO(); image.save(buffer,format="PNG")
        data="data:image/png;base64,"+base64.b64encode(buffer.getvalue()).decode("ascii")
        image.save(public/(name+".png"))
        public_tasks.append({"id":name,"image":data,"width":121,"height":49,"central_row":24})
        key.append({"task_id":name,"beam":task["beam"],"stage_index":task["stage_index"],
                    "transect_id":task["transect_id"],"source":task["source"],
                    "repeat_of_unique_index":task.get("repeat_of"),"unique_index":int(i) if i<len(tasks) else task["repeat_of"]})
    dump(output/"private_blind_key.json",key)
    # Template has no widths, boundary suggestions, physical labels or source key.
    template=Path(__file__).with_name("d01_blind_edge_packet.html").read_text()
    (public/"index.html").write_text(template.replace("__TASKS_JSON__",json.dumps(public_tasks)))
    dump(public/"packet_status.json",{"unique_tasks":len(tasks),"task_views":len(candidates),
         "reference_status":"pending_unannotated","independent_annotator":None,
         "algorithm_boundary_prefill":False,"key_included":False})


def self_test():
    profile=180-50*(np.tanh((S+10)/.5)-np.tanh((S-10)/.5))
    result,_=edge_pair(profile)
    assert result["valid"] and abs(result["width_px"]-20)<=.5
    other,_=edge_pair(profile*.8+15)
    assert result["left_px"]==other["left_px"] and result["right_px"]==other["right_px"]
    assert not edge_pair(np.full(len(S),180.))[0]["valid"]
    src=(3000,4000); tgt=(3744,5616)
    h=repeatview_h(np.eye(3),np.eye(3),tgt,src)
    p=np.array([2000.,1500.,1.]); expected=np.linalg.inv(resize_map(tgt))@resize_map(src)@p
    assert np.allclose(h@p,expected)
    assert np.allclose(repeatview_h(np.eye(3),np.eye(3),tgt,tgt),np.eye(3))
    assert [v[0] for v in VARIANTS]==["centered","tangent_minus2","tangent_plus2","normal_minus2","normal_plus2"]
    print("Alternate blurred-step edges, affine intensities, missing edges, two-camera resize mapping and frozen variants: passed")


def run(args,receipt):
    lock=json.loads(args.lock.read_text()); stage=args.stage
    if Path(lock["source_run"]).resolve()!=stage.resolve(): raise ValueError("lock source mismatch")
    groups=json.loads((stage/"selected_sequences_before_pixel_access.json").read_text())["groups"]
    originals={r["saved_as"]:r for r in json.loads((stage/"acquisition_receipt.json").read_text())}
    repeats={r["saved_as"]:r for r in json.loads((args.repeat_source/"selection_manifest.json").read_text())["files"]}
    old_rows=list(csv.DictReader((args.profile/"profile_measurements.csv").open()))
    def original(path,record):
        if path.stat().st_size!=record["bytes"] or crc32_file(path)!=record["crc32"]: raise ValueError(f"CRC/size mismatch: {path}")
        return native_gray(path)
    edges=[]; locations=[]; repeats_rows=[]; scores=[]; blind=[]; results=[]
    for beam in (4,5,6):
        geo=lock["beams"][str(beam)]; transects=geo["transects"]; states=groups[str(beam)]
        prior=np.load(args.profile/f"Beam{beam}_profiles.npz"); stage_data=np.load(stage/f"Beam{beam}_stage_fields.npz")
        loads=prior["loads_kN"]
        if not np.array_equal(loads,stage_data["nominal_loads_kN"]): raise ValueError("load identity mismatch")
        width=np.full((5,len(states),12),np.nan); alternate=np.full((len(states),12),np.nan)
        paired_edge=np.full((len(states),12,2),np.nan); old_edge=paired_edge.copy()
        for j,state in enumerate(states):
            path=stage/"raw_images"/state["saved_as"]; image=original(path,originals[state["saved_as"]])
            if list(image.shape)!=geo["native_shape"]: raise ValueError("native shape mismatch")
            h=native_homography(stage_data["homographies"][j],image.shape,geo["working_shape"])
            for k,t in enumerate(transects):
                # Distinct operator consumes stored GRAYSCALE only, not previous edges.
                e,_=edge_pair(prior["profiles"][j,k])
                old=next(r for r in old_rows if int(r["beam"])==beam and int(r["stage_index"])==j and int(r["transect_id"])==k+1 and r["role"]=="crack")
                old_edge[j,k]=[float(old["left_crossing_px"]),float(old["right_crossing_px"])]
                if e["valid"]:
                    alternate[j,k]=e["width_px"]; paired_edge[j,k]=[e["left_px"],e["right_px"]]
                edges.append({"beam":beam,"stage_index":j,"load_kN":float(loads[j]),"transect_id":k+1,
                              "half_depth_width_px":float(prior["widths"][j,k]),**e,
                              "width_difference_px":float(e["width_px"]-prior["widths"][j,k]) if e["valid"] else None,
                              "mean_absolute_edge_difference_px":float(np.abs(paired_edge[j,k]-old_edge[j,k]).mean()) if e["valid"] else None})
                n=np.array(t["normal"])
                for v,(name,tangent,normal) in enumerate(VARIANTS):
                    center=np.array(t["center"])+normal*n
                    found,_,_=measure(sample_profile(image,h,center,n,tangent))
                    if found["valid"]: width[v,j,k]=found["fwhm_native_px"]
                    if v==0:
                        np.testing.assert_allclose(width[v,j,k],prior["widths"][j,k],atol=1e-7,rtol=0)
                    locations.append({"beam":beam,"stage_index":j,"load_kN":float(loads[j]),"transect_id":k+1,
                                      "variant":name,"valid":found["valid"],"reason":found["reason"],
                                      "width_px":float(width[v,j,k]) if found["valid"] else None,
                                      "difference_from_centered_px":float(width[v,j,k]-prior["widths"][j,k]) if found["valid"] else None})
                if j in (0,len(states)-1) and k+1 in (3,6,9,12):
                    blind.append({"beam":beam,"stage_index":j,"transect_id":k+1,"source":str(path),
                                  "strip":sample_strip(image,h,t["center"],t["normal"])})
            del image
        eligible=prior["eligible"]
        for v,(name,_,_) in enumerate(VARIANTS):
            for origin in range(1,len(states)-1):
                supported=eligible & np.isfinite(width[v,origin-1:origin+2]).all(axis=0)
                for arm in ARMS:
                    pred=forecast(width[v,origin-1:origin+1,supported],loads[origin-1:origin+1],loads[origin+1],arm) if supported.any() else None
                    scores.append({"beam":beam,"variant":name,"origin_kN":float(loads[origin]),"target_kN":float(loads[origin+1]),
                                   "arm":arm,"scored_transects":int(supported.sum()),"eligible_transects":int(eligible.sum()),
                                   "MAE_px":float(np.abs(pred-width[v,origin+1,supported]).mean()) if supported.any() else None})
        # Replay the existing E010 reference-route mappings; never register anew.
        token=np.load(args.repeat_transforms/f"Beam{beam}_tokens.npz")
        metadata=json.loads(str(token["metadata_json"]))
        if metadata[0]["source_path"]!=states[0]["saved_as"]: raise ValueError("repeat anchor identity mismatch")
        views=np.full((8,12),np.nan)
        for i,meta in enumerate(metadata):
            path=args.repeat_source/"raw_images"/meta["source_path"]
            if meta["nominal_stop_label_kN"]!=int(loads[0 if i<4 else -1]): raise ValueError("stop identity mismatch")
            image=original(path,repeats[meta["source_path"]])
            h=repeatview_h(token["homographies"][0],token["homographies"][i],tuple(geo["native_shape"]),image.shape)
            for k,t in enumerate(transects):
                reason="outside_source_support"; found=None
                try:
                    p=sample_profile(image,h,t["center"],t["normal"])
                    found,_,_=measure(p); reason=found["reason"]
                except ValueError as error:
                    if str(error)!="profile support leaves source image": raise
                if found is not None and found["valid"]: views[i,k]=found["fwhm_native_px"]
                fixed=views[0 if i<4 else 4,k]
                repeats_rows.append({"beam":beam,"stop":meta["stop"],"view":meta["view"],"source":str(path),
                                     "transect_id":k+1,"valid":bool(np.isfinite(views[i,k])),"reason":reason,
                                     "width_px":float(views[i,k]) if np.isfinite(views[i,k]) else None,
                                     "difference_from_same_route_fixed_px":float(views[i,k]-fixed) if np.isfinite(views[i,k]+fixed) else None})
            del image
        np.savez_compressed(args.output/f"Beam{beam}_checks.npz",width_variants=width,gradient_widths=alternate,
                            half_depth_edges=old_edge,gradient_edges=paired_edge,repeatview_widths=views,loads_kN=loads)
        results.append({"beam":beam,"width":width,"alternate":alternate,"views":views,"prior":prior,
                        "old_edges":old_edge,"new_edges":paired_edge,"loads":loads})
    table(args.output/"edge_method_agreement.csv",edges); table(args.output/"location_variants.csv",locations)
    table(args.output/"repeatview_measurements.csv",repeats_rows); table(args.output/"variant_forecast_metrics.csv",scores)
    prepare_blind(blind,args.output)
    summary=summarize(results,edges,scores,repeats_rows)
    dump(args.output/"summary.json",summary); plots(results,edges,scores,args.output)
    receipt.update(execution="succeeded",retrieval="verified_local",ended_at_utc=datetime.now(timezone.utc).isoformat())
    print(json.dumps(summary,indent=2))


def finite_summary(values):
    values=np.array(values,float); good=values[np.isfinite(values)]
    return {"n":int(len(good)),"median":float(np.median(good)) if good.size else None,
            "p90":float(np.quantile(good,.9)) if good.size else None}


def summarize(results,edges,scores,repeat_rows):
    beams=[]
    for r in results:
        b=r["beam"]; er=[e for e in edges if e["beam"]==b and e["valid"]]
        coherent=np.nanmedian(r["width"],axis=2)
        growth=coherent[:,-1]-coherent[:,0]
        conservative_growth=float(np.min(coherent[:,-1])-np.max(coherent[:,0]))
        shifts=np.abs(r["width"][1:]-r["width"][0])
        same_stop=[]; common=0; route=[]
        for i,start in enumerate((0,4)):
            v=r["views"][start:start+4]; common+=int(np.isfinite(v).all(axis=0).sum())
            same_stop.extend(np.abs(v[1:]-v[0]).ravel().tolist())
            route.extend(np.abs(v[0]-r["width"][0,0 if start==0 else -1]).tolist())
        beams.append({"beam":b,"edge_valid":len(er),"edge_opportunities":int(r["alternate"].size),
                      "width_method_disagreement_px":finite_summary([abs(e["width_difference_px"]) for e in er]),
                      "boundary_method_disagreement_px":finite_summary([e["mean_absolute_edge_difference_px"] for e in er]),
                      "location_abs_difference_px":finite_summary(shifts.ravel()),
                      "coherent_first_last_median_growth_px":dict(zip([v[0] for v in VARIANTS],map(float,growth))),
                      "stage_independent_first_last_envelope_growth_px":conservative_growth,
                      "repeatview_valid":int(np.isfinite(r["views"]).sum()),"repeatview_opportunities":96,
                      "moving_fixed_disagreement_px":finite_summary(same_stop),"common_four_view_stop_transects":common,
                      "fixed_registration_route_disagreement_px":finite_summary(route)})
    aggregate=[]
    for name,_,_ in VARIANTS:
        losses={}; support=[]
        for a in ARMS:
            perbeam=[]
            for b in (4,5,6):
                items=[s for s in scores if s["beam"]==b and s["variant"]==name and s["arm"]==a and s["MAE_px"] is not None]
                perbeam.append(float(np.mean([s["MAE_px"] for s in items])) if items else np.nan)
                if a=="persistence": support.append(sum(s["scored_transects"] for s in items))
            losses[a]=float(np.mean(perbeam)) if np.isfinite(perbeam).all() else None
        aggregate.append({"variant":name,"equal_beam_MAE_px":losses,"scored_pair_transects":sum(support),
                          "secant_relative_change":losses["secant"]/losses["persistence"]-1 if losses["secant"] is not None else None})
    return {"run_id":"S03-E016-D01-R001","protocol":"development-v1","per_beam":beams,
            "variant_forecasts":aggregate,"reference_status":"PENDING_NO_INDEPENDENT_ANNOTATIONS",
            "blind_packet":{"unique_tasks":24,"views_including_duplicates":30,"completed_annotations":0},
            "formal_review":"pending","scientific_status":"DEVELOPMENT_DIAGNOSTIC_NOT_METROLOGY_VALIDATION"}


def plots(results,edges,scores,output):
    fig,axes=plt.subplots(2,3,figsize=(14,7),constrained_layout=True)
    for col,r in enumerate(results):
        for row,j in enumerate((0,len(r["loads"])-1)):
            profile=r["prior"]["profiles"][j,5]
            axes[row,col].plot(S,profile,color=".3",lw=1.2,label="gray profile")
            for i,x in enumerate(r["old_edges"][j,5]): axes[row,col].axvline(x,color="#0072B2",lw=1.3,label="half-depth" if i==0 else None)
            for i,x in enumerate(r["new_edges"][j,5]):
                if np.isfinite(x): axes[row,col].axvline(x,color="#D55E00",ls="--",lw=1.3,label="gradient edge" if i==0 else None)
            axes[row,col].set(title=f"Beam {r['beam']} | {r['loads'][j]:.0f} kN | transect 6",xlabel="Normal offset (native px)",ylabel="Raw grayscale",xlim=(-40,40),ylim=(0,255))
            axes[row,col].legend(fontsize=7)
    fig.suptitle("E016-D01-R001 | distinct algorithm boundary definitions, NOT independent reference truth")
    fig.savefig(output/"edge_operator_comparison.png",dpi=165); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    colors=["black","#0072B2","#56B4E9","#D55E00","#E69F00"]
    for ax,r in zip(axes,results):
        for v,(name,_,_) in enumerate(VARIANTS):
            ax.plot(r["loads"],np.nanmedian(r["width"][v],axis=1),"o-",lw=1.2,color=colors[v],label=name.replace("_"," "))
        ax.set(title=f"Beam {r['beam']}",xlabel="Nominal stage (kN)",ylabel="Median half-depth width (px)",ylim=(0,40))
        ax.legend(fontsize=7)
    fig.suptitle("All coherent +/-2 native-pixel location variants | all stages, no selected best path | development")
    fig.savefig(output/"location_growth_comparison.png",dpi=165); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    for ax,r in zip(axes,results):
        for i,start in enumerate((0,4)):
            views=r["views"][start:start+4]
            for v in range(1,4):
                valid=np.isfinite(views[0]+views[v]); ax.scatter(views[0,valid],views[v,valid],s=13,
                    c="#0072B2" if i==0 else "#D55E00",marker=["o","x","+"][v-1],alpha=.7)
        ax.plot([0,60],[0,60],"k--",lw=1)
        ax.set(title=f"Beam {r['beam']}",xlabel="Same-route fixed width (px)",ylabel="Moving-view width (px)",xlim=(0,60),ylim=(0,60))
    fig.suptitle("Real repeated nominal-stop views | blue=low / orange=high | unsupported/QC failures recorded, not plotted\nCamera/resolution/registration/within-hold change confounded; NOT pure repeatability error")
    fig.savefig(output/"repeatview_width_comparison.png",dpi=165); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
    for a,c in zip(ARMS,(".3","#0072B2","#D55E00")):
        vals=[]
        for name,_,_ in VARIANTS:
            vals.append(np.mean([np.mean([s["MAE_px"] for s in scores if s["beam"]==b and s["variant"]==name and s["arm"]==a and s["MAE_px"] is not None]) for b in (4,5,6)]))
        ax.plot(range(5),vals,"o-",color=c,label=a.replace("_"," "),lw=1.3)
    ax.set(xticks=range(5),xticklabels=[v[0].replace("_","\n") for v in VARIANTS],ylabel="Equal-beam one-step MAE (px)",ylim=(0,None))
    ax.legend(fontsize=8); ax.set_title("All frozen location variants / same forecast rules | E016-D01-R001, development")
    fig.savefig(output/"variant_forecast_comparison.png",dpi=165); plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("stage","profile","lock","repeat-source","repeat-transforms","output"): p.add_argument("--"+name,type=Path)
    p.add_argument("--self-test",action="store_true"); args=p.parse_args()
    if args.self_test: self_test(); return
    if any(getattr(args,k.replace("-","_")) is None for k in ("stage","profile","lock","repeat-source","repeat-transforms","output")): p.error("all input/output paths required")
    repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("commit source before diagnostic")
    if args.output.exists(): raise FileExistsError("fresh run output required")
    args.output.mkdir(parents=True); started=time.monotonic()
    receipt={"experiment_id":"S03-E016-D01","run_id":"S03-E016-D01-R001","protocol":"development-v1",
             "producer":"Mac-PIDL CPU offline diagnostic","hostname":socket.gethostname(),"pid":os.getpid(),
             "source_commit":git("rev-parse","HEAD"),"git_dirty":False,"command":sys.argv,"python":sys.executable,
             "started_at_utc":datetime.now(timezone.utc).isoformat(),"execution":"running","retrieval":"pending",
             "independent_reference":"pending_no_annotations","independent_code_review":"pending_development_only","gpu":None}
    dump(args.output/"run_receipt.json",receipt)
    run(args,receipt); receipt["runtime_seconds"]=time.monotonic()-started; dump(args.output/"run_receipt.json",receipt)


if __name__=="__main__": main()
