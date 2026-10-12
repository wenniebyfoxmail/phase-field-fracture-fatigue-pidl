#!/usr/bin/env python3
"""First-image-locked native crack-profile diagnostic; not physical metrology."""
import argparse
import csv
from datetime import datetime, timezone
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
from PIL import Image, ImageOps

from d01_directional_scale_repeatability import crc32_file
from d01_stage_forecast_diagnostic import ARMS, BOXES, dump, write_csv

# Visually estimated on the first image ONLY, displayed at 1920x1280.
# Native conversion is by image dimensions, not the old 2000px working scale.
PREVIEW_KNOTS = {
    4: [(1697,435),(1689,485),(1685,530),(1670,575),(1650,620),(1635,665),
        (1628,710),(1625,755),(1610,800),(1595,845),(1592,890),(1602,935)],
    5: [(1400,490),(1374,530),(1350,570),(1324,610),(1304,650),(1280,690),
        (1265,730),(1250,770),(1217,804),(1178,827),(1143,850),(1105,886)],
    6: [(1371,598),(1339,620),(1301,644),(1263,667),(1228,695),(1194,725),
        (1160,751),(1136,780),(1125,815),(1103,852),(1070,885),(1028,918)],
}
S = np.arange(-60.,60.001,.25)
COLORS = {"persistence":"#555555","secant":"#0072B2","conservative_secant":"#D55E00"}


def native_gray(path):
    with Image.open(path) as im:
        return np.asarray(ImageOps.exif_transpose(im).convert("L"),dtype=np.float32)


def native_homography(h, native_shape, working_shape):
    """OpenCV resize pixel centers: xw=(xn+.5)*sx-.5, independently for y."""
    sy=working_shape[0]/native_shape[0]; sx=working_shape[1]/native_shape[1]
    t=np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])
    return np.linalg.inv(t)@h@t


