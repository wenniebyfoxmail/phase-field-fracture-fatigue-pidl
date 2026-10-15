"""Render all frozen Beam4 alignment outputs without refitting anything."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read(p):
    with p.open(newline="") as f: return list(csv.DictReader(f))


def valid(x): return str(x).lower() in ("true","1")


def write(p,rows):
    if rows:
        with p.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def median(x):
    x=np.asarray(x,float)
    return float(np.median(x[np.isfinite(x)])) if np.isfinite(x).any() else None


def export(fig,out,name,question,reading,takeaway,sources):
    for suffix in ("png","pdf"): fig.savefig(out/f"{name}.{suffix}",dpi=180,bbox_inches="tight")
    plt.close(fig)
    (out/f"{name}.md").write_text(f"""# How to read {name}
## Figure question
{question}
## Data provenance
{sources}
Beam4 only, controlled-experiment DEVELOPMENT; S03-E019-D01-R001. Renderer `scripts/render_d01_background_alignment.py`, no fitting/scoring of forecasts. Protocol fixes all patches, all12 transects, all4 stages and T6 examples.
## Visual grammar and panel guide
{reading}
## Key numerical takeaway
{takeaway}
## Limitations and claim boundary
Background matching displacement is an algorithmic texture-correspondence proxy, not an independent physical landmark or calibrated registration error. One already-viewed beam, spatially dependent patches/transects. Fit/check patches are distinct within each local model; not a specimen holdout. Width sensitivity is a perturbation diagnostic, not measured noise or a confidence interval. No human/physical reference, forecast rescore, or causal future-prediction claim. Missing corrections/measurements are retained, not zero-filled. Shared local translation cannot remove intrinsic spatial width heterogeneity.
## Related assets
`summary.json`, paired CSVs, original run receipt and `README_analysis.md`; same-stem PNG/PDF share this sidecar.
""")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",type=Path,required=True)
    p.add_argument("--e018",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    anchors=read(a.run/"anchor_matches.csv")
    translations=read(a.run/"translations.csv")
    widths=read(a.run/"width_variants.csv")
    assert len(anchors)==288 and len(translations)==48 and len(widths)==480
    assert len({(r['stage_index'],r['transect_id'],r['anchor_id']) for r in anchors})==288
    assert len({(r['stage_index'],r['transect_id'],r['arm'],r['variant']) for r in widths})==480
    checks=[r for r in anchors if r["role"]=="check"]
    paired=[r for r in checks if valid(r["available"]) and valid(r["correction_available"])]
    assert len(checks)==144
    diffs=[float(r["after_residual_px"])-float(r["before_residual_px"]) for r in paired]
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    colors={1:"#0072B2",2:"#D55E00",3:"#009E73"}
    per_stage=[]
    for j,load in ((1,30),(2,40),(3,50)):
        group=[r for r in paired if int(r["stage_index"])==j]
        before=[float(r["before_residual_px"]) for r in group]
        after=[float(r["after_residual_px"]) for r in group]
        axes[0].scatter(before,after,color=colors[j],s=17,alpha=.65,label=f"{load} kN | {len(group)}/48 checks")
        ds=np.sort(np.array(after)-np.array(before))
        if len(ds): axes[1].step(ds,np.arange(1,len(ds)+1)/len(ds),where="post",color=colors[j],label=f"{load} kN")
        per_stage.append(dict(stage_index=j,load_kN=load,paired_check_count=len(group),total_check_count=48,
                              before_residual_median_px=median(before),after_residual_median_px=median(after),
                              median_paired_change_px=median(ds)))
    lim=max([float(r[k]) for r in paired for k in ("before_residual_px","after_residual_px")]+[1])*1.05
    axes[0].plot([0,lim],[0,lim],"--",color="#777777",lw=1)
    axes[0].set(xlim=(0,lim),ylim=(0,lim),xlabel="Original-H check residual (native px)",ylabel="After FIT-only translation (native px)",title="Held-out patch proxy | below diagonal improves")
    axes[0].legend(fontsize=8)
    axes[1].axvline(0,color="#777777",ls="--",lw=1)
    axes[1].set(xlabel="After - before check residual (native px)",ylabel="Fraction of paired checks",title="All paired checks, by load stage")
    axes[1].legend(fontsize=8)
    if not paired:
        for ax in axes: ax.text(.5,.5,"No paired available corrections",transform=ax.transAxes,ha="center")
    fig.suptitle("Beam4 background correspondence | FIT4 / separate CHECK4",fontsize=13)
    fig.tight_layout(rect=[0,.05,1,.94])
    fig.text(.02,.01,f"Paired CHECK support {len(paired)}/144; stage0 excluded. Texture-matching proxy only; not physical registration truth.",fontsize=9)
    export(fig,a.output,"background_correspondence","Does background-only local translation improve separate CHECK patch consistency?",
           "Left: every paired CHECK residual, same before/after scales, dashed1:1. Right: ECDF of paired residual changes; negative is improvement, zero line explicit. Colours identify allthree later stages; origin excluded. Missing matches remain outside paired summary and counted in denominator.",
           json.dumps(per_stage),str(a.run/"anchor_matches.csv"))

    grouped={}
    for r in widths: grouped.setdefault((int(r["stage_index"]),int(r["transect_id"]),r["arm"]),{})[r["variant"]]=r
    expected={"baseline","normal_minus2","normal_plus2","tangent_minus2","tangent_plus2"}
    assert len(grouped)==96 and all(set(g)==expected for g in grouped.values())
    sensitivity=[]
    for j in range(4):
        for t in range(1,13):
            row=dict(stage_index=j,transect_id=t)
            for arm in ("original_H","background_aligned"):
                group=grouped[(j,t,arm)]
                complete=all(valid(v["valid"]) for v in group.values())
                row[arm+"_complete"]=complete
                row[arm+"_sensitivity_px"]=max(abs(float(v["width_px"])-float(group["baseline"]["width_px"])) for v in group.values()) if complete else np.nan
            row["paired_complete"]=row["original_H_complete"] and row["background_aligned_complete"]
            sensitivity.append(row)
    write(a.output/"paired_width_sensitivity.csv",sensitivity)
    reference={(int(r["stage_index"]),int(r["transect_id"])):r for r in read(a.e018/"independent_measurements.csv") if int(r["beam"])==4}
    assert len(reference)==48
    replay_diff=[]
    for (j,t,arm), group in grouped.items():
        if arm=="original_H":
            before=group["baseline"]
            assert valid(before["valid"])==valid(reference[(j,t)]["valid"])
            if valid(before["valid"]): replay_diff.append(abs(float(before["width_px"])-float(reference[(j,t)]["width_px"])))
    assert len(replay_diff)==48 and max(replay_diff)<=1e-8
    summaries={}
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,(name,include) in zip(axes,(("All4 stages",lambda r:True),("Later3 stages",lambda r:r["stage_index"]>0))):
        all_rows=[r for r in sensitivity if include(r)]
        group=[r for r in all_rows if r["paired_complete"]]
        x=[r["original_H_sensitivity_px"] for r in group]
        y=[r["background_aligned_sensitivity_px"] for r in group]
        for r in group: ax.scatter(r["original_H_sensitivity_px"],r["background_aligned_sensitivity_px"],color=colors.get(r["stage_index"],"#777777"),s=25,alpha=.7)
        summaries[name]=dict(paired_profiles=len(group),total_profiles=len(all_rows),
                            before_median_px=median(x),after_median_px=median(y),
                            median_paired_change_px=median(np.array(y)-np.array(x)),
                            original_all_available_median_px=median([r["original_H_sensitivity_px"] for r in all_rows]))
        lim=max(x+y+[1])*1.05
        ax.plot([0,lim],[0,lim],"--",color="#777777",lw=1)
        ax.set(xlim=(0,lim),ylim=(0,lim),xlabel="Original-H max shift effect (native px)",ylabel="After background alignment (native px)",
               title=f"{name} | paired {len(group)}/{len(all_rows)}")
        if not group: ax.text(.5,.5,"No paired complete measurements",transform=ax.transAxes,ha="center")
    # A shared comparison scale, not per-panel autoscaling.
    shared=max(ax.get_xlim()[1] for ax in axes)
    for ax in axes: ax.set(xlim=(0,shared),ylim=(0,shared)); ax.set_aspect("equal",adjustable="box")
    fig.suptitle("Does the SAME +/-2 px position perturbation become smaller?",fontsize=13)
    fig.tight_layout(rect=[0,.08,1,.95])
    fig.text(.02,.01,"Each dot: max width change across four predeclared shifts; correction fitted once, NOT per variant.\nBelow diagonal is less sensitive. No smoothing/width fitting; this is not physical measurement noise.",fontsize=9)
    export(fig,a.output,"alignment_width_sensitivity","How does width position sensitivity change after independently fitted background alignment?",
           "Left all48 profiles includes unchanged origin; right later36 only. Both panels use same x/y range. Every paired complete profile is shown, coloured by stage (origin gray;30blue/40orange/50green). Below1:1 means smaller sensitivity. Denominators retain missing correction cases; no missing values as zero.",
           json.dumps(summaries),str(a.run/"width_variants.csv")+"; E018 same-profile measurements for baseline replay check")

    with np.load(a.run/"examples.npz",allow_pickle=False) as z:
        fig,axes=plt.subplots(4,3,figsize=(11,10))
        for j,load in enumerate((10,30,40,50)):
            key=f"st{j}_"
            for col,arm in enumerate(("original_H","background_aligned")):
                if key+arm+"_strip" in z.files:
                    axes[j,col].imshow(z[key+arm+"_strip"],cmap="gray",vmin=0,vmax=255,extent=[-60.5,60.5,60.5,-60.5],aspect="auto")
                    axes[j,col].axhspan(-2.5,2.5,color="#56B4E9",alpha=.2)
                    d=z[key+arm+"_deficit"]
                    axes[j,2].plot(np.arange(-60,60.25,.25),d,color="#777777" if col==0 else "#0072B2",lw=1.2,ls="-" if col==0 else "--",label=arm)
                else: axes[j,col].text(.5,.5,"Correction unavailable",transform=axes[j,col].transAxes,ha="center")
                axes[j,col].set(xticks=[-60,0,60],yticks=[-60,0,60],title=f"{load} kN | {arm}" if j==0 else f"{load} kN")
                if col==0: axes[j,col].set_ylabel("Tangent native px")
            axes[j,2].set(xlim=(-60,60),ylim=(-25,220),title=f"T6 | {load} kN deficit",ylabel="Gray deficit")
            for ax in axes[j]: ax.set_xlabel("Normal offset (native px)")
        axes[0,2].legend(fontsize=7)
        fig.suptitle("Beam4 T6 at ALL4 stages | original / aligned source sampling",fontsize=13)
        fig.tight_layout(rect=[0,.05,1,.96])
        fig.text(.02,.01,"Fixed example T6, same source photographs/gray scales. Blue band: five sampling lines; no crack-edge fitting.\nTranslation from background only; profiles can change because a nearby location is sampled, not necessarily because truth is recovered.",fontsize=9)
        export(fig,a.output,"aligned_source_examples","What source locations/profiles change under the fixed background correction?",
               "Four stage rows, original and aligned raw local strips in columns1/2; half-depth deficit curves in column3. Every original/available aligned case at fixedT6, not outcome-selected. Shared grayscale0..255, deficit-25..220; native local coordinates. Missing correction stays explicitly unavailable.",
               "T6 examples at all4 stages; exact widths and translations in original run CSVs. Display is an image-coordinate resampling, not AI-generated pictures or physical edge ground truth.",str(a.run/"examples.npz"))
    available_later=[r for r in translations if int(r["stage_index"])>0 and valid(r["available"])]
    summary=dict(experiment_id="S03-E019-D01",claim="C1 internal background-correspondence diagnostic, not physical accuracy",
                 later_translation_coverage=dict(available=len(available_later),total=36),
                 later_anchor_available=sum(valid(r["available"]) for r in anchors),later_anchor_opportunities=288,
                 check_paired_support=len(paired),check_opportunities=144,
                 check_before_median_px=median([float(r["before_residual_px"]) for r in paired]),
                 check_after_median_px=median([float(r["after_residual_px"]) for r in paired]),
                 primary_median_paired_check_change_px=median(diffs),per_stage=per_stage,
                 width_sensitivity=summaries,baseline_replay_max_width_difference_px=max(replay_diff),
                 anchor_failures={reason:sum(r["reason"]==reason for r in anchors) for reason in sorted({r["reason"] for r in anchors})},
                 anchor_ncc_median=median([float(r["ncc_peak"]) for r in anchors]),
                 anchor_peak_separation_median=median([float(r["peak_separation"]) for r in anchors]),
                 physical_reference=False,new_forecast_scores=False)
    (a.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
