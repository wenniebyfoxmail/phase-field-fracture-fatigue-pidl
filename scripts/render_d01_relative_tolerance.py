"""E023 render saved tolerance tables and the separately audited load evidence."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
import numpy as np
from d01_short_support import ARMS, LOADS, read_csv, boolean
from d01_relative_tolerance import RHOS

COLORS=("#0072B2","#D55E00","#009E73")
def nullable(value):
    return None if value in ("", "None") else boolean(value)

def export(fig,out,stem,question,guide,source):
    for fmt in ("png","pdf"):fig.savefig(out/f"{stem}.{fmt}",dpi=170,bbox_inches="tight")
    plt.close(fig)
    (out/f"{stem}.md").write_text(f"""# {stem}
## Figure question
{question}
## Data and execution provenance
{source}. E023-R001, relative-tolerance-v1. Fixed E022-R001 table, clean247b8f6,
all12 Beam4 transects x3 transitions x2 location arms, one viewed specimen.
Renderer scripts/render_d01_relative_tolerance.py. Load audit is a separate
source-evidence check, not numerical execution or a forecast score.
## Panel guide and visual grammar
{guide}
## Key takeaway
Exact tables and interpretation in README_analysis.md and ../outputs/summary.json.
Direction means same sign as the nominal optical increment D0, not physical growth.
## Boundaries and missingness
Each stage's absolute tangent shift is bounded +/-2 nativepixels, grid .5px.
rho bounds relative shift |db-da| on a cumulative finite band. No interpolation
or subgrid guarantee; .5px spacing is not measurement precision. All81valid
cells and a nonzero valid D0 required; otherwise unassessable, not0orfailure.
rho0 loss is no admissible tolerance; stable through4 is right-censored on this
grid, not unlimited. No physical opening, independent position-reference,
actual correspondence, confidence/probability or forecast validation claim.
Coverage falls with nested sets by construction; no independent sample inference.
OriginalH primary, aligned secondary, no best-case selection; old width/scores unchanged.
## Related assets
Same-stem PNG/PDF; ../outputs/pair_bounds.csv; ../outputs/band_metrics.csv;
../outputs/summary.json; README_analysis.md; load_knowledge audit and reading record.
""")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--load-audit",type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    bands=read_csv(args.run/"band_metrics.csv");pairs=read_csv(args.run/"pair_bounds.csv");summary=json.loads((args.run/"summary.json").read_text());audit=json.loads(args.load_audit.read_text())
    if len(pairs)!=72 or len(bands)!=648:raise ValueError("render coverage")
    source=str(args.run)
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),sharey=True)
    for ai,arm in enumerate(ARMS):
        cov=summary["by_arm"][ai]["coverage"]
        for ax,field in zip(axes,("direction_stable","amplitude_stable")):
            values=[x[field] for x in cov]
            ax.plot(RHOS,values,"o-",color=COLORS[ai],label=f"{arm} ({summary['by_arm'][ai]['eligible']}/36 eligible)",lw=1.8)
            if field=="direction_stable" and ai==0:
                for x,y in zip(RHOS,values):ax.annotate(str(y),(x,y),xytext=(0,7),textcoords="offset points",ha="center",fontsize=8,color=COLORS[ai])
    for ax,title in zip(axes,("Primary: direction retained for ALL band cells","Secondary: max |difference - D0| < |D0|")):
        ax.set(title=title,xlabel="Relative-mismatch bound rho (native px)",xticks=RHOS,ylim=(-.5,37.5),yticks=range(0,37,6));ax.grid(alpha=.2)
    axes[0].set_ylabel("Stable stage/transect pairs /36 opportunities");axes[1].legend(fontsize=8,loc="upper right")
    fig.suptitle("Beam4: how tightly must stage positions correspond?",fontsize=13)
    fig.tight_layout(rect=[0,.1,1,.93]);fig.text(.02,.015,"Each absolute shift <=2px; cumulative finite grid, 0.5px spacing. D0 is nominal optical change, not truth. No physical precision claim.",fontsize=9)
    export(fig,args.output,"relative_tolerance_coverage","How many nominal directions survive each bounded relative mismatch?","Left: same direction as D0 for every tested cell in the band. Right: stricter-in-scale amplitude context, NOT a combined vote; EPS means the two rules are not mathematically identical. Blue originalH primary, orange aligned secondary; denominator36, full support reported.",source)

    matrices={};ratio_matrices={}
    for arm in ARMS:
        ordered=sorted([r for r in bands if r["arm"]==arm],key=lambda r:(int(r["stage_a"]),int(r["transect_id"]),float(r["rho_px"])))
        if len(ordered)!=324:raise ValueError("band arm coverage")
        matrices[arm]=np.array([2 if nullable(r["direction_stable"]) is None else int(nullable(r["direction_stable"])) for r in ordered]).reshape(36,9)
        ratio_matrices[arm]=np.array([float(r["max_deviation_to_signal"]) for r in ordered]).reshape(36,9)
    fig,axes=plt.subplots(1,2,figsize=(11,10.5),sharex=True,sharey=True)
    cmap=ListedColormap(["#E8A879","#82B8D5","#dddddd"]);norm=BoundaryNorm([-.5,.5,1.5,2.5],3)
    labels=[f"{LOADS[j]}-{LOADS[j+1]} | T{t:02d}" for j in range(3) for t in range(1,13)]
    for ax,arm in zip(axes,ARMS):
        ax.imshow(matrices[arm],aspect="auto",cmap=cmap,norm=norm,interpolation="nearest",extent=[-.25,4.25,35.5,-.5])
        ax.set(title=arm,xticks=RHOS,xlabel="Relative-mismatch bound rho (px)",yticks=range(36),yticklabels=labels)
        for y in (11.5,23.5):ax.axhline(y,color="white",lw=2)
        ax.tick_params(axis="y",labelsize=8)
    fig.legend(handles=[Patch(facecolor=cmap.colors[k],label=label) for k,label in enumerate(("Direction lost somewhere in band","Direction retained everywhere","Unassessable"))],loc="lower center",ncol=3,bbox_to_anchor=(.5,.045),fontsize=9)
    fig.suptitle("All36 stage/transect pairs per arm: finite-grid direction envelopes",fontsize=13)
    fig.tight_layout(rect=[0,.1,1,.95]);fig.text(.02,.012,"Orange at rho0 = no admissible tolerance, NOT '0px tolerance'. Blue through4 = right-censored on tested grid.\nEach absolute shift <=2px; untested in-between locations are not guaranteed. Rows are dependent observations, not36 specimens.",fontsize=9)
    export(fig,args.output,"all_pair_direction_envelopes","Which exact locations lose the nominal direction first?","Two categorical maps, all36rows each in transition/T1..12 order, all9rho columns. Blue retained; orange at least one zero/opposite increment; gray unassessable. The first orange column brackets loss only on tested grid. Entire blue row right-censored at4; orange first column no admissible bound. No hidden difficult positions.",source)

    finite=np.concatenate([m.ravel() for m in ratio_matrices.values()]);finite=finite[np.isfinite(finite)];top=max(float(finite.max()) if len(finite) else 1,1.)*1.12
    fig,axes=plt.subplots(1,2,figsize=(11,5),sharex=True,sharey=True)
    for ax,arm in zip(axes,ARMS):
        for row in range(36):ax.plot(RHOS,ratio_matrices[arm][row],color=COLORS[row//12],alpha=.55,lw=1)
        ax.axhline(1,color="black",ls="--",lw=1);ax.set(title=arm,xlabel="Relative-mismatch bound rho (px)",xticks=RHOS,yscale="symlog",ylim=(0,top));ax.set_yscale("symlog",linthresh=.1);ax.grid(alpha=.15)
    axes[0].set_ylabel("max |difference - D0| / |D0| (dimensionless; symlog)")
    fig.legend(handles=[plt.Line2D([0],[0],color=COLORS[j],label=f"{LOADS[j]}-{LOADS[j+1]} kN") for j in range(3)],loc="lower center",ncol=3,bbox_to_anchor=(.5,.06),fontsize=9)
    fig.suptitle("All36 response envelopes per arm: position response relative to nominal change",fontsize=12)
    fig.tight_layout(rect=[0,.17,1,.93]);fig.text(.02,.01,"Shared symlog y-scale (linear within0.1), all tails retained; dashed1 is one nominal increment, not physical measurement noise.\nAll lines shown, not a chosen typical case. Same finite +/-2px absolute support and0.5px grid; no probability interpretation.",fontsize=9)
    export(fig,args.output,"all_pair_amplitude_envelopes","Is bounded-location response comparable with the nominal optical increment?","Every pair line shown with transition colour. Shared symlog y-axis, linear0..0.1 and logarithmic tails, full maximum retained. Dashed1 is max|D-D0|=|D0|, equality fails strict amplitude guard; no physical noise threshold. Valid nonzero D0/full81support required; missing would be a gap, not0.",source)

    fig,ax=plt.subplots(figsize=(12,6.6));ax.axis("off")
    rows=[[f"B{q['beam']}",q["history_kN"],f"{q['origin_kN']} to {q['next_nominal_kN']}",q["source_cell"].split(" / ")[0]+"\n"+q["source_cell"].split(" / ")[1],q["exact_origin_availability"]] for q in audit["queries"]]
    table=ax.table(cellText=rows,colLabels=["Beam","History (kN)","Origin to next (kN)","Retrospective label source","Exact target known at origin?"],cellLoc="left",colLoc="left",colWidths=[.06,.12,.16,.34,.25],bbox=[0,.18,1,.68])
    table.auto_set_font_size(False);table.set_fontsize(9)
    for (r,c),cell in table.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if r==0:cell.set_facecolor("#e6edf2")
    ax.text(0,.98,"Load knowledge: planned protocol is supported; exact historical query availability is not demonstrated",fontsize=12,va="top",transform=ax.transAxes)
    ax.text(0,.91,"Primary paper: pre-defined load stops (Abstract / section2). Acquisition sheets: observed labels and times.",fontsize=10,transform=ax.transAxes)
    ax.text(0,.11,"Beam4 also lists20kN with blank times (Beam-time!A18); later unused nominal rows remain in the sheets.\nA general plan and a retrospective label do not certify which IB observation would next be included.",fontsize=10,transform=ax.transAxes)
    ax.text(0,.015,"Full main text checked; supplementary PDF blocked by browser challenge, not inspected. No claim that operators lacked a plan.\nOld eight queries remain retrospective nominal-load-conditioned DEVELOPMENT; no new forecast score or future-force input.",fontsize=9,transform=ax.transAxes)
    export(fig,args.output,"next_load_knowledge_audit","Was the exact next included nominal load documented as origin-known for each of eight historical queries?","Eight rows all retained; source cells are observed-label provenance, not proof of origin availability. Generic protocol supported by paper. Exact historical target availability not demonstrated in accessed sources. Full main text read, appendix PDF not inspected due access challenge; no categorical absence/unknown-to-operator claim. Future actual force differs from a planned nominal scenario input.",str(args.load_audit))

if __name__=="__main__":main()
