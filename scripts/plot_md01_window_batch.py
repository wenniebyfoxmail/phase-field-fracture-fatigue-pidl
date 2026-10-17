"""Saved-output E036 plots only; no registration/measurement/forecast selection."""
import argparse
import json
from pathlib import Path
import os
import socket
import subprocess
import sys
import time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image,ImageOps
from md01_early_relative import now,save
sys.path.insert(0,"/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import render_preview,audit_layout


def run(a):
    start=time.monotonic();started=now();a.output.mkdir(parents=True,exist_ok=False)
    cases=json.loads((a.target/"cases.json").read_text());summary=json.loads((a.target/"summary.json").read_text())
    lock=json.loads(a.lock.read_text());hist={w["id"]:json.loads((a.history/w["id"]/"history_snapshot.json").read_text()) for w in lock["windows"]}
    refs={w["id"]:json.loads((a.target/w["id"]/"target_measurement.json").read_text()) if (a.target/w["id"]/"target_measurement.json").exists() else None for w in lock["windows"]}
    arrays={}
    for w in lock["windows"]:
        arr={}
        for directory in (a.history/w["id"],a.target/w["id"]):
            if (directory/"profiles.npz").exists():
                with np.load(directory/"profiles.npz") as data:arr.update({k:data[k].copy() for k in data.files})
        arrays[w["id"]]=arr
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})
    qa={};prefix="S03-E036-MD01 R001/R002 | four fixed development windows, one source trajectory"
    scope="Native first-history px/window, not mm. Ordinal stage is not equal load/time; no independent-specimen or physical-accuracy claim."
    guides={
        "F01_case_predictions":("Each saved forecast versus the same fixed target","Four panels in fixed W12/W15/W18/W21 order. Black circles measured history/reference; grey squares persistence; blue triangles two-point stage trend. Dashed forecast segments start at origin. Target grey region indicates evaluation stage, not uncertainty. Shared y scale includes0. All observed widths and forecasts come from closed R001/R002 outputs; ineligible or unscorable cases stay labelled, not zero-filled."),
        "F02_gains_and_increments":("Per-case baseline gains, coverage and changing increments","Left: persistence grey squares and trend blue triangles absolute error for each window. Middle: gain=persistenceAE minus trendAE; right of0 trend better. Right: hollow circles previous increment d1,filled diamonds next increment d2, zero line and numerical labels. Categories are retrospective descriptors,never forecast inputs. No mean-only bars,CI,regression or independent-window population inference."),
        "F03_original_bands":("All fixed source-image supports","Rows W12/W15/W18/W21, columns historical1/historical2/target. Same420x320nativepx crop around fixed refined centre plus saved median translation when valid. No-trace cases display fixed native centre(4300,2200); invalid mapping displays first-frame centre without translation. These views are explicitly UNREGISTERED and carry no band. Green original normal band; orange crossing segment is saved half-depth readout,not human edge labels. Unopened targets remainblank. No enhancement,registration,profile remeasurement or target-driven centre change during rendering."),
        "F04_saved_profiles":("Unchanged half-depth readouts on all selected observations","Rows four windows, columns three stages; exact saved deficit profiles on shared grey-deficit and native normal offset axes. Grey shoulder zones|s|>=45,orange half-depth line andblack crossing segment when valid. QC reasons/missing retained. No smoothing,re-centering or profile recomputation; five-row median isone measurement,notfive samples."),
        "F05_W18_background_support":("Why W18 cannot supply a historical pair","Left Step18 andright Step19 show identical first-image-coordinate bounds without registration. Blue61px squares mark original four anchor footprints; dashedorange squares are the nominal zero-seeded search support61+2x80px,not independently matched peaks. No target20 opened. Individual original NCCscores are labelled,not recomputed; no template or search repair. Changed fixtures may occlude the region; visual evidence isnot calibrated displacement truth.")}
    def missing_label(r):
        h=hist[r["case"]]
        return "No first-history trace" if h["geometry"].get("no_identifiable_trace") else "Background match missing" if not r["E"] else r["reason"]
    def finish(fig,name):
        qa[name]=audit_layout(fig);stem=name+("_preview" if a.preview else "")
        text=f"# How to read {name}\n\n## Figure question\n\n{guides[name][0]}\n\n## Data provenance\n\nHistory {a.history}; target {a.target}; cases.json/summary.json/profiles.npz and frozen lock {a.lock}. Plot script scripts/plot_md01_window_batch.py at {subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}. Only saved quantities; original JPGs under {a.source} used only for F03 and F05.\n\n## Visual grammar and panel guide\n\n{guides[name][1]}\n\n## Key numerical takeaway\n\nCommon scoring {summary['common_scored']}/4; trend better {summary['trend_better']},ties {summary['tie']},persistence better {summary['persistence_better']},missing {summary['missing']}; mean paired delta={summary['mean_delta_abs_error_px']}px. Exact per-case gains: {[(r['case'],r['gain_px'],r['reason']) for r in cases]}. Original half-depth definition and previous scores unchanged.\n\n## Limitations and claim boundary\n\n{scope} Four correlated windows do not establish independent beam generalisation. Geometry observer-assisted on firsthistory only; background-to-crack correspondence and target reference are optical proxies,not physical truth. Retrospective slowing/reversal strata cannot be used at forecast origin. Missing cases retain denominator4; no error-based replacement.\n\n## Related assets\n\nR002/cases.csv and summary.json authoritative; README_analysis.md interprets outcomes. Preview is presentation only,not extra scoring. PNG/PDF share same-stem sidecar; grey retains marker/numeric redundancy.\n"
        (a.output/(stem+".md")).write_text(text)
        if a.preview:render_preview(fig,a.output/(stem+".png"),dpi=150)
        else:
            fig.savefig(a.output/(stem+".png"),dpi=300);fig.savefig(a.output/(stem+".pdf"))
            with Image.open(a.output/(stem+".png")) as im:ImageOps.grayscale(im).save(a.output/(stem+"_gray.png"),dpi=(300,300))
            (a.output/(stem+"_gray.md")).write_text(text)
        plt.close(fig)

    finite=[v for r in cases for v in (r["w1"],r["w2"],r["w3"],r["methods"]["persistence"]["prediction_px"],r["methods"]["stage_trend"]["prediction_px"]) if v is not None]
    ymax=max(finite,default=1)*1.25
    fig,axes=plt.subplots(2,2,figsize=(11,7.7),sharey=True,constrained_layout=True)
    for ax,r in zip(axes.flat,cases):
        stages=r["stages"];ys=[r["w1"],r["w2"],r["w3"]];ax.axvspan(stages[1]+.5,stages[2]+.25,color=".95")
        good=[(x,y) for x,y in zip(stages,ys) if y is not None]
        if good:ax.plot(*np.array(good).T,"o-",color="black",lw=1.3,label="Observed half-depth")
        for arm,color,marker in (("persistence",".5","s"),("stage_trend","#0072B2","^")):
            val=r["methods"][arm]["prediction_px"]
            if val is not None:
                ax.plot(stages[1:],[r["w2"],val],ls="--",color=color,lw=1.2)
                ax.scatter(stages[2],val,color=color,marker=marker,s=46,label="Persistence" if arm=="persistence" else "Two-point trend")
        title=f"{r['case']}: {stages[0]}/{stages[1]}/{stages[2]} | "+(r["stratum"].replace("_"," ") if r["stratum"] else missing_label(r))
        ax.set(title=title,xticks=stages,xlim=(stages[0]-.25,stages[-1]+.25),ylim=(0,ymax),xlabel="Ordinal stage",ylabel="Half-depth image width (native px)")
        vals=" / ".join("missing" if y is None else f"{y:.2f}" for y in ys)
        ax.text(.03,.94,"Observed: "+vals,transform=ax.transAxes,va="top",fontsize=9)
        if not r["common_scored"]:ax.text(.5,.45,"Not scored: "+missing_label(r),transform=ax.transAxes,ha="center",wrap=True,fontsize=9)
        ax.grid(alpha=.15)
    handles=[Line2D([],[],color="black",marker="o",label="Observed half-depth"),Line2D([],[],color=".5",marker="s",ls="--",label="Persistence"),Line2D([],[],color="#0072B2",marker="^",ls="--",label="Two-point trend")]
    fig.legend(handles=handles,loc="outside lower center",ncols=3,frameon=False)
    fig.suptitle(prefix+"\nSaved history-first forecasts; common scoring "+str(summary["common_scored"])+"/4",fontsize=12)
    finish(fig,"F01_case_predictions")

    fig,axes=plt.subplots(1,3,figsize=(13,4.8),constrained_layout=True)
    for i,r in enumerate(cases):
        if r["common_scored"]:
            for arm,col,m in (("persistence",".5","s"),("stage_trend","#0072B2","^")):
                v=r["methods"][arm]["abs_error_px"];axes[0].scatter(v,i,color=col,marker=m,s=45,label=arm if i==0 else None)
                axes[0].annotate(f"{v:.2f}",(v,i),xytext=(3,5 if arm=="persistence" else -13),textcoords="offset points",fontsize=8)
            axes[1].scatter(r["gain_px"],i,color="#0072B2",marker="o",s=42);axes[1].annotate(f"{r['gain_px']:+.2f}",(r["gain_px"],i),xytext=(4,5),textcoords="offset points",fontsize=9)
            for k,col,m,fill in (("d1",".35","o","none"),("d2","#D55E00","D","#D55E00")):
                axes[2].scatter(r[k],i,edgecolors=col,facecolors=fill,marker=m,s=46,label=k if i==0 else None)
                axes[2].annotate(f"{r[k]:+.2f}",(r[k],i),xytext=(3,5 if k=="d1" else -14),textcoords="offset points",fontsize=8)
        else:
            for ax in axes:ax.text(.02,i,missing_label(r),transform=ax.get_yaxis_transform(),fontsize=8,bbox=dict(facecolor="white",edgecolor="none",pad=1))
    for ax in axes:
        ax.set_yticks(range(4),[r["case"] for r in cases]);ax.set_ylim(3.5,-.5);ax.grid(axis="x",alpha=.15);ax.margins(x=.22)
    axes[0].set(xlabel="Absolute error (px)",title="Same-target errors");axes[0].set_xlim(left=0)
    axes[0].legend(handles=handles[1:],loc="upper right",fontsize=8,frameon=False)
    axes[1].axvline(0,color="black",lw=1);axes[1].set(xlabel="Persistence AE - trend AE (px)",title="Positive gain favours trend")
    axes[2].axvline(0,color="black",lw=1);axes[2].set(xlabel="Width increment (px / ordinal step)",title="Previous versus next increment")
    axes[2].legend(handles=[Line2D([],[],color=".35",marker="o",markerfacecolor="none",ls="none",label="Previous d1"),Line2D([],[],color="#D55E00",marker="D",ls="none",label="Next d2")],loc="upper right",fontsize=8,frameon=False)
    fig.suptitle(prefix+f"\nCoverage {summary['common_scored']}/4; slowing {summary['strata']['growth_deceleration']}, reversal {summary['strata']['direction_reversal']} (retrospective)",fontsize=12)
    finish(fig,"F02_gains_and_increments")

    fig,axes=plt.subplots(4,3,figsize=(12,12),constrained_layout=True)
    for i,w in enumerate(lock["windows"]):
        h=hist[w["id"]];g=h["geometry"];rr=h["history"]+[refs[w["id"]]]
        for j,(ax,f,r) in enumerate(zip(axes[i],w["files"],rr)):
            ax.set_title(f"{w['id']} | Step{f['step']} | {f['filename']}",fontsize=9);ax.set_xticks([]);ax.set_yticks([])
            if r is None:
                ax.text(.5,.5,"Target not opened",transform=ax.transAxes,ha="center");continue
            mapped="center" in g and r["registration"].get("valid")
            center=np.array(g.get("center",[4300,2200]))
            if mapped:center=center+[r["registration"]["dx"],r["registration"]["dy"]]
            x0,y0=np.floor(center-[210,160]).astype(int);x1,y1=x0+420,y0+320
            with Image.open(a.source/f["filename"]) as raw:crop=ImageOps.exif_transpose(raw).convert("RGB").crop((x0,y0,x1,y1))
            ax.imshow(crop,extent=[x0-center[0]-.5,x1-center[0]-.5,y1-center[1]-.5,y0-center[1]-.5])
            if not mapped:
                ax.text(.02,.98,"UNREGISTERED: "+missing_label(cases[i]),va="top",fontsize=8,transform=ax.transAxes,color="white",bbox=dict(facecolor="black",alpha=.6));continue
            n=np.array(g["normal"]);band=np.array([-60*n,60*n]);ax.plot(*band.T,color="#009E73",lw=1.4)
            m=r["measurement"]
            if m["valid"]:
                xy=np.array([m["left_crossing_px"]*n,m["right_crossing_px"]*n]);ax.plot(*xy.T,"o-",color="#D55E00",ms=3,lw=1.8)
            else:ax.text(.02,.98,m["reason"],va="top",transform=ax.transAxes,color="white",bbox=dict(facecolor="black",alpha=.5))
    fig.suptitle(prefix+"\nAll raw 420 x 320 native-px crops | green=fixed band; orange=saved half-depth width",fontsize=12)
    finish(fig,"F03_original_bands")

    extrema=[float(np.max(v)) for ar in arrays.values() for k,v in ar.items() if k.endswith("_deficit")]
    minima=[float(np.min(v)) for ar in arrays.values() for k,v in ar.items() if k.endswith("_deficit")]
    fig,axes=plt.subplots(4,3,figsize=(12,10),sharex=True,sharey=True,constrained_layout=True)
    for i,w in enumerate(lock["windows"]):
        rr=hist[w["id"]]["history"]+[refs[w["id"]]];arr=arrays[w["id"]]
        for ax,f,r in zip(axes[i],w["files"],rr):
            ax.set_title(f"{w['id']} | Step{f['step']}",fontsize=9);ax.axvspan(-60,-45,color=".93");ax.axvspan(45,60,color=".93")
            k=f"s{f['step']}_deficit"
            if k in arr:
                ax.plot(arr["offsets"],arr[k],color="#0072B2",lw=1.2);m=r["measurement"]
                if m["valid"]:
                    level=m["depth_gray"]/2;ax.axhline(level,color="#D55E00",ls="--",lw=.8)
                    ax.plot([m["left_crossing_px"],m["right_crossing_px"]],[level,level],color="black",lw=2)
                ax.text(.02,.94,(f"Width {m['fwhm_native_px']:.2f}px" if m["valid"] else m["reason"]),transform=ax.transAxes,va="top",fontsize=8)
            else:ax.text(.5,.5,"Not opened" if r is None else r["measurement"]["reason"],transform=ax.transAxes,ha="center",fontsize=8)
            ax.set(xlim=(-60,60),ylim=(min(minima,default=0)-5,max(extrema,default=1)+20));ax.grid(alpha=.12)
    for ax in axes[-1]:ax.set_xlabel("Normal offset (native px)")
    for ax in axes[:,0]:ax.set_ylabel("Background - grey value")
    fig.suptitle(prefix+"\nExact saved five-row median deficits; original half-depth operator unchanged",fontsize=12)
    finish(fig,"F04_saved_profiles")
    w=next(w for w in lock["windows"] if w["id"]=="W18");h=hist["W18"];g=h["geometry"]
    fig,axes=plt.subplots(1,2,figsize=(11,5.9),constrained_layout=True)
    for j,(ax,f) in enumerate(zip(axes,w["files"][:2])):
        bounds=(3800,2200,4800,2900)
        with Image.open(a.source/f["filename"]) as raw:crop=ImageOps.exif_transpose(raw).convert("RGB").crop(bounds)
        ax.imshow(crop,extent=[3800-.5,4800-.5,2900-.5,2200-.5])
        for k,(x,y) in enumerate(g["background_centers"]):
            ax.add_patch(Rectangle((x-30-.5,y-30-.5),61,61,fill=False,edgecolor="#56B4E9",lw=1.4))
            if j:
                ax.add_patch(Rectangle((x-110-.5,y-110-.5),221,221,fill=False,edgecolor="#D55E00",ls="--",lw=1))
                score0=h["history"][1]["registration"]["patches"][k]["correlation"]
                ax.text(x-25,y-115,f"A{k+1}: NCC {score0:.3f}",color="white",fontsize=8,bbox=dict(facecolor="black",alpha=.6))
            else:ax.text(x-20,y-40,f"A{k+1}",color="white",fontsize=9,bbox=dict(facecolor="black",alpha=.6))
        ax.set(title=f"Step{f['step']} | {f['filename']} | unregistered coordinates",xlabel="Original native x (px)",ylabel="Original native y (px)")
    fig.suptitle(prefix+"\nW18 source-support diagnosis only | fixed61px templates / zero-seeded search +/-80px",fontsize=11)
    finish(fig,"F05_W18_background_support")
    save(a.output/"layout_audit.json",qa)
    save(a.output/"run_receipt.json",dict(render_only=True,no_new_measurement=True,execution="succeeded",retrieval="verified_local",started_at_utc=started,ended_at_utc=now(),wall_seconds=time.monotonic()-start,host=socket.gethostname(),pid=os.getpid(),command=sys.argv,commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines()))
    print(json.dumps(qa,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("history","target","source","lock","output"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--preview",action="store_true");run(p.parse_args())
