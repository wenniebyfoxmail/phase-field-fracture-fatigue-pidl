"""E022 fixed-grid difference sensitivity figures from saved tables only."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from d01_short_support import ARMS,LOADS,read_csv,boolean
from d01_stage_shift import SHIFTS

COLORS=("#0072B2","#D55E00","#009E73")
def num(r,k): return float(r[k])

def export(fig,out,stem,question,guide,source):
    for fmt in ("png","pdf"):fig.savefig(out/f"{stem}.{fmt}",dpi=170,bbox_inches="tight")
    plt.close(fig)
    (out/f"{stem}.md").write_text(f"""# How to read {stem}
## Figure question
{question}
## Data provenance
{source}. S03-E022-D01-R001, stage-shift-v1, Beam4 controlled-experiment DEVELOPMENT, one previously viewed beam. E020 cached original half-depth widths, all12transects/all3 adjacent load transitions/both frozen arms. No segment median, new image sampling, registration fit, training or forecast score. Renderer scripts/render_d01_stage_shift.py.
## Visual grammar and panel guide
{guide}
## Key numerical takeaway
Exact per-arm/per-transition RMS and sign diagnostics are in outputs/summary.json and README_analysis.md. C=RMS deviation from nominal increment under9 equal common shifts; I=same under81 Cartesian shifts with the same equal-weight9point marginal grid. Main criterion median of paired(C-I), originalH only, negative favours lower common-shift response. Native px, not mm; ratios dimensionless where explicitly marked. Position axes are NOT time.
## Limitations and claim boundary
D0 is the nominal zero-shift observed increment, NOT independently verified physical truth. Uniform finite-grid weights are a declared sensitivity diagnostic, NOT displacement probabilities or confidence intervals. Common nominal coordinate offsets do not establish actual material correspondence, physical precision or future prediction. Independent grid contains common diagonal: maximum and any-sign-loss inequalities are nested by construction, not independent evidence; RMS is not automatically ordered. All9source widths per stage required for matched RMS, invalid remains missing. One viewed beam and overlapping positions/stages/arms are dependent. No holdout/generalisation or old-score rescue; negative increments retained and not forced to growth. Figure examples fixed before outcome; no best-position/arm/length selection.
## Related assets
../outputs/pair_metrics.csv; ../outputs/perturbations.csv; ../outputs/summary.json; README_analysis.md. Same-stem PNG/PDF share this note.
""")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    pairs=read_csv(a.run/"pair_metrics.csv");grid=read_csv(a.run/"perturbations.csv");stats=json.loads((a.run/"summary.json").read_text())
    assert len(pairs)==72 and len(grid)==5832
    assert len({(r['arm'],r['stage_a'],r['transect_id']) for r in pairs})==72
    assert len({(r['arm'],r['stage_a'],r['transect_id'],r['shift_a_px'],r['shift_b_px']) for r in grid})==5832
    valid=[r for r in pairs if boolean(r["paired_valid"])]
    limit=max([num(r,k) for r in valid for k in ("common_rms_px","independent_rms_px")]+[.1])*1.08
    fig,axes=plt.subplots(1,2,figsize=(10,5),sharex=True,sharey=True)
    for ai,ax in enumerate(axes):
        for j in range(3):
            rows=[r for r in valid if r["arm"]==ARMS[ai] and int(r["stage_a"])==j]
            ax.scatter([num(r,"independent_rms_px") for r in rows],[num(r,"common_rms_px") for r in rows],s=25,alpha=.8,color=COLORS[j],label=f"{LOADS[j]}→{LOADS[j+1]} kN")
        ax.plot([0,limit],[0,limit],color="#888888",ls="--",lw=1)
        stat=stats["by_arm"][ai]["overall"];change=stat['median_paired_rms_change_px']
        label=f"Matched {stat['matched']}/36\nmedian paired(C-I): {change:.4f}px" if change is not None else "No matched pairs"
        ax.text(.04,.96,label,transform=ax.transAxes,va="top",fontsize=9)
        ax.set(xlim=(0,limit),ylim=(0,limit),xlabel="Independent-shift RMS I (native px)",ylabel="Common-shift RMS C (native px)",title=ARMS[ai]);ax.set_aspect("equal");ax.grid(alpha=.15)
    axes[1].legend(fontsize=8,loc="lower right")
    fig.suptitle("S03-E022-D01-R001 | Beam4 DEVELOPMENT | below identity: less response to common shifts",fontsize=11)
    fig.tight_layout(rect=[0,.08,1,.94]);fig.text(.02,.01,"Same ±2px / 0.5px marginal grid: 9 common pairs vs81 Cartesian pairs. RMS is finite-grid sensitivity, NOT physical error.",fontsize=9)
    export(fig,a.output,"common_vs_independent_rms","Does coupling offsets reduce stage-difference response under the same fixed marginal grid?",
           "Every matched stage/transect point, two arms on shared axes. Transition colours; diagonal=equalRMS, below=common lower. Primary originalH annotation uses paired differences, not separate-median subtraction; aligned arm secondary.",str(a.run/"pair_metrics.csv"))

    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,sharey=True)
    magnitude=max([num(r,k) for r in valid for k in ("common_rms_px","independent_rms_px")]+[abs(num(r,"baseline_delta_px")) for r in valid]+[.1])*1.08
    for ai,ax in enumerate(axes):
        rows=sorted([r for r in pairs if r["arm"]==ARMS[ai]],key=lambda r:(int(r["stage_a"]),int(r["transect_id"])))
        for name,color,marker,label in (("common_rms_px","#0072B2","o","Common RMS C"),("independent_rms_px","#D55E00","s","Independent RMS I"),("baseline_delta_px","#555555","x","|Nominal increment D0|")):
            values=[abs(num(r,name)) if boolean(r["paired_valid"]) else np.nan for r in rows]
            ax.scatter(np.arange(36),values,s=22,color=color,marker=marker,label=label,alpha=.85)
        for x in (11.5,23.5):ax.axvline(x,color="#aaaaaa",lw=.7)
        for j in range(3):ax.text(j*12+5.5,magnitude*.95,f"{LOADS[j]}→{LOADS[j+1]} kN",ha="center",fontsize=9)
        ax.set(title=ARMS[ai],ylim=(0,magnitude),ylabel="Native px");ax.grid(axis="y",alpha=.15)
    axes[0].legend(loc="upper right",fontsize=8,ncol=3,bbox_to_anchor=(1,1.24))
    axes[1].set(xticks=np.arange(36),xticklabels=[str(t) for j in range(3) for t in range(1,13)],xlabel="Transect within each observed load transition (all12)")
    fig.suptitle("S03-E022-D01-R001 | residual sensitivity versus observed increment magnitude",fontsize=12)
    fig.tight_layout(rect=[0,.07,1,.94]);fig.text(.02,.01,"All36 stage/transect pairs per arm. These are C, I and |D0| in PIXELS, not the dimensionless C/I ratio. D0 is not truth.",fontsize=9)
    export(fig,a.output,"rms_and_increment_magnitudes","Is residual response small or large relative to the observed stage increment?",
           "All36ordered pairs per arm;3transition blocks, T1..12 within each. Blue circle commonRMS, orange square independentRMS, gray cross absolute nominal observed increment. All quantities nativepixels on shared axes; no ratio on this scale. Raw signed increments retained in tables, no growth claim or physical tolerance.",str(a.run/"pair_metrics.csv"))

    common=[r for r in grid if r["arm"]==ARMS[0] and boolean(r["common"])]
    values=[num(r,"stage_delta_px") for r in common if boolean(r["valid_difference"])]
    low,high=min(values+[0]),max(values+[0]);pad=max((high-low)*.08,.1)
    fig,axes=plt.subplots(4,3,figsize=(11,10),sharex=True,sharey=True)
    for t,ax in enumerate(axes.flat,1):
        for j in range(3):
            rows=sorted([r for r in common if int(r["transect_id"])==t and int(r["stage_a"])==j],key=lambda r:num(r,"shift_a_px"))
            assert len(rows)==9
            ax.plot(SHIFTS,[num(r,"stage_delta_px") if boolean(r["valid_difference"]) else np.nan for r in rows],color=COLORS[j],lw=1.3,label=f"{LOADS[j]}→{LOADS[j+1]} kN")
            if boolean(rows[4]["valid_difference"]):ax.plot(0,num(rows[4],"stage_delta_px"),"o",ms=3,color=COLORS[j])
        ax.axhline(0,color="#cccccc",lw=.7);ax.axvline(0,color="#aaaaaa",lw=.7)
        ax.set(title=f"T{t}",xlim=(-2,2),ylim=(low-pad,high+pad));ax.grid(alpha=.15)
        if t>=10:ax.set_xlabel("Common shift (native px)")
        if (t-1)%3==0:ax.set_ylabel("Signed stage difference (px)")
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc="lower center",ncol=3,bbox_to_anchor=(.5,.01),fontsize=9)
    fig.suptitle("S03-E022-D01-R001 | original H | common-shift differences, ALL12 transects",fontsize=12)
    fig.tight_layout(rect=[0,.06,1,.95])
    export(fig,a.output,"all_common_shift_differences","Where does a stage difference remain position-sensitive even under common offsets?",
           "All12original-H transects, shared signed y-axis. Three transition colours, all9equal shifts. d0 dot is original nominal increment; zero line exposes reversals/shrinkage. No median/smoothing or post-outcome case choice. These are measured differences, not predictions or physical crack growth.",str(a.run/"perturbations.csv"))

    maps={}
    for arm in ARMS:
        for j in range(3):
            rows=[r for r in grid if r["arm"]==arm and int(r["transect_id"])==6 and int(r["stage_a"])==j]
            matrix=np.full((9,9),np.nan)
            for r in rows:matrix[int(round((num(r,"shift_b_px")+2)*2)),int(round((num(r,"shift_a_px")+2)*2))]=num(r,"deviation_px")
            maps[(arm,j)]=matrix
    finite=np.concatenate([m.ravel() for m in maps.values()]);finite=finite[np.isfinite(finite)];clim=max(float(np.max(abs(finite))) if len(finite) else 1,1e-6)
    fig,axes=plt.subplots(2,3,figsize=(12,7),sharex=True,sharey=True)
    cmap=plt.get_cmap("RdBu_r").copy();cmap.set_bad("#dddddd")
    for ai,arm in enumerate(ARMS):
        for j in range(3):
            ax=axes[ai,j];im=ax.imshow(maps[(arm,j)],origin="lower",extent=[-2.25,2.25,-2.25,2.25],vmin=-clim,vmax=clim,cmap=cmap,aspect="equal")
            ax.plot([-2,2],[-2,2],color="white",ls="--",lw=1);ax.plot(0,0,"s",mfc="none",mec="black",ms=6)
            ax.set(title=f"{arm}\n{LOADS[j]}→{LOADS[j+1]} kN",xticks=[-2,0,2],yticks=[-2,0,2])
            if ai==1:ax.set_xlabel("Previous-stage shift (px)")
            if j==0:ax.set_ylabel("Next-stage shift (px)")
    fig.subplots_adjust(left=.08,right=.84,bottom=.15,top=.85,wspace=.18,hspace=.45)
    cax=fig.add_axes([.88,.21,.02,.56]);fig.colorbar(im,cax=cax,label="Increment minus nominal D0 (native px)")
    fig.suptitle("S03-E022-D01-R001 | FIXED T6 | Cartesian grid; white diagonal = common shifts",fontsize=12)
    fig.text(.02,.02,"Shared signed colour scale; black square nominal(0,0), gray=missing. Fixed T6 is NOT selected for best or typical cancellation.\nCoordinate shifts are counterfactuals, not verified material correspondence or physical displacement error.",fontsize=9)
    export(fig,a.output,"fixed_t6_shift_maps","What does common versus independent displacement mean on the fixedT6 grid?",
           "Six9×9deviation maps,3transitions×2arms, shared symmetric nativepixel colour scale. Columns previous shift, rows next shift, y increasing upward. White diagonal is common9point subset, full field all81 independent pairs. Nominal(0,0) black square; gray invalid. Not an estimated offset distribution or representative-frequency sample.",str(a.run/"perturbations.csv"))

if __name__=="__main__":main()
