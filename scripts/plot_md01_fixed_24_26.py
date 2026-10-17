"""E034 historical inspection or saved-output plotting; never rescores sources."""
import argparse
import csv
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
from md01_fixed_24_26 import SOURCE, FILES, now, save
sys.path.insert(0,"/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout


def main(a):
    start=time.monotonic(); a.output.mkdir(parents=True,exist_ok=False)
    started=now(); qa={}
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42,
                         "axes.spines.top":False,"axes.spines.right":False})
    def finish(fig,name,caption):
        qa[name]=audit_layout(fig)
        fig.savefig(a.output/(name+".png"),dpi=300)
        with Image.open(a.output/(name+".png")) as im:
            ImageOps.grayscale(im).save(a.output/(name+"_gray.png"),dpi=(300,300))
        if a.vector: fig.savefig(a.output/(name+".pdf"))
        (a.output/(name+".md")).write_text(caption+"\n")
        (a.output/(name+"_gray.md")).write_text("# Grayscale QA\nSame content/source as "+name+".md; not extra evidence.\n")
        plt.close(fig)
    if a.phase=="anchors":
        cfg=json.loads(a.geometry.read_text())
        half=cfg["patch_size"]//2
        fig,axes=plt.subplots(1,4,figsize=(9.5,3),constrained_layout=True)
        with Image.open(SOURCE/FILES[0]) as raw:
            im=ImageOps.exif_transpose(raw).convert("RGB")
            for i,((x,y),ax) in enumerate(zip(cfg["background_centers"],axes)):
                ax.imshow(im.crop((x-half,y-half,x+half+1,y+half+1)),extent=(x-half,x+half+1,y+half+1,y-half))
                ax.set_title(f"Anchor {i+1}: ({x},{y})",fontsize=9)
                ax.set_xticks([]);ax.set_yticks([])
        fig.suptitle(f"E034 | fixed Step24 background templates ({cfg['patch_size']} x {cfg['patch_size']} native px)\n"
                     "Source inspection only; no replacement / target access",fontsize=11)
        finish(fig,"F00_fixed_background_templates","# Fixed original templates\nStep24 source394, "
               f"exact original four centers; native{cfg['patch_size']}px crops. No enhancement or measurement. "
               "Inspect source content only, not target errors. These are background correspondences, not physical truth.")
    elif a.phase=="inspect":
        crop=(3900,900,4700,3500)
        for i in (0,1):
            with Image.open(SOURCE/FILES[i]) as im:
                image=ImageOps.exif_transpose(im).convert("RGB")
                image.crop(crop).save(a.output/f"step{24+i}_trace_crop.png")
            (a.output/f"step{24+i}_trace_crop.md").write_text(
                f"# History inspection only\nE034 {FILES[i]}, native crop xyxy={crop}; no enhancement, "
                "measurement, position scan or target access. Chosen from first-history whole-view trace extent.\n")
    else:
        h=json.loads((a.history/"predictions_saved_before_target.json").read_text())
        target=json.loads((a.target/"target_measurement.json").read_text())
        result=json.loads((a.target/"summary.json").read_text())
        records=h["history"]+[target]; data={}
        for folder in (a.history,a.target):
            with np.load(folder/"profiles.npz") as f: data.update({k:f[k] for k in f.files})
        colors=("#666666","#0072B2","#D55E00")
        fig,axes=plt.subplots(2,3,figsize=(12,7.2),constrained_layout=True)
        for i,r in enumerate(records):
            with Image.open(SOURCE/r["filename"]) as raw:
                im=ImageOps.exif_transpose(raw).convert("RGB")
                pre=im.copy(); pre.thumbnail((1500,1000))
                axes[0,i].imshow(pre,extent=(0,im.width,im.height,0))
                reg=r["registration"]
                shift=np.array([reg.get("dx") or 0,reg.get("dy") or 0])
                center=np.array(h["geometry"]["center"])+shift
                normal=np.array(h["geometry"]["normal"])
                x0,y0=np.floor(center-[360,300]).astype(int); x1,y1=x0+720,y0+600
                axes[0,i].add_patch(Rectangle((x0,y0),720,600,fill=False,color="#009E73",lw=1.3))
                axes[1,i].imshow(im.crop((x0,y0,x1,y1)),extent=(x0,x1,y1,y0))
                for p in h["geometry"]["background_centers"]:
                    q=np.array(p)+shift
                    half=h["geometry"]["patch_size"]//2
                    axes[1,i].add_patch(Rectangle(q-half,2*half+1,2*half+1,fill=False,color="#56B4E9",lw=1))
                band=np.array([center-normal*60,center+normal*60])
                axes[1,i].plot(*band.T,color="#009E73",lw=1.5)
                m=r["measurement"]
                if m["valid"]:
                    cross=np.array([center+normal*m[k] for k in ("left_crossing_px","right_crossing_px")])
                    axes[1,i].scatter(*cross.T,marker="x",c="#D55E00",s=22,linewidths=1.5)
            role="target: after saved forecasts" if i==2 else "history"
            axes[0,i].set_title(f"Step {r['step']} | {r['filename']}\n{role}",fontsize=10)
            axes[1,i].set_title("Fixed band and mapped background patches",fontsize=9)
            for ax in axes[:,i]: ax.set_xticks([]);ax.set_yticks([])
        fig.suptitle("S03-E034-MD01 | controlled-experiment development, one transect\n"
                     "Green: sampling / crop; orange: half-depth crossings; blue: background patches",fontsize=12)
        finish(fig,"F01_originals_and_sampling",f"# E034 originals and sampling\nSources {FILES}; "
               f"history={a.history}; target={a.target}. Top full views, bottom native720x600px crops; "
               f"green fixed band/crop, orange half-depth crossings, blue{h['geometry']['patch_size']}px background patches. "
               "Background translation only; no target-specific recentering. These are image widths, "
               "not physical aperture, independently labelled edges or calibrated registration. See README_analysis.md.")
        fig,axes=plt.subplots(1,3,figsize=(12,3.8),sharey=True,constrained_layout=True)
        limits=[float(data[f"s{r['step']}_deficit"].min()) for r in records]+[float(data[f"s{r['step']}_deficit"].max()) for r in records]
        for i,(ax,r) in enumerate(zip(axes,records)):
            m=r["measurement"]; level=m["depth_gray"]/2
            ax.plot(data["offsets"],data[f"s{r['step']}_deficit"],color=colors[i],lw=1.5)
            ax.axhline(level,color=colors[i],ls="--",lw=1)
            if m["valid"]: ax.hlines(level,m["left_crossing_px"],m["right_crossing_px"],color="black",lw=2)
            for low,high in ((-60,-45),(45,60)): ax.axvspan(low,high,color=".9",zorder=-2)
            label=f"{m['fwhm_native_px']:.3f} px" if m["valid"] else m["reason"]
            ax.set(title=f"Step {r['step']} | {label}",xlabel="Normal offset (Step24 native px)",xlim=(-60,60),ylim=(min(limits)-5,max(limits)+8))
            ax.grid(alpha=.15)
        axes[0].set_ylabel("Background minus grayscale intensity")
        fig.suptitle("S03-E034-MD01 | unchanged five-row median half-depth\nDashed: half local peak depth; black: width; grey: shoulder support",fontsize=11)
        finish(fig,"F02_halfdepth_profiles",f"# E034 saved half-depth profiles\nExact profiles.npz and measurements from {a.history}, {a.target}. "
               "No new sampling. Shared grayscale-deficit axis and native-offset units; shoulder background beyond±45px, fixed peak search±15px, "
               "five rows are not independent samples. Width is half local optical depth, not physical opening. See README_analysis.md.")
        fig,axes=plt.subplots(1,2,figsize=(9.5,4.5),constrained_layout=True)
        widths=[r["measurement"]["fwhm_native_px"] if r["measurement"]["valid"] else np.nan for r in records]
        axes[0].plot([24,25,26],widths,"ko-",lw=1.2,label="Measured image width")
        for arm,col,marker,label in (("persistence","#666666","s","Persistence"),("stage_trend","#0072B2","^","Stage trend")):
            p=h["predictions"]["arms"][arm]["prediction_px"]
            axes[0].plot([25,26],[widths[1],p],color=col,ls="--",lw=1.2)
            axes[0].scatter(26,p,color=col,marker=marker,s=65,label=f"{label}: {p:.3f} px",zorder=4)
        maxima=[v for v in widths if np.isfinite(v)]+[v["prediction_px"] for v in h["predictions"]["arms"].values()]
        axes[0].set(xlabel="Relative stage index (not kN or seconds)",ylabel="Half-depth width (Step24 native px)",xticks=[24,25,26],ylim=(0,max(maxima)*1.4))
        axes[0].legend(loc="upper left",frameon=False,fontsize=8);axes[0].grid(alpha=.15)
        errors=[]
        for i,(arm,col,marker) in enumerate((("persistence","#666666","s"),("stage_trend","#0072B2","^"))):
            e=result["methods"][arm]["abs_error_px"]
            if e is not None:
                errors.append(e);axes[1].scatter(i,e,color=col,marker=marker,s=70)
                axes[1].annotate(f"{e:.3f} px",(i,e),xytext=(0,10),textcoords="offset points",ha="center")
        axes[1].set(xlim=(-.5,1.5),xticks=[0,1],xticklabels=["Persistence","Stage trend"],ylabel="Absolute error vs same target (px)",ylim=(0,max(errors+[.1])*1.5))
        delta=result["delta_abs_error_px"]
        axes[1].set_title(f"Trend minus persistence error: {delta:+.3f} px" if delta is not None else "Unscorable; reference missing",fontsize=10)
        axes[1].grid(axis="y",alpha=.15)
        fig.suptitle("S03-E034-MD01 | one controlled-experiment development query\nOrigin Step25, target Step26; forecasts saved before target acquisition",fontsize=11)
        fig.supxlabel(f"Common scored {result['common_scored']}/1. Lines guide order only, not equal time/load. No CI from one case; not physical-width validation.",fontsize=8)
        finish(fig,"F03_prediction_comparison",f"# E034 paired forecast comparison\nExact saved predictions and summary from {a.history}, {a.target}. "
               "Left measured half-depth widths plus persistence and stage-trend forecast; right absolute errors vs same fixed reference. "
               f"Delta={delta}, negative favours trend. Common coverage{result['common_scored']}/1; one same-source development query, not independent-beam validation. "
               "No extra measurement, smoothing, rescoring or uncertainty interval. See README_analysis.md.")
        with (a.output/"stage_widths.csv").open("x",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=["step","filename","width_px","valid","dx_px","dy_px","max_background_residual_px"])
            writer.writeheader()
            for r in records: writer.writerow(dict(step=r["step"],filename=r["filename"],width_px=r["measurement"]["fwhm_native_px"],valid=r["measurement"]["valid"],dx_px=r["registration"].get("dx"),dy_px=r["registration"].get("dy"),max_background_residual_px=r["registration"].get("max_patch_residual_px")))
    save(a.output/"layout_audit.json",qa)
    save(a.output/"run_receipt.json",dict(execution="succeeded",retrieval="verified_local",render_only=True,
         command=sys.argv,host=socket.gethostname(),pid=os.getpid(),started_at_utc=started,ended_at_utc=now(),
         wall_seconds=time.monotonic()-start,commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
         dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines()))
    print(json.dumps(qa))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("phase",choices=("inspect","anchors","result"))
    for key in ("output","history","target","geometry"):p.add_argument("--"+key,type=Path)
    p.add_argument("--vector",action="store_true");main(p.parse_args())
