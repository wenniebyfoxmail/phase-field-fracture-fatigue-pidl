"""Read-only plots of frozen tangent response and operational band candidates."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from d01_tangent_width_response import TANGENTS,ARMS

COLORS={0:"#0072B2",1:"#D55E00",2:"#009E73",3:"#CC79A7"}
LOADS=(10,30,40,50)

def read(p):
    with p.open(newline="") as f: return list(csv.DictReader(f))

def yes(x): return str(x).lower()=="true"
def num(r,k): return float(r[k])

def ordered(r):
    return int(r["stage_index"]),int(r["transect_id"]),ARMS.index(r["arm"]),int(r.get("t_index_a",r.get("t_index",0)))

def export(fig,out,stem,question,reading,takeaway,source):
    for fmt in ("png","pdf"): fig.savefig(out/f"{stem}.{fmt}",dpi=170,bbox_inches="tight")
    plt.close(fig)
    (out/f"{stem}.md").write_text(f"""# How to read {stem}
## Figure question
{question}
## Data provenance
{source}
S03-E020-D01-R001; Beam4 only, controlled-experiment DEVELOPMENT; original H versus frozen E019 background translation. Renderer `scripts/render_d01_tangent_response.py`. All12transects/all4stages;41 centres per curve, tangent-10..10 at0.5 native px. Source images are original photos, not AI-generated.
## Visual grammar and panel guide
{reading}
## Key numerical takeaway
{takeaway}
## Limitations and claim boundary
Five-line-median profile half-depth crossings are projected onto raw central strips for explanation; they are NOT central-row human edge annotations or physical aperture ground truth. Band-switch/merge/split are operational candidates at each profile's own half-depth level, not proven algorithm errors or physical branch identities. Peak wandering within the same band is not a switch. No event at this sampling grid does not prove smooth physical truth. One viewed specimen, overlapping positions and dependent rows; no confidence intervals/generalisation claim, no new forecast/target/registration fit or smoothing. Invalid values remain missing.
## Related assets
`summary.json`, all-row input CSVs, `diagnostic_selections.json`, `README_analysis.md`; same-stem PNG/PDF share this note.
""")


def draw_strip(ax,z,key,rows):
    if key+"_strip" not in z.files:
        ax.text(.5,.5,"Unavailable source correction",transform=ax.transAxes,ha="center"); return
    ax.imshow(z[key+"_strip"],cmap="gray",vmin=0,vmax=255,extent=[-60.5,60.5,14.25,-14.25],aspect="auto")
    for name,color,style in (("left_px","#56B4E9","-"),("right_px","#E69F00","-"),("peak_px","#CC79A7","--")):
        values=[num(r,name) if yes(r["valid"]) else np.nan for r in rows]
        ax.plot(values,TANGENTS,color=color,ls=style,lw=1.1)
    ax.axhline(0,color="white",lw=.5,alpha=.6)
    ax.set(xlim=(-60,60),ylim=(14,-14),xlabel="Normal native px",ylabel="Tangent native px")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    rows=read(a.run/"measurements.csv"); pairs=read(a.run/"adjacent_pairs.csv"); curves=read(a.run/"curve_summaries.csv")
    assert len(rows)==3936 and len(pairs)==3840 and len(curves)==96
    assert len({ordered(r) for r in rows})==3936
    assert len({ordered(r) for r in pairs})==3840
    groups={}
    for r in rows: groups.setdefault(ordered(r)[:3],[]).append(r)
    assert len(groups)==96
    for group in groups.values():
        group.sort(key=lambda r:int(r["t_index"]))
        assert [num(r,"tangent_px") for r in group]==TANGENTS.tolist()
    summary=[]
    for arm in ARMS:
        rp=[r for r in pairs if r["arm"]==arm and yes(r["paired_valid"])]
        events=[r for r in rp if yes(r["any_band_event"])]
        cr=[r for r in curves if r["arm"]==arm]
        summary.append(dict(arm=arm,valid_profiles=sum(yes(r["valid"]) for r in rows if r["arm"]==arm),profiles=1968,
                            paired_adjacent=len(rp),adjacent_opportunities=1920,band_event_pairs=len(events),
                            band_event_fraction=len(events)/len(rp) if rp else None,
                            switch_candidates=sum(yes(r["switch_candidate"]) for r in rp),
                            split_candidates=sum(yes(r["split_candidate"]) for r in rp),
                            merge_candidates=sum(yes(r["merge_candidate"]) for r in rp),
                            curves_with_events=sum(int(r["band_events"])>0 for r in cr),curves=48,
                            median_width_range_px=float(np.nanmedian([num(r,"width_range_px") for r in cr])),
                            max_adjacent_width_change_px=max([abs(num(r,"width_change_px")) for r in rp],default=None),
                            max_adjacent_peak_change_px=max([abs(num(r,"peak_change_px")) for r in rp],default=None)))
    finite_widths=[num(r,"width_px") for r in rows if yes(r["valid"])]
    ymax=max(finite_widths+[1])*1.05
    fig,axes=plt.subplots(4,3,figsize=(12,11),sharex=True,sharey=True)
    for t,ax in enumerate(axes.flat,1):
        for j in range(4):
            for ai,arm in enumerate(ARMS):
                group=groups[(j,t,ai)]
                w=[num(r,"width_px") if yes(r["valid"]) else np.nan for r in group]
                ax.plot(TANGENTS,w,color=COLORS[j],ls="-" if ai==0 else "--",lw=1.1)
        ax.axvline(0,color="#aaaaaa",lw=.6)
        ax.set(title=f"Transect {t}",xlim=(-10,10),ylim=(0,ymax))
        ax.grid(alpha=.15)
        if t>=10: ax.set_xlabel("Tangent displacement (native px)")
        if (t-1)%3==0: ax.set_ylabel("Half-depth width (native px)")
    legend=[Line2D([0],[0],color=COLORS[j],label=f"{LOADS[j]} kN") for j in range(4)]
    legend += [Line2D([0],[0],color="#555555",ls=ls,label=arm) for ls,arm in (("-",ARMS[0]),("--",ARMS[1]))]
    fig.legend(handles=legend,loc="lower center",ncol=6,bbox_to_anchor=(.5,.03),fontsize=9)
    fig.suptitle("Beam4 fixed tangential response | all12 transects / all4 stages",fontsize=14)
    fig.tight_layout(rect=[0,.08,1,.95])
    export(fig,a.output,"all_tangent_width_responses","How much does the SAME width functional change over the fixed local tangent range?",
           "Twelve transect panels share width axes0..data-wide maximum. Four stage colours; solid originalH, dashed frozen background correction; t0gray line. All41positions shown without smoothing, invalid gaps retained. This is spatial displacement, not future time.",
           json.dumps(summary),str(a.run/"measurements.csv"))

    deltas=[]
    for ai in range(2):
        data=[]
        for j in range(4):
            for t in range(1,13):
                group=groups[(j,t,ai)]
                zero=num(group[20],"width_px") if yes(group[20]["valid"]) else np.nan
                data.append([num(r,"width_px")-zero if yes(r["valid"]) else np.nan for r in group])
        deltas.append(np.array(data))
    finite=np.concatenate([d.ravel() for d in deltas]); finite=finite[np.isfinite(finite)]
    clim=max(float(np.max(abs(finite))) if len(finite) else 1,1e-6)
    fig,axes=plt.subplots(1,2,figsize=(10,8),sharex=True,sharey=True)
    for ai,ax in enumerate(axes):
        cm=plt.get_cmap("RdBu_r").copy();cm.set_bad("#eeeeee")
        im=ax.imshow(deltas[ai],cmap=cm,vmin=-clim,vmax=clim,aspect="auto",extent=[-10.25,10.25,47.5,-.5])
        for r in pairs:
            if r["arm"]==ARMS[ai] and yes(r["any_band_event"]):
                y=int(r["stage_index"])*12+int(r["transect_id"])-1
                ax.plot(num(r,"tangent_b_px"),y,"k|",ms=4,mew=.8)
        for boundary in (11.5,23.5,35.5): ax.axhline(boundary,color="#555555",lw=.6)
        ax.set(title=ARMS[ai],xlabel="Tangent displacement (native px)",yticks=[5.5,17.5,29.5,41.5],yticklabels=["10 kN | T1..12","30 kN | T1..12","40 kN | T1..12","50 kN | T1..12"])
    fig.colorbar(im,ax=axes.ravel().tolist(),label="Width(t) - width(0), native px",fraction=.035,pad=.04)
    fig.suptitle("Spatial width response relative to each curve's t0 | black ticks: band events",fontsize=12)
    fig.subplots_adjust(bottom=.12,top=.91,left=.15,right=.85,wspace=.15)
    fig.text(.02,.02,"All96 curves; row order stage then transect. Shared symmetric colour scale; gray=unavailable.\nHalf-level component events are candidates, NOT physical truth or proof of an algorithm mistake.",fontsize=9)
    export(fig,a.output,"tangent_response_map","Where are width responses and operational band events concentrated?",
           "Two48-row panels, identical symmetric signed scale around each curve's own t0. Stage separators; transect1..12 within each block. Black ticks denote event union at the later adjacent position. Gray invalid values are not zero. Colour changes are spatial response, not stage growth.",json.dumps(summary),str(a.run/"measurements.csv")+" and adjacent_pairs.csv")

    all_valid_pairs=sorted([r for r in pairs if yes(r["paired_valid"])],key=ordered)
    event_pairs=[r for r in all_valid_pairs if yes(r["any_band_event"])]
    selected=[]
    if event_pairs: selected.append(dict(rule="first_operational_band_event",**event_pairs[0]))
    if all_valid_pairs:
        worst=max(all_valid_pairs,key=lambda r:abs(num(r,"width_change_px")))
        if not selected or ordered(worst)!=ordered(selected[0]): selected.append(dict(rule="largest_absolute_adjacent_width_change",**worst))
        else: selected[0]["rule"]+="; also_largest_absolute_adjacent_width_change"
    (a.output/"diagnostic_selections.json").write_text(json.dumps(selected,indent=2)+"\n")
    with np.load(a.run/"source_arrays.npz",allow_pickle=False) as z:
        fig,axes=plt.subplots(4,2,figsize=(10,10))
        for j in range(4):
            group=groups[(j,6,0)];key=f"st{j}_tr6_original_H"
            draw_strip(axes[j,0],z,key,group)
            axes[j,0].set_title(f"T6 | {LOADS[j]} kN | original source + functional crossings")
            for ai,arm in enumerate(ARMS):
                group_arm=groups[(j,6,ai)]
                axes[j,1].plot(TANGENTS,[num(r,"width_px") if yes(r["valid"]) else np.nan for r in group_arm],color="#555555" if ai==0 else "#0072B2",ls="-" if ai==0 else "--",label=arm)
            axes[j,1].set(xlim=(-10,10),ylim=(0,ymax),xlabel="Tangent displacement (native px)",ylabel="Half-depth width (native px)",title=f"T6 | {LOADS[j]} kN spatial response")
        axes[0,1].legend(fontsize=8)
        fig.suptitle("Fixed T6 source audit | cyan left / orange right / purple selected peak",fontsize=13)
        fig.tight_layout(rect=[0,.04,1,.96]);fig.text(.02,.005,"Curves on strips are projections of the FIVE-line median functional, not independent human-visible edges.",fontsize=9)
        export(fig,a.output,"fixed_t6_source_response","Does peak wandering or edge motion explain the fixedT6 response?",
               "Four stage rows. Left raw local source grayscale0..255 with left/right half-depth crossings and selected peak projected at each tangent. Right width response in both frozen arms, same scale as all-case atlas. All4stages andT6 preselected regardless of outcome; tangent y downward on strip, horizontal on response curve.",
               "Fixed example; all numerical findings in summary and complete tables. Large peak jumps within the same wide band do not by themselves indicate edge switching.",str(a.run/"source_arrays.npz")+" and measurements.csv")
        all_ds=[]
        for r in selected:
            k=f"st{r['stage_index']}_tr{r['transect_id']}_{r['arm']}"
            idx=int(r["t_index_a"]);all_ds.extend(z[k+"_deficits"][[idx,idx+1]].ravel())
        limits=(min([0.]+all_ds)-5,max([10.]+all_ds)*1.08)
        for case,r in enumerate(selected,1):
            j,t,ai,_=ordered(r);group=groups[(j,t,ai)];idx=int(r["t_index_a"])
            key=f"st{j}_tr{t}_{r['arm']}"
            fig,axes=plt.subplots(1,3,figsize=(12,4))
            draw_strip(axes[0],z,key,group)
            for tangent in (TANGENTS[idx],TANGENTS[idx+1]): axes[0].axhline(tangent,color="white",lw=.8,ls=":")
            axes[1].plot([num(v,"width_px") if yes(v["valid"]) else np.nan for v in group],TANGENTS,color="#0072B2",lw=1.2)
            axes[1].plot([num(group[ii],"width_px") for ii in (idx,idx+1)],TANGENTS[[idx,idx+1]],"o",color="#D55E00",ms=4)
            axes[1].set(xlabel="Half-depth width (native px)",ylabel="Tangent native px",ylim=(14,-14))
            for ii,color in ((idx,"#0072B2"),(idx+1,"#D55E00")):
                rr=group[ii];d=z[key+"_deficits"][ii]
                s=np.arange(-60,60.25,.25);half=num(rr,"depth")/2
                axes[2].plot(s,d,color=color,lw=1.2,label=f"t={TANGENTS[ii]:g}")
                axes[2].hlines(half,num(rr,"left_px"),num(rr,"right_px"),color=color,lw=2)
                axes[2].plot(num(rr,"peak_px"),num(rr,"depth"),"x",color=color,ms=5)
            axes[2].set(xlim=(-60,60),ylim=limits,xlabel="Normal native px",ylabel="Darkness deficit (gray)")
            axes[2].legend(fontsize=8)
            fig.suptitle(f"Case{case}: {r['rule']} | T{t}, {LOADS[j]} kN, {r['arm']}",fontsize=11)
            fig.tight_layout(rect=[0,.1,1,.91])
            fig.text(.02,.01,f"Adjacent t={TANGENTS[idx]:g}->{TANGENTS[idx+1]:g}; width change={num(r,'width_change_px'):.3f}px.\nSwitch={r['switch_candidate']}, merge={r['merge_candidate']}, split={r['split_candidate']}; candidates only.",fontsize=9)
            export(fig,a.output,f"diagnostic_case_{case}","What source/profile change accompanies a deterministically selected diagnostic pair?",
                   "Left raw strip + crossings/peak, white lines mark paired tangent positions. Middle full width response with pair highlighted. Right both original deficit profiles, half-depth intervals and peak crosses; shared deficit y limits across selected cases. Rule is first event or maximal adjacent width jump, fixed before execution. Not a representative frequency estimate.",json.dumps(r),str(a.run/"source_arrays.npz")+"; selection in diagnostic_selections.json")
    replay=read(a.run/"t0_replay.csv")
    result=dict(experiment_id="S03-E020-D01",profiles=3936,curves=96,adjacent_opportunities=3840,by_arm=summary,
                t0_replay_rows=len(replay),t0_max_width_difference_px=max([num(r,"abs_replay_difference_px") for r in replay if yes(r["t0_valid"])],default=None),
                diagnostic_cases=len(selected),physical_reference=False,new_forecast_scores=False)
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