def sample_profile(image, h_native, center, normal, tangent_shift=0.):
    center=np.asarray(center,float); normal=np.asarray(normal,float)
    tangent=np.array([-normal[1],normal[0]])
    points=(center[None,None,:]+S[None,:,None]*normal[None,None,:]
            +(np.arange(-2,3)+tangent_shift)[:,None,None]*tangent[None,None,:])
    homogeneous=np.concatenate([points,np.ones((*points.shape[:2],1))],axis=2)
    mapped=homogeneous@np.linalg.inv(h_native).T
    mapped=mapped[...,:2]/mapped[...,2:]
    if (not np.isfinite(mapped).all() or mapped[...,0].min()<1 or
        mapped[...,1].min()<1 or mapped[...,0].max()>image.shape[1]-2 or
        mapped[...,1].max()>image.shape[0]-2):
        raise ValueError("profile support leaves source image")
    values=cv2.remap(image,mapped[...,0].astype(np.float32),mapped[...,1].astype(np.float32),
                     cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    return np.median(values,axis=0)


def measure(profile, search_radius=15.):
    left=(S<=-45); right=(S>=45)
    lx=float(np.median(S[left])); rx=float(np.median(S[right]))
    lv=float(np.median(profile[left])); rv=float(np.median(profile[right]))
    background=lv+(rv-lv)*(S-lx)/(rx-lx)
    deficit=background-profile
    shoulder=(left|right); residual=deficit[shoulder]
    noise=float(1.4826*np.median(np.abs(residual-np.median(residual))))
    indices=np.flatnonzero(np.abs(S)<=search_radius)
    peak=int(indices[np.argmax(deficit[indices])]); depth=float(deficit[peak])
    threshold=max(10.,3*noise)
    result={"peak_offset_native_px":float(S[peak]),"depth_gray":depth,
            "shoulder_noise_gray":noise,"qc_threshold_gray":threshold,
            "relative_contrast":depth/max(float(background[peak]),1.),
            "fwhm_native_px":None,"left_crossing_px":None,"right_crossing_px":None,
            "valid":False,"reason":"low_contrast"}
    if depth<threshold: return result,deficit,background
    level=depth/2; lo=hi=peak
    while lo>0 and deficit[lo]>=level: lo-=1
    while hi<len(S)-1 and deficit[hi]>=level: hi+=1
    if lo==0 or hi==len(S)-1:
        result["reason"]="censored_window"; return result,deficit,background
    # Linear interpolation at both half-depth crossings.
    xlo=float(S[lo]+(S[lo+1]-S[lo])*(level-deficit[lo])/(deficit[lo+1]-deficit[lo]))
    xhi=float(S[hi-1]+(S[hi]-S[hi-1])*(level-deficit[hi-1])/(deficit[hi]-deficit[hi-1]))
    width=xhi-xlo
    result.update(fwhm_native_px=width,left_crossing_px=xlo,right_crossing_px=xhi,
                  valid=bool(width>=1),reason="ok" if width>=1 else "resolution_limited")
    return result,deficit,background


def forecast(history, loads, next_load, arm):
    if len(history)!=len(loads) or len(history)<2 or not np.isfinite(history).all():
        raise ValueError("aligned finite historical widths required")
    dl=loads[-1]-loads[-2]
    if dl<=0 or next_load<=loads[-1]: raise ValueError("strict load order required")
    factor={"persistence":0.,"secant":1.,"conservative_secant":.5}[arm]
    return np.clip(history[-1]+factor*(history[-1]-history[-2])*(next_load-loads[-1])/dl,0,120)


def self_test():
    for sigma in (1.5,3.,8.):
        profile=180+.02*S-100*np.exp(-S*S/(2*sigma*sigma))
        result,_,_=measure(profile)
        assert result["valid"]
        assert abs(result["fwhm_native_px"]-2*np.sqrt(2*np.log(2))*sigma)<.04
        transformed,_,_=measure(profile*.7+20)
        assert abs(result["fwhm_native_px"]-transformed["fwhm_native_px"])<1e-10
    assert not measure(np.full(S.shape,180.))[0]["valid"]
    assert not measure(180-100*np.exp(-(S-60)**2/(2*3**2)),60)[0]["valid"]
    h=np.array([[1.,.003,2.],[0,1,-3],[0,0,1]])
    hn=native_homography(h,(3744,5616),(1333,2000))
    assert np.allclose(native_homography(np.eye(3),(3744,5616),(1333,2000)),np.eye(3))
    assert abs(hn[1,2]+3*3744/1333)<1e-10
    assert np.allclose(forecast(np.array([[10.],[14.]]),[10,30],40,"secant"),16.)
    assert np.allclose(forecast(np.array([[10.],[14.]]),[10,30],40,"conservative_secant"),15.)
    sequence=np.array([[10.],[14.],[50.]])
    prior=forecast(sequence[:2],[10,30],40,"secant"); sequence[2]=0
    assert np.array_equal(prior,forecast(sequence[:2],[10,30],40,"secant"))
    image=np.arange(240,dtype=np.float32)[None,:]*np.ones((200,1),np.float32)
    profile=sample_profile(image,np.eye(3),[120,100],[1,0])
    assert np.allclose(profile,120+S)
    print("Gaussian widths, affine intensity, weak/censored profiles, native geometry, prefix-only forecast and sampler: passed")


def prepare(source, output, receipt):
    groups=json.loads((source/"selected_sequences_before_pixel_access.json").read_text())["groups"]
    lock={"protocol":"development-v1","source_run":str(source),"beams":{}}
    previews=[]
    for beam in (4,5,6):
        state=groups[str(beam)][0]; im=native_gray(source/"raw_images"/state["saved_as"])
        if im.shape!=(3744,5616): raise ValueError("unexpected native shape")
        points=np.array(PREVIEW_KNOTS[beam],float)*np.array([im.shape[1]/1920,im.shape[0]/1280])
        tangents=np.gradient(points,axis=0); tangents/=np.linalg.norm(tangents,axis=1)[:,None]
        normals=np.column_stack([-tangents[:,1],tangents[:,0]])
        control=BOXES[beam][1]; cx=(control[0]+control[2])/2
        ys=np.linspace(control[1]+80,control[3]-80,len(points))
        records=[]
        for i,(p,n) in enumerate(zip(points,normals)):
            found,_,_=measure(sample_profile(im,np.eye(3),p,n),40)
            refined=p+n*found["peak_offset_native_px"]
            check,_,_=measure(sample_profile(im,np.eye(3),refined,n))
            records.append({"id":i+1,"rough_center":p.tolist(),"center":refined.tolist(),
                            "normal":n.tolist(),"control_center":[cx,float(ys[i])],
                            "origin_valid":check["valid"],"origin_qc":check})
        lock["beams"][str(beam)]={"origin_source":state["saved_as"],"native_shape":list(im.shape),
                                     "working_shape":[1333,2000],"transects":records}
        previews.append((beam,im,records))
    dump(output/"first_frame_transects_lock.json",lock)
    fig,axes=plt.subplots(2,3,figsize=(14,9),constrained_layout=True)
    for col,(beam,im,records) in enumerate(previews):
        axes[0,col].imshow(im,cmap="gray",vmin=0,vmax=255)
        axes[1,col].imshow(im,cmap="gray",vmin=0,vmax=255)
        centers=np.array([r["center"] for r in records])
        axes[0,col].plot(*centers.T,color="#D55E00",lw=1)
        for record in records:
            p=np.array(record["center"]); n=np.array(record["normal"]); c=np.array(record["control_center"])
            color="#009E73" if record["origin_valid"] else "#CC79A7"
            for ax in axes[:,col]:
                ax.plot(*np.array([p-60*n,p+60*n]).T,color=color,lw=1.4)
                ax.text(*(p+75*n),str(record["id"]),color=color,fontsize=8)
            axes[0,col].plot(*np.array([c-60*n,c+60*n]).T,color="#0072B2",lw=1)
        axes[0,col].set_title(f"Beam {beam} | first 10 kN image only")
        axes[1,col].set_xlim(centers[:,0].min()-150,centers[:,0].max()+150)
        axes[1,col].set_ylim(centers[:,1].max()+100,centers[:,1].min()-100)
        axes[1,col].set_title("Locked path / transverse sampling (native pixels)")
        for ax in axes[:,col]: ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("S03-E015-D01-R000 | observer-assisted origin-only geometry, NOT reference masks\nGreen=origin QC detected; purple=weak; blue=background negative controls")
    fig.savefig(output/"first_frame_transects.png",dpi=170); plt.close(fig)
    receipt.update(execution="succeeded",retrieval="verified_local",origin_only=True,
                   ended_at_utc=datetime.now(timezone.utc).isoformat())
    dump(output/"run_receipt.json",receipt)
    print(json.dumps({b:sum(r["origin_valid"] for r in x["transects"]) for b,x in lock["beams"].items()}))


def evaluate(source, lock_path, output, receipt):
    lock=json.loads(lock_path.read_text())
    if Path(lock["source_run"]).resolve()!=source.resolve(): raise ValueError("source/lock mismatch")
    groups=json.loads((source/"selected_sequences_before_pixel_access.json").read_text())["groups"]
    acquisitions={r["saved_as"]:r for r in json.loads((source/"acquisition_receipt.json").read_text())}
    rows=[]; scores=[]; predictions=[]; results=[]
    for beam in (4,5,6):
        states=groups[str(beam)]; geometry=lock["beams"][str(beam)]; transects=geometry["transects"]
        old=np.load(source/f"Beam{beam}_stage_fields.npz")
        loads=np.array([s["nominal_load_kN"] for s in states],float)
        if not np.array_equal(loads,old["nominal_loads_kN"]): raise ValueError("stage mismatch")
        if geometry["origin_source"]!=states[0]["saved_as"]: raise ValueError("origin mismatch")
        widths=np.full((len(states),len(transects)),np.nan); controls=widths.copy(); sensitivities=widths.copy()
        all_profiles=[]; deficits=[]
        for j,state in enumerate(states):
            path=source/"raw_images"/state["saved_as"]; identity=acquisitions[state["saved_as"]]
            if path.stat().st_size!=identity["bytes"] or crc32_file(path)!=identity["crc32"]:
                raise ValueError("source size/CRC changed")
            image=native_gray(path)
            if list(image.shape)!=geometry["native_shape"]: raise ValueError("native geometry changed")
            h=native_homography(old["homographies"][j],image.shape,geometry["working_shape"])
            profiles=[]; ds=[]
            for k,t in enumerate(transects):
                for role,center in (("crack",t["center"]),("control",t["control_center"])):
                    p=sample_profile(image,h,center,t["normal"])
                    found,d,bg=measure(p)
                    row={"beam":beam,"stage_index":j,"load_kN":float(loads[j]),"source":str(path),
                         "transect_id":t["id"],"role":role,"origin_eligible":t["origin_valid"],**found}
                    rows.append(row)
                    if role=="control":
                        if found["valid"]: controls[j,k]=found["fwhm_native_px"]
                        continue
                    profiles.append(p); ds.append(d)
                    if found["valid"]:
                        widths[j,k]=found["fwhm_native_px"]
                        shifted=[]
                        for offset in (-2.,2.):
                            test,_,_=measure(sample_profile(image,h,center,t["normal"],offset))
                            if test["valid"]: shifted.append(abs(test["fwhm_native_px"]-widths[j,k]))
                        if len(shifted)==2: sensitivities[j,k]=max(shifted)
            all_profiles.append(profiles); deficits.append(ds)
        eligible=np.array([t["origin_valid"] for t in transects],bool)
        pred={a:[] for a in ARMS}
        for current in range(1,len(states)-1):
            support=eligible & np.isfinite(widths[current-1:current+2]).all(axis=0)
            count=int(support.sum())
            for arm in ARMS:
                vector=np.full(len(transects),np.nan)
                if count:
                    vector[support]=forecast(widths[current-1:current+1,support],loads[current-1:current+1],loads[current+1],arm)
                pred[arm].append(vector)
                loss=float(np.abs(vector[support]-widths[current+1,support]).mean()) if count else None
                scores.append({"beam":beam,"origin_kN":float(loads[current]),"target_kN":float(loads[current+1]),
                               "arm":arm,"eligible_transects":int(eligible.sum()),"scored_transects":count,
                               "coverage":count/max(int(eligible.sum()),1),"MAE_native_px":loss})
                for k in np.flatnonzero(support):
                    predictions.append({"beam":beam,"origin_kN":float(loads[current]),"target_kN":float(loads[current+1]),
                                        "transect_id":int(k+1),"arm":arm,"observed_width_px":float(widths[current+1,k]),
                                        "predicted_width_px":float(vector[k]),"abs_error_px":float(abs(vector[k]-widths[current+1,k]))})
        pred={a:np.array(v) for a,v in pred.items()}
        profiles=np.array(all_profiles); deficit=np.array(deficits)
        np.savez_compressed(output/f"Beam{beam}_profiles.npz",normal_offsets_native_px=S,profiles=profiles,deficits=deficit,
                            widths=widths,control_widths=controls,tangent_shift_sensitivity=sensitivities,
                            eligible=eligible,loads_kN=loads,**{a+"_predictions":v for a,v in pred.items()})
        results.append({"beam":beam,"loads":loads,"widths":widths,"controls":controls,"profiles":profiles,
                        "deficits":deficit,"sensitivity":sensitivities,"eligible":eligible,"predictions":pred})
    write_csv(output/"profile_measurements.csv",rows); write_csv(output/"forecast_metrics.csv",scores)
    if predictions: write_csv(output/"individual_forecasts.csv",predictions)
    beams=[]
    for r in results:
        beam=r["beam"]; beam_scores=[s for s in scores if s["beam"]==beam]
        values={a:float(np.mean([s["MAE_native_px"] for s in beam_scores if s["arm"]==a and s["MAE_native_px"] is not None])) for a in ARMS}
        if not np.isfinite(list(values.values())).all(): raise ValueError("no computable beam comparison")
        changes=np.abs(np.diff(r["widths"],axis=0))
        beams.append({"beam":beam,"states":len(r["loads"]),"origin_eligible":int(r["eligible"].sum()),
                      "valid_crack_profiles":int(np.isfinite(r["widths"]).sum()),"profile_opportunities":int(r["widths"].size),
                      "background_detections":int(np.isfinite(r["controls"]).sum()),
                      "median_width_first_px":float(np.nanmedian(r["widths"][0])),
                      "median_width_last_px":float(np.nanmedian(r["widths"][-1])),
                      "median_absolute_stage_change_px":float(np.nanmedian(changes)),
                      "median_tangent_shift_sensitivity_px":float(np.nanmedian(r["sensitivity"])),
                      "scored_pair_transects":sum(s["scored_transects"] for s in beam_scores if s["arm"]=="persistence"),
                      "eligible_pair_transects":int(r["eligible"].sum())*(len(r["loads"])-2),**values})
    aggregate={a:float(np.mean([b[a] for b in beams])) for a in ARMS}
    summary={"run_id":"S03-E015-D01-R001","protocol":"development-v1","states":14,"independent_beams":3,
             "forecast_pairs":8,"transects_per_beam":12,"per_beam":beams,"equal_beam_MAE_native_px":aggregate,
             "relative_change_vs_persistence":{a:aggregate[a]/aggregate["persistence"]-1 for a in ARMS[1:]},
             "scientific_verdict":"DEVELOPMENT_DIAGNOSTIC_ONLY","physical_width_validated":False,
             "held_out_generalisation":False,"formal_review":"pending"}
    dump(output/"summary.json",summary); figures(results,beams,output)
    receipt.update(execution="succeeded",retrieval="verified_local",lock_path=str(lock_path),
                   ended_at_utc=datetime.now(timezone.utc).isoformat())
    dump(output/"run_receipt.json",receipt); print(json.dumps(summary,indent=2))


def figures(results,beams,output):
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    for col,r in enumerate(results):
        # Fixed ID 6 for every beam, NOT chosen by errors or visibility.
        for j,load in enumerate(r["loads"]):
            axes[0,col].plot(S,r["profiles"][j,5],label=f"{load:.0f} kN",lw=1)
            axes[1,col].plot(S,r["deficits"][j,5],label=f"{load:.0f} kN",lw=1)
        axes[0,col].set(title=f"Beam {r['beam']} | fixed transect 6",ylabel="Raw grayscale (0..255)",ylim=(0,255))
        axes[0,col].legend(fontsize=8); axes[1,col].set(ylabel="Local intensity deficit",xlabel="Normal offset (native px)",xlim=(-35,35))
    low=min(float(r["deficits"].min()) for r in results); high=max(float(r["deficits"].max()) for r in results)
    for ax in axes[1]: ax.set_ylim(low-5,high+5)
    fig.suptitle("S03-E015-D01-R001 | all stages at a fixed preselected transect | controlled lab, development")
    fig.savefig(output/"transverse_profiles.png",dpi=170); plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    vmax=max(float(np.nanmax(r["widths"])) for r in results)
    for col,(r,b) in enumerate(zip(results,beams)):
        masked=np.ma.masked_invalid(r["widths"].T)
        cmap=plt.get_cmap("viridis").copy(); cmap.set_bad("#eeeeee")
        m=axes[0,col].imshow(masked,origin="lower",aspect="auto",cmap=cmap,vmin=0,vmax=vmax)
        axes[0,col].set(xticks=np.arange(len(r["loads"])),xticklabels=[f"{x:.0f}" for x in r["loads"]],
                        yticks=[0,5,11],yticklabels=["1","6","12"],xlabel="Nominal stage (kN)",ylabel="Fixed transect ID",
                        title=f"Beam {r['beam']} | detected {b['valid_crack_profiles']}/{b['profile_opportunities']}")
        for k in range(12): axes[1,col].plot(r["loads"],r["widths"][:,k],color=".75",lw=.7)
        axes[1,col].plot(r["loads"],np.nanmedian(r["widths"],axis=1),"ko-",lw=1.5,label="median of valid profiles")
        axes[1,col].set(xlabel="Nominal stage (kN)",ylabel="Half-depth width (native px)",ylim=(0,vmax*1.05))
        axes[1,col].legend(fontsize=8)
    fig.colorbar(m,ax=list(axes[0]),fraction=.02,pad=.015,label="Image half-depth width, native px")
    fig.suptitle("All 36 locked transects / all 14 stages | gray=missing QC, NOT zero | not physical aperture")
    fig.savefig(output/"crack_width_trajectories.png",dpi=170); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    for ax,r,b in zip(axes,results,beams):
        for a in ARMS:
            pred=r["predictions"][a]; losses=[]
            for j,vector in enumerate(pred):
                support=np.isfinite(vector)
                losses.append(np.abs(vector[support]-r["widths"][j+2,support]).mean() if support.any() else np.nan)
            ax.plot(r["loads"][2:],losses,"o-",color=COLORS[a],lw=1.3,label=a.replace("_"," "))
        ax.set(title=f"Beam {r['beam']} | {b['scored_pair_transects']}/{b['eligible_pair_transects']} scored",xlabel="Next nominal stage (kN)",ylabel="Same-support one-step width MAE (px)",ylim=(0,None))
        ax.legend(fontsize=7)
    ymax=max(ax.get_ylim()[1] for ax in axes)
    for ax in axes: ax.set_ylim(0,ymax)
    fig.suptitle("S03-E015-D01-R001 | observed-history updates, 8 origins, no held-out beams | development")
    fig.savefig(output/"profile_forecast_comparison.png",dpi=170); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path); parser.add_argument("--output",type=Path)
    parser.add_argument("--lock",type=Path); parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test: self_test(); return
    if not args.source or not args.output or (not args.prepare and not args.lock): parser.error("source/output and prepare or lock required")
    repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("commit source before execution")
    if args.output.exists(): raise FileExistsError("fresh output required")
    args.output.mkdir(parents=True)
    started=time.monotonic()
    receipt={"experiment_id":"S03-E015-D01","run_id":"S03-E015-D01-R000" if args.prepare else "S03-E015-D01-R001",
             "protocol":"development-v1","producer":"Mac-PIDL CPU offline diagnostic","hostname":socket.gethostname(),
             "pid":os.getpid(),"source_commit":git("rev-parse","HEAD"),"git_dirty":False,"python":sys.executable,
             "command":sys.argv,"started_at_utc":datetime.now(timezone.utc).isoformat(),"execution":"running",
             "retrieval":"pending","independent_review":"pending_development_only","gpu":None}
    dump(args.output/"run_receipt.json",receipt)
    if args.prepare: prepare(args.source,args.output,receipt)
    else: evaluate(args.source,args.lock,args.output,receipt)
    receipt["runtime_seconds"]=time.monotonic()-started
    dump(args.output/"run_receipt.json",receipt)


if __name__=="__main__": main()
