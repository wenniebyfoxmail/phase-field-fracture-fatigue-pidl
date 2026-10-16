"""E032 saved-output figures; no measurement, registration or error selection."""
import argparse
from datetime import datetime,timezone
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
from matplotlib.patches import Rectangle,Polygon
import numpy as np
from PIL import Image,ImageOps

sys.path.insert(0,"/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout


def run(a):
    start=time.monotonic();started=datetime.now(timezone.utc).isoformat()
    a.output.mkdir(parents=True,exist_ok=False)
    summary=json.loads((a.numeric/"summary.json").read_text())
    lock=json.loads((a.numeric/"input_position_lock.json").read_text())
    cases=json.loads((a.numeric/"scenarios.json").read_text())
    common=[c for c in cases if c["family"]=="common"]
    independent=[c for c in cases if c["family"]=="independent"]
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
                         "axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42})
    qa={}
    def finish(fig,name):
        qa[name]=audit_layout(fig)
        fig.savefig(a.output/(name+".png"),dpi=300)
        fig.savefig(a.output/(name+".pdf"))
        with Image.open(a.output/(name+".png")) as im:
            ImageOps.grayscale(im).save(a.output/(name+"_gray.png"),dpi=(300,300))
        plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11.5,4.9),constrained_layout=True)
    matrix_c=np.full((5,5),np.nan);matrix_i=matrix_c.copy()
    for c in common:
        i=lock["fractions"].index(c["normal_fraction"])
        j=lock["fractions"].index(c["tangent_fraction"])
        if c["valid"]: matrix_c[j,i]=c["delta_abs_error"]
    for c in independent:
        i=lock["labels"].index(c["anchor28"]);j=lock["labels"].index(c["anchor29"])
        if c["valid"]: matrix_i[j,i]=c["delta_abs_error"]
    lim=max(abs(c["delta_abs_error"]) for c in cases if c["valid"])
    for ax,matrix in zip(axes,(matrix_c,matrix_i)):
        image=ax.imshow(np.ma.masked_invalid(matrix),origin="lower",cmap="RdBu_r",vmin=-lim,vmax=lim,interpolation="nearest",aspect="equal")
        ax.set_xticks(range(5));ax.set_yticks(range(5))
        for j,i in np.ndindex(matrix.shape):
            value=matrix[j,i]
            text=f"{value:.2f}" if np.isfinite(value) else "missing"
            color="white" if np.isfinite(value) and abs(value)>.58*lim else "black"
            ax.text(i,j,text,color=color,ha="center",va="center",fontsize=9)
    axes[0].set(xticklabels=[f"{f*lock['envelope_normal_px']:.2f}" for f in lock["fractions"]],
                yticklabels=[f"{f*lock['envelope_tangent_px']:.2f}" for f in lock["fractions"]],
                xlabel="Common normal offset (native px)",ylabel="Common tangent offset (native px)",
                title="Same shift at stages 27, 28 and 29")
    axes[1].set(xticklabels=lock["labels"],yticklabels=lock["labels"],xlabel="Step 28 position proxy",
                ylabel="Step 29 position proxy",title="Independent later-stage mismatch; 27 fixed")
    axes[0].add_patch(Rectangle((1.5,1.5),1,1,fill=False,color="black",lw=2))
    axes[1].add_patch(Rectangle((-.5,-.5),1,1,fill=False,color="black",lw=2))
    fig.colorbar(image,ax=axes,shrink=.9,label="Absolute error: secant minus persistence (px)")
    fig.suptitle("S03-E032-MD01 R001 | viewed controlled-experiment sensitivity\nOrigin 28 / target 29; negative favours secant; 50 finite cases, one record",fontsize=12)
    fig.supxlabel("Discrete cases only, not continuous or probability bounds. M=original median; L/R=left/right background anchors. Outlined=E031 position.",fontsize=8)
    finish(fig,"F01_all_position_scenarios")

    fig,axes=plt.subplots(1,2,figsize=(10,4.7),constrained_layout=True)
    max_error=max(max(c["persistence_abs_error"],c["secant_abs_error"]) for c in cases if c["valid"])
    for k,(name,rows,color,marker) in enumerate((("Common",common,"#0072B2","o"),("Independent",independent,"#D55E00","^"))):
        valid=[c for c in rows if c["valid"]]
        axes[0].scatter([c["persistence_abs_error"] for c in valid],[c["secant_abs_error"] for c in valid],
                        c=color,marker=marker,s=30,alpha=.75,label=f"{name}: {len(valid)}/{len(rows)} valid")
        xs=k+np.linspace(-.18,.18,len(rows))
        for x,c in zip(xs,rows):
            if c["valid"]: axes[1].scatter(x,c["delta_abs_error"],c=color,marker=marker,s=28,alpha=.75)
    axes[0].plot([0,max_error*1.12],[0,max_error*1.12],color=".55",ls="--",lw=1,label="Equal absolute error")
    base=summary["baseline"]
    axes[0].scatter(base["persistence_abs_error"],base["secant_abs_error"],c="black",marker="*",s=110,label="E031 original")
    axes[0].set(xlabel="Persistence absolute error (px)",ylabel="Secant absolute error (px)",
                xlim=(0,max_error*1.12),ylim=(0,max_error*1.12),title="Same target for both methods in every case")
    axes[0].legend(loc="upper left",fontsize=8,frameon=False)
    axes[0].grid(alpha=.15)
    axes[1].axhline(0,color="black",lw=1)
    axes[1].axhline(base["delta_abs_error"],color=".45",lw=1,ls=":",label="E031 original difference")
    axes[1].set(xticks=[0,1],xticklabels=["Common offsets","Independent mismatch"],
                ylabel="Secant minus persistence absolute error (px)",xlim=(-.4,1.4),
                ylim=(min(c["delta_abs_error"] for c in cases if c["valid"])-.5,max(0,max(c["delta_abs_error"] for c in cases if c["valid"]))+.5))
    axes[1].set_title("All prespecified cases; lower is better")
    axes[1].legend(loc="upper right",frameon=False,fontsize=8)
    axes[1].grid(axis="y",alpha=.15)
    fig.suptitle("S03-E032-MD01 R001 | one viewed continuation, not 50 independent tests\nUnchanged half-depth width; E031 original scores retained",fontsize=12)
    fig.supxlabel("Points show deterministic position assumptions; no CI or sampling probability. Horizontal spreading follows fixed case order, not error rank.",fontsize=8)
    finish(fig,"F02_comparator_and_gain")

    fig,axes=plt.subplots(2,3,figsize=(11.5,7.6),constrained_layout=True)
    n=np.array(lock["normal"]);t=np.array(lock["tangent"])
    rn,rt=lock["envelope_normal_px"],lock["envelope_tangent_px"]
    n0=np.array(lock["geometry"]["center"])
    common_xy=np.array([fn*rn*n+ft*rt*t for fn in lock["fractions"] for ft in lock["fractions"]])
    corner_xy=np.array([sn*rn*n+st*rt*t for sn,st in ((-1,-1),(1,-1),(1,1),(-1,1))])
    label_offsets={"L1":(-24,9),"L2":(-24,-14),"R1":(5,9),"R2":(5,-14)}
    for j,stage in enumerate((27,28,29)):
        reg=lock["registrations"][j];center=n0+[reg["dx"],reg["dy"]]
        x0,y0=np.floor(center-[140,110]).astype(int);x1,y1=x0+280,y0+220
        with Image.open(a.old_source/("IMG_0403.JPG","IMG_0406.JPG","IMG_0409.JPG")[j]) as im:
            crop=ImageOps.exif_transpose(im).convert("RGB").crop((x0,y0,x1,y1))
            axes[0,j].imshow(crop,extent=[x0-.5-center[0],x1-.5-center[0],y1-.5-center[1],y0-.5-center[1]])
        band=np.array([-60*n,60*n]);axes[0,j].plot(*band.T,color="#009E73",lw=1.4)
        axes[0,j].add_patch(Polygon(corner_xy,fill=False,color="#56B4E9",lw=1.2))
        axes[0,j].set(title=f"Step {stage} | original raw crop",xticks=[],yticks=[])
        xx=common_xy@n;yy=common_xy@t
        axes[1,j].scatter(xx,yy,color="#0072B2",marker="s",s=18,alpha=.65,label="25 common offsets")
        axes[1,j].scatter(0,0,color="black",marker="*",s=70,label="E031 centre")
        if stage>27:
            for label in lock["labels"][1:]:
                delta=np.array(lock["residual_xy"][str(stage)][label]);x,y=delta@n,delta@t
                axes[1,j].scatter(x,y,c="#D55E00",marker="x",s=45)
                axes[1,j].annotate(label,(x,y),xytext=label_offsets[label],textcoords="offset points",fontsize=8)
        axes[1,j].set(xlim=(-rn-1.5,rn+1.5),ylim=(-rn-1.5,rn+1.5),xlabel="Normal displacement (px)",ylabel="Tangent displacement (px)")
        axes[1,j].set_title("Independent set: fixed reference" if stage==27 else "Paired background residuals\n(not known crack errors)",fontsize=9)
        axes[1,j].set_aspect("equal");axes[1,j].grid(alpha=.15)
    axes[1,0].legend(loc="upper left",fontsize=7,frameon=False)
    fig.suptitle("S03-E032-MD01 R001 | fixed raw-image band and ALL prescribed positional support\nGreen: original band; blue outline: common-centre envelope; orange crosses: anchor alternatives",fontsize=11)
    fig.supxlabel("Same native crop scale; no new registration, no width-based selection. Background-to-crack error transfer remains an assumption.",fontsize=8)
    finish(fig,"F03_originals_and_offset_support")
    (a.output/"layout_audit.json").write_text(json.dumps(qa,indent=2)+"\n")
    (a.output/"run_receipt.json").write_text(json.dumps(dict(render_only=True,no_new_measurement=True,execution="succeeded",retrieval="verified_local",
        source_numeric=str(a.numeric),host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,command=sys.argv,
        commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
        started_at_utc=started,ended_at_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start),indent=2)+"\n")
    print(json.dumps(qa,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("numeric","old-source","output"):p.add_argument("--"+name,type=Path,required=True)
    run(p.parse_args())
