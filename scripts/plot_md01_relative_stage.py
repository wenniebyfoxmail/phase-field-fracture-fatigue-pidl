"""Saved-output visualization only; never measures profiles or predicts."""
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0,"/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout


def main(a):
    t=time.monotonic()
    started_at=datetime.now(timezone.utc).isoformat()
    a.output.mkdir(parents=True,exist_ok=False)
    h=json.loads((a.history/"predictions_saved_before_target.json").read_text())
    target=json.loads((a.target/"measurements.json").read_text())
    summary=json.loads((a.target/"summary.json").read_text())
    records=h["history"]+target
    data={}
    for folder in (a.history,a.target):
        with np.load(folder/"profiles.npz") as f:
            data.update({k:f[k] for k in f.files})
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                         "font.family":"DejaVu Sans","pdf.fonttype":42})
    colors=("#666666","#0072B2","#D55E00")
    qa={}

    def finish(fig,name):
        qa[name]=audit_layout(fig)
        fig.savefig(a.output/(name+".png"),dpi=300)
        fig.savefig(a.output/(name+".pdf"))
        with Image.open(a.output/(name+".png")) as im:
            ImageOps.grayscale(im).save(a.output/(name+"_gray.png"),dpi=(300,300))
        plt.close(fig)

    fig,axes=plt.subplots(2,3,figsize=(12,7.5),constrained_layout=True)
    for j,rec in enumerate(records):
        with Image.open(a.source/rec["filename"]) as image:
            image=ImageOps.exif_transpose(image).convert("RGB")
            preview=image.copy()
            preview.thumbnail((1500,1000))
            axes[0,j].imshow(preview,extent=[0,image.width,image.height,0])
            shift=np.array([rec["registration"]["dx"] or 0,rec["registration"]["dy"] or 0])
            center=np.array(h["geometry"]["center"])+shift
            normal=np.array(h["geometry"]["normal"])
            x0,y0=np.floor(center-[350,275]).astype(int)
            x1,y1=x0+700,y0+550
            axes[0,j].add_patch(Rectangle((x0,y0),700,550,fill=False,color="#009E73",lw=1.4))
            axes[1,j].imshow(image.crop((x0,y0,x1,y1)),extent=[x0,x1,y1,y0])
            for p in h["geometry"]["background_centers"]:
                q=np.array(p)+shift
                axes[1,j].add_patch(Rectangle(q-40,81,81,fill=False,color="#56B4E9",lw=1))
            band=np.array([center-60*normal,center+60*normal])
            axes[1,j].plot(*band.T,color="#009E73",lw=1.5)
            m=rec["measurement"]
            if m["valid"]:
                endpoints=np.array([center+normal*m[k] for k in ("left_crossing_px","right_crossing_px")])
                axes[1,j].scatter(*endpoints.T,color="#D55E00",s=22,marker="x",linewidths=1.5)
            role="target: opened after prediction save" if j==2 else "history"
            axes[0,j].set_title(f"Step {rec['stage']} | {rec['filename']}\n{role}",fontsize=10)
            axes[1,j].set_title("Raw native crop; fixed band + mapped anchors",fontsize=9)
            for ax in axes[:,j]: ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("S03-E031-MD01 R001/R002 | controlled experiment, one fixed transect\nGreen: sampling band / crop; orange: half-depth crossings; blue: background patches",fontsize=12)
    finish(fig,"F01_originals_and_sampling")

    fig,axes=plt.subplots(1,3,figsize=(12,3.7),sharey=True,constrained_layout=True)
    ymin=min(float(data[f"s{r['stage']}_deficit"].min()) for r in records)
    ymax=max(float(data[f"s{r['stage']}_deficit"].max()) for r in records)
    for j,(ax,rec) in enumerate(zip(axes,records)):
        m=rec["measurement"]
        s=data["offsets"]
        ax.plot(s,data[f"s{rec['stage']}_deficit"],color=colors[j],lw=1.5)
        ax.axhline(m["depth_gray"]/2,color=colors[j],ls="--",lw=1)
        if m["valid"]:
            ax.hlines(m["depth_gray"]/2,m["left_crossing_px"],m["right_crossing_px"],color="black",lw=2)
            for key in ("left_crossing_px","right_crossing_px"):
                ax.plot(m[key],m["depth_gray"]/2,"ko",ms=3)
        ax.axvspan(-60,-45,color=".9",zorder=-2)
        ax.axvspan(45,60,color=".9",zorder=-2)
        width=f"{m['fwhm_native_px']:.3f} px" if m["valid"] else m["reason"]
        ax.set(title=f"Step {rec['stage']} | {width}",xlabel="Normal offset (native px)",xlim=(-60,60),ylim=(ymin-5,ymax+8))
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Background minus grayscale intensity")
    fig.suptitle("S03-E031-MD01 R001/R002 | unchanged half-depth, five-line median profiles\nDashed: half local depth; black segment: measured image width; grey: shoulders",fontsize=11)
    finish(fig,"F02_halfdepth_profiles")

    fig,axes=plt.subplots(1,2,figsize=(9,4.3),constrained_layout=True)
    widths=[r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else np.nan for r in records]
    stages=[r["stage"] for r in records]
    ax=axes[0]
    ax.plot(stages,widths,"ko-",lw=1.2,label="Measured optical width")
    for arm,color,marker in (("persistence","#666666","s"),("secant","#0072B2","^")):
        value=h["predictions"][arm]
        if value is not None:
            ax.plot([28,29],[widths[1],value],ls="--",color=color,lw=1.3)
            ax.scatter(29,value,color=color,marker=marker,s=60,label=f"{arm}: {value:.3f} px",zorder=4)
    ax.set(xlabel="Relative stage index (not kN or seconds)",ylabel="Half-depth image width (native px)",xticks=stages,
           ylim=(0,max([v for v in widths if np.isfinite(v)]+[h["predictions"].get("secant") or 0])*1.3))
    ax.legend(loc="upper left",fontsize=8,frameon=False)
    ax.grid(alpha=.15)
    errors=[summary[arm+"_abs_error_px"] for arm in ("persistence","secant")]
    for i,(error,color,marker) in enumerate(zip(errors,("#666666","#0072B2"),("s","^"))):
        if error is not None:
            axes[1].scatter(i,error,c=color,marker=marker,s=70)
            axes[1].annotate(f"{error:.3f} px",(i,error),xytext=(0,10),textcoords="offset points",ha="center")
    available=[v for v in errors if v is not None]
    axes[1].set(xticks=[0,1],xticklabels=["Persistence","Secant"],xlim=(-.5,1.5),ylim=(0,max(available+[.1])*1.45),ylabel="Absolute error against same target (px)")
    axes[1].grid(axis="y",alpha=.15)
    delta=summary["delta_abs_error_px"]
    message=f"Secant minus persistence error = {delta:+.3f} px" if delta is not None else "Score unavailable; missingness retained"
    axes[1].set_title(message,fontsize=10)
    fig.suptitle("S03-E031-MD01 R001/R002 | controlled experiment\nOne preselected continuation: origin 28, target 29; not physical-width validation",fontsize=11)
    fig.supxlabel(f"Valid profiles {summary['valid_profiles']}/3; scored opportunities {summary['coverage']}/1. Lines guide stage order, not equal time/load; no CI from one case.",fontsize=8)
    finish(fig,"F03_minimal_baseline_comparison")

    with (a.output/"stage_widths.csv").open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["stage","filename","width_px","valid","dx_px","dy_px","max_patch_residual_px"])
        writer.writeheader()
        for r in records:
            writer.writerow(dict(stage=r["stage"],filename=r["filename"],width_px=r["measurement"]["fwhm_native_px"],
                                 valid=r["measurement"]["valid"],dx_px=r["registration"]["dx"],dy_px=r["registration"]["dy"],
                                 max_patch_residual_px=r["registration"].get("max_patch_residual_px")))
    for name,value in (("visual_layout_audit.json",qa),("run_receipt.json",dict(
        execution="succeeded",retrieval="verified_local",render_only=True,host=socket.gethostname(),pid=os.getpid(),
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),command=sys.argv,
        dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),runtime=sys.executable,
        started_at_utc=started_at,
        ended_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-t,
        input_history=str(a.history),input_target=str(a.target),no_new_measurement=True))):
        (a.output/name).write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(qa,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("source","history","target","output"): p.add_argument("--"+key,type=Path,required=True)
    main(p.parse_args())
