"""E021 figures from saved comparison tables; no fresh image sampling."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from d01_short_support import ARMS,LOADS,CENTRES,read_csv,boolean

COLORS=("#0072B2","#D55E00","#009E73","#CC79A7")

def num(r,k): return float(r[k])

def export(fig,out,stem,question,guide,source):
    for fmt in ("png","pdf"): fig.savefig(out/f"{stem}.{fmt}",dpi=170,bbox_inches="tight")
    plt.close(fig)
    (out/f"{stem}.md").write_text(f"""# How to read {stem}
## Figure question
{question}
## Data provenance
S03-E021-D01-R001, short-support-v1, controlled-experiment DEVELOPMENT, one viewed Beam4. {source}
Renderer scripts/render_d01_short_support.py. E020 cached half-depth widths and source strips; no new image sampling. All12transects,4load stages,2fixed location arms; spatial samples and arms dependent. Native pixels, not mm.
## Visual grammar and panel guide
{guide}
## Key numerical takeaway
Exact primary paired sensitivity change and stage-retention results are in summary.json and README_analysis.md; all plotted values come from the scored tables. c is spatial position, not time. Negative paired sensitivity change is favourable; stage increments are comparisons with the point observable, not reference truth.
## Limitations and claim boundary
Fixed segment is median of9WIDTHS at c±2 in0.5px increments, not the original median-of-gray-profile function. Each width retains gray±2 footprint: segment raw footprint±4 at c0; across jitter c±2 raw union±6. This is a changed observation support, not the same point target, physical crack aperture, independent material tracking or verified future prediction. No length tuning, new alignment, training, old-score change or independent-specimen uncertainty. All9widths required; missing stays missing. Odd symmetric median leaves monotone spatial curves unchanged, so smoothing is not guaranteed. Point-stage increments are not human truth; sign tolerance1e-8 is arithmetic only. See README_analysis.md for exact matched denominators and no-event caveats.
## Related assets
summary.json; centre_estimates.csv; sensitivity_comparison.csv; stage_changes.csv; README_analysis.md. Same-stem PNG/PDF share this note.
""")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True);parser.add_argument("--source",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    centres=read_csv(a.run/"centre_estimates.csv");sens=read_csv(a.run/"sensitivity_comparison.csv");stages=read_csv(a.run/"stage_changes.csv")
    summary=json.loads((a.run/"summary.json").read_text())
    assert (len(centres),len(sens),len(stages))==(864,96,72)
    valid=[r for r in sens if boolean(r["paired_valid"])]
    limit=max([num(r,k) for r in valid for k in ("point_sensitivity_px","segment_sensitivity_px")]+[1])*1.08
    fig,axes=plt.subplots(1,2,figsize=(10,5),sharex=True,sharey=True)
    for ai,ax in enumerate(axes):
        arm=ARMS[ai]
        for j in range(4):
            rows=[r for r in valid if r["arm"]==arm and int(r["stage_index"])==j]
            ax.scatter([num(r,"point_sensitivity_px") for r in rows],[num(r,"segment_sensitivity_px") for r in rows],color=COLORS[j],s=24,alpha=.8,label=f"{LOADS[j]} kN")
        ax.plot([0,limit],[0,limit],color="#888888",ls="--",lw=1)
        stat=summary["by_arm"][ai]["sensitivity"]
        change=stat['median_paired_change_px']
        annotation=f"Matched {stat['matched']}/48\nmedian paired change: {change:.4f}px" if change is not None else "No paired sensitivity"
        ax.text(.04,.96,annotation,transform=ax.transAxes,va="top",fontsize=9)
        ax.set(xlim=(0,limit),ylim=(0,limit),xlabel="Point sensitivity (native px)",ylabel="Segment-median sensitivity (native px)",title=arm)
        ax.set_aspect("equal");ax.grid(alpha=.15)
    axes[1].legend(fontsize=8,loc="lower right")
    fig.suptitle("S03-E021-D01-R001 | Beam4 DEVELOPMENT | below identity = less sensitive",fontsize=11)
    fig.tight_layout(rect=[0,.07,1,.94]);fig.text(.02,.01,"Sensitivity=max |width(c=±2)-width(c=0)|. Primary: ORIGINAL-H median of paired changes; not difference of medians.",fontsize=9)
    export(fig,a.output,"sensitivity_comparison","Does the one fixed short support reduce tangent sensitivity?",
           "Two arms on identical nonnegative axes; every matched stage/transect point shown. Stage colours; dashed identity. Below identity favours segment. Counts out48 remain visible; no independent-point confidence interval. Primary annotation uses median(pair difference).",str(a.run/"sensitivity_comparison.csv"))

    valid=[r for r in stages if boolean(r["paired_valid"])]
    vals=[num(r,k) for r in valid for k in ("point_increment_px","segment_increment_px")]
    low=min(vals+[0]);high=max(vals+[0]);pad=max((high-low)*.1,.1)
    fig,axes=plt.subplots(1,2,figsize=(10,5),sharex=True,sharey=True)
    for ai,ax in enumerate(axes):
        for j in range(3):
            rows=[r for r in valid if r["arm"]==ARMS[ai] and int(r["stage_a"])==j]
            ax.scatter([num(r,"point_increment_px") for r in rows],[num(r,"segment_increment_px") for r in rows],s=25,alpha=.8,color=COLORS[j],label=f"{LOADS[j]}→{LOADS[j+1]} kN")
        ax.plot([low-pad,high+pad],[low-pad,high+pad],color="#888888",ls="--",lw=1)
        ax.axhline(0,color="#cccccc",lw=.7);ax.axvline(0,color="#cccccc",lw=.7)
        stat=summary["by_arm"][ai]["stage_retention"]
        distortion=stat['median_absolute_distortion_px']
        annotation=f"Matched {stat['matched']}/36\nmedian |distortion|: {distortion:.4f}px\nsign agreement: {stat['sign_agreement']}/{stat['nonzero_point_increments']}" if distortion is not None else "No paired increments"
        ax.text(.04,.96,annotation,transform=ax.transAxes,va="top",fontsize=9)
        ax.set(xlim=(low-pad,high+pad),ylim=(low-pad,high+pad),xlabel="Point stage increment (native px)",ylabel="Segment stage increment (native px)",title=ARMS[ai]);ax.set_aspect("equal");ax.grid(alpha=.15)
    axes[1].legend(loc="lower right",fontsize=8)
    fig.suptitle("S03-E021-D01-R001 | observed load-stage increments | comparator, NOT physical truth",fontsize=11)
    fig.tight_layout(rect=[0,.07,1,.94]);fig.text(.02,.01,"All3 adjacent stage pairs ×12transects per arm. Signed axes retain shrinkage/reversals. No forecast rescoring.",fontsize=9)
    export(fig,a.output,"stage_increment_retention","Are observed load-stage differences retained after support aggregation?",
           "Every matched adjacent stage/transect increment, with identical signed x/y scales across arms. Dashed identity=unchanged increment; colours denote transition, not uncertainty. Zero lines expose reversals. Displayed sign agreement excludes arithmetic-zero point increments and uses exact reported support.",str(a.run/"stage_changes.csv"))

    groups={}
    for r in centres: groups.setdefault((int(r["stage_index"]),int(r["transect_id"]),r["arm"]),[]).append(r)
    for group in groups.values(): group.sort(key=lambda r:num(r,"centre_px"))
    finite=[num(r,k) for r in centres for k,v in (("point_px","point_valid"),("segment_px","segment_valid")) if boolean(r[v])]
    ymax=max(finite+[1])*1.06
    fig,axes=plt.subplots(4,3,figsize=(11,10),sharex=True,sharey=True)
    source_pairs=read_csv(a.source/"adjacent_pairs.csv")
    for t,ax in enumerate(axes.flat,1):
        for j in range(4):
            group=groups[(j,t,ARMS[0])]
            for name,v,ls in (("point_px","point_valid","-"),("segment_px","segment_valid","--")):
                ax.plot(CENTRES,[num(r,name) if boolean(r[v]) else np.nan for r in group],color=COLORS[j],ls=ls,lw=1.3)
            for pair in source_pairs:
                if pair["arm"]==ARMS[0] and int(pair["transect_id"])==t and int(pair["stage_index"])==j and boolean(pair["any_band_event"]) and -2<=num(pair,"tangent_b_px")<=2:
                    rr=group[int(round((num(pair,"tangent_b_px")+2)*2))]
                    if boolean(rr["point_valid"]): ax.plot(num(pair,"tangent_b_px"),num(rr,"point_px"),"k|",ms=5)
        ax.axvline(0,color="#aaaaaa",lw=.7);ax.set(title=f"T{t}",xlim=(-2,2),ylim=(0,ymax));ax.grid(alpha=.15)
        if t>=10: ax.set_xlabel("Centre shift (native px)")
        if (t-1)%3==0: ax.set_ylabel("Half-depth width (native px)")
    handles=[Line2D([0],[0],color=COLORS[j],label=f"{LOADS[j]} kN") for j in range(4)]+[Line2D([0],[0],color="#555555",ls=ls,label=name) for name,ls in (("point","-"),("segment median","--"))]
    fig.legend(handles=handles,loc="lower center",ncol=6,fontsize=8,bbox_to_anchor=(.5,.01))
    fig.suptitle("S03-E021-D01-R001 | original H | all12 transects / all4 stages",fontsize=12)
    fig.tight_layout(rect=[0,.06,1,.95])
    export(fig,a.output,"all_centre_responses","Where does aggregation change the local spatial response?",
           "All12original-H transects;4stage colours, solid original point/dashed segment median. Shared width scale, all9jitter centres c=-2..2 shown, missing gaps kept. Black ticks, if present, are frozen E020 band events at later position within this plotted range; no new physical event detection. Coincident lines are meaningful: monotone profiles may be unchanged. No case selection or extra smoothing.",str(a.run/"centre_estimates.csv"))

    originals=read_csv(a.source/"measurements.csv")
    fig=plt.figure(figsize=(11,9));gs=fig.add_gridspec(4,2,width_ratios=(1.25,1))
    with np.load(a.source/"source_arrays.npz",allow_pickle=False) as z:
        for j in range(4):
            ax=fig.add_subplot(gs[j,0]);key=f"st{j}_tr6_original_H_strip"
            ax.imshow(z[key],cmap="gray",vmin=0,vmax=255,extent=[-60.5,60.5,14.25,-14.25],aspect="auto")
            ax.axhspan(-4,4,color="#56B4E9",alpha=.15)
            for y in (-2,2): ax.axhline(y,color="#E69F00",lw=.8,ls="--")
            ax.axhline(0,color="white",lw=.8)
            group=[r for r in originals if int(r["stage_index"])==j and int(r["transect_id"])==6 and r["arm"]==ARMS[0]]
            group.sort(key=lambda r:int(r["t_index"]))
            for name,color in (("left_px","#56B4E9"),("right_px","#E69F00")):
                ax.plot([num(r,name) if boolean(r["valid"]) else np.nan for r in group],np.arange(-10,10.25,.5),color=color,lw=.8)
            ax.set(title=f"T6 | {LOADS[j]} kN | original photo crop",xlim=(-60,60),ylim=(14,-14),ylabel="Tangent native px")
            if j==3: ax.set_xlabel("Normal native px")
        trajectory=fig.add_subplot(gs[:2,1]);response=fig.add_subplot(gs[2:,1])
        for name,v,ls in (("point_px","point_valid","-"),("segment_px","segment_valid","--")):
            zero=[groups[(j,6,ARMS[0])][4] for j in range(4)]
            trajectory.plot(LOADS,[num(r,name) if boolean(r[v]) else np.nan for r in zero],ls=ls,marker="o",color="#555555" if ls=="-" else "#0072B2",label="point" if ls=="-" else "segment median")
        trajectory.set(xlabel="Observed nominal load (kN)",ylabel="Width at c0 (native px)",title="Fixed T6: load-stage trajectory",ylim=(0,ymax));trajectory.legend(fontsize=8);trajectory.grid(alpha=.15)
        for j in range(4):
            group=groups[(j,6,ARMS[0])]
            for name,v,ls in (("point_px","point_valid","-"),("segment_px","segment_valid","--")):
                response.plot(CENTRES,[num(r,name) if boolean(r[v]) else np.nan for r in group],color=COLORS[j],ls=ls,lw=1.3)
        response.set(xlabel="Centre shift (native px)",ylabel="Width (native px)",title="Same fixed T6: jitter response",ylim=(0,ymax),xlim=(-2,2));response.grid(alpha=.15)
        response.legend(handles=[Line2D([0],[0],color=COLORS[j],label=f"{LOADS[j]} kN") for j in range(4)],fontsize=8,loc="lower left",ncol=2)
    fig.suptitle("S03-E021-D01-R001 | fixed T6 source/support audit | no independent edge reference",fontsize=12)
    fig.tight_layout(rect=[0,.07,1,.95]);fig.text(.02,.01,"White: c0 point. Orange dashed horizontals: segment width-centres ±2px. Blue shade: inherited raw footprint ±4px at c0.\nCurved cyan/orange lines: original functional crossings, NOT human-visible edges. All-jitter raw union is ±6px.",fontsize=9)
    export(fig,a.output,"fixed_t6_support_and_load","What image area is aggregated and how does fixedT6 retain stage changes?",
           "Left4original photo crops with source gray0..255, c0 point line, width-centre segment bounds and larger inherited gray footprint. Crossings are original five-row functional projections only. Right top both methods' observed c0load trajectories; bottom all4stage jitter curves with solid point/dashed segment, using same width scale as atlas. FixedT6 chosen before aggregation outcomes, not selected for benefit.",str(a.source/"source_arrays.npz")+" plus "+str(a.run/"centre_estimates.csv"))

if __name__=="__main__": main()
