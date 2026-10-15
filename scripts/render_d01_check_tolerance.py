"""E024 exact-output figures: CHECK proxy versus tested directional envelope."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch
import numpy as np
from d01_short_support import ARMS,LOADS,read_csv,boolean
from d01_check_tolerance import STATES

COLORS=("#0072B2","#D55E00","#009E73","#CC79A7")
STATE_COLORS=("#95B9D2","#E8B66C","#D9898F","#BAA1C9","#dddddd")
STATE_LABELS=("Proxy-band compatible","Beyond stable band: check","Common-shift sensitive","Outside absolute grid: check","Unassessable")
def value(r,key):return float(r[key]) if r[key] not in ("","None") else np.nan
def order(r):return int(r["stage_a"]),int(r["transect_id"])
def export(fig,out,stem,question,guide,source):
    for fmt in ("png","pdf"):fig.savefig(out/f"{stem}.{fmt}",dpi=170,bbox_inches="tight")
    plt.close(fig)
    (out/f"{stem}.md").write_text(f"""# {stem}
## Figure question
{question}
## Data provenance
{source}; S03-E024-D01-R001 / check-tolerance-v1, controlled-experiment
DEVELOPMENT, one viewed Beam4. E019 background residuals and E023 finite bands,
all12transects/3transitions/both frozen arms. No rematching, fit, pixels sampled,
new model or forecast. Renderer scripts/render_d01_check_tolerance.py.
## Reading order and visual grammar
{guide}
## Numerical takeaway
Exact counts in ../outputs/summary.json; all72position rows and all288nominal
CHECK pairs retained. Per-arm opportunity denominator36; eligible CHECK support
141/144, original/after are not independent282 measurements. T1 uses the3
prespecified eligible CHECKs, not a new data-dependent subset.
## Limits and interpretation
Signed e is in frozen origin-native tangent pixels: original shift_t; after
shift_t-FITtranslation_t. No norm substitution or5616/2000 scaling. Reference
stage e0=0 by template definition, not independently verified zero error.
Matched M=max_k|ebk-eak|; absolute A=max|e|; ceil(M/.5)*.5 selects a tested rho.
This compares scales with an E023 FINITE grid, does not interpolate/guarantee
fractional positions or actual crack-centre displacement. CHECK patches are
away from crack, normal residual and matching uncertainty remain unqualified.
Compatible means conditional tangential optical-development proxy screen,
not physically usable localisation, verified crack width or future prediction.
Beyond band means further checking, NOT actual observed reversal. Common-
sensitive retained; outsideA2px is beyond tested support, not automatically fail.
Cartesian cross-CHECK comparison is spatial-transfer stress only, not ground
truth or a physical worst-case bound. Repair categories are pending, not repairs.
## Related assets
Same-stem PNG/PDF; README_analysis.md; ../outputs/position_comparison.csv;
../outputs/check_pair_residuals.csv; ../outputs/stage_residuals.csv.
""")

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    pairs=read_csv(args.run/"position_comparison.csv");stages=read_csv(args.run/"stage_residuals.csv");summary=json.loads((args.run/"summary.json").read_text())
    if len(pairs)!=72 or len(stages)!=384:raise ValueError("figure coverage")
    by_arm={arm:sorted([r for r in pairs if r["arm"]==arm],key=order) for arm in ARMS}
    if any(len(v)!=36 for v in by_arm.values()):raise ValueError("arm figure coverage")
    source=str(args.run)
    # All36 per arm: each absolute support test, and relative proxy versus tested bounds.
    fig,axes=plt.subplots(2,2,figsize=(14,7.8),sharex=True,sharey="row")
    for ai,arm in enumerate(ARMS):
        rows=by_arm[arm];x=np.arange(36)
        axes[0,ai].scatter(x,[value(r,"absolute_max_t_px") for r in rows],color="#555555",s=22,label="A = max absolute CHECK residual")
        axes[0,ai].axhline(2,color="#AA4499",ls="--",lw=1.2,label="E023 absolute-support limit2px")
        axes[1,ai].scatter(x,[value(r,"matched_max_relative_t_px") for r in rows],color="#222222",s=23,label="M: matched-CHECK relative residual",zorder=3)
        axes[1,ai].scatter(x,[value(r,"last_stable_tested_px") for r in rows],facecolors="none",edgecolors=COLORS[0],s=32,label="Last stable tested rho (4=right-censored)")
        axes[1,ai].scatter(x,[value(r,"first_loss_tested_px") for r in rows],color=COLORS[1],marker="x",s=27,label="First loss tested rho (0=no admissible)")
        axes[0,ai].set(title=arm,ylabel="Absolute tangent residual A (native px)")
        axes[1,ai].set(ylabel="Relative mismatch / tested rho (native px)",xlabel="Transect in each transition; all12 positions")
        for ax in axes[:,ai]:
            for line in (11.5,23.5):ax.axvline(line,color="#aaaaaa",lw=.7)
            ax.set(xticks=x,xticklabels=[str(t) for j in range(3) for t in range(1,13)],xlim=(-.8,35.8));ax.tick_params(axis="x",labelsize=7);ax.grid(axis="y",alpha=.15)
        for j in range(3):axes[0,ai].text(j*12+5.5,1.02,f"{LOADS[j]}-{LOADS[j+1]} kN",transform=axes[0,ai].get_xaxis_transform(),ha="center",fontsize=9)
    # Legends stay outside data panels.
    h0,l0=axes[0,0].get_legend_handles_labels();h1,l1=axes[1,0].get_legend_handles_labels()
    fig.legend(h0+h1,l0+l1,loc="lower center",ncol=2,bbox_to_anchor=(.5,.035),fontsize=8)
    fig.suptitle("E024-R001 | Beam4 DEVELOPMENT | CHECK tangent proxy versus E023 finite-grid support",fontsize=12)
    fig.tight_layout(rect=[0,.19,1,.94]);fig.text(.02,.005,"M is not the rounded rho_req: ceiling to0.5px is used for classification. Markers are tested grid bounds, NOT continuous safe intervals.\nA<=2px required; e0=0 by reference definition. Background CHECKs do not certify crack-centre/normal/physical accuracy.",fontsize=9)
    export(fig,args.output,"check_residual_vs_tolerance","How do absolute and relative CHECK scales compare with each location's tested envelope?","Two arms in columns. Top:A with2px support line. Bottom:blackM, open-blue last-stable grid rho, orangeX first-loss grid rho. All36pairs, three transition blocks. No continuous interval or background-to-crack error guarantee; full tails retained.",source)

    # Working categories, not binary physical pass/fail.
    fig,axes=plt.subplots(1,2,figsize=(11,9),sharey=True)
    cmap=ListedColormap(STATE_COLORS);norm=BoundaryNorm(np.arange(-.5,5,1),5)
    for ax,arm in zip(axes,ARMS):
        rows=by_arm[arm];matrix=np.array([STATES.index(r["status"]) for r in rows]).reshape(3,12).T
        ax.imshow(matrix,cmap=cmap,norm=norm,aspect="auto",interpolation="nearest")
        for r in rows:
            j,t=order(r);m,rho=value(r,"matched_max_relative_t_px"),value(r,"required_tested_rho_px")
            label=f"M={m:.2f}\nrho={rho:g}" if np.isfinite([m,rho]).all() else "missing"
            ax.text(j,t-1,label,ha="center",va="center",fontsize=9)
        ax.set(title=arm,xticks=range(3),xticklabels=[f"{LOADS[j]}-{LOADS[j+1]} kN" for j in range(3)],yticks=range(12),yticklabels=[f"T{t:02d}"+("*" if t==1 else "") for t in range(1,13)],xlabel="Observed stage transition")
    fig.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(STATE_COLORS,STATE_LABELS)],loc="lower center",bbox_to_anchor=(.5,.055),ncol=2,fontsize=9)
    fig.suptitle("E024-R001 | all12 local positions: conditional working categories",fontsize=13)
    fig.tight_layout(rect=[0,.18,1,.94]);fig.text(.02,.01,"*T1 has3/4 frozen eligible CHECKs; others4/4. M/rho are native tangent px. Missing and overlapping limitations remain in raw flags.\nBlue means proxy-band compatible only; orange means further local checking, NOT observed reversal. No physical usable/not-usable verdict.",fontsize=9)
    export(fig,args.output,"position_working_categories","Which locations can be retained under the conditional proxy screen, and which need which follow-up?","T1..12rows, three transitions in columns, botharms. Five predeclared categories, M/raw relative proxy andrho/ceiling displayed. T1star fixed3/4 support, not adaptive exclusion. Priority unassessable/common-sensitive/outside/compatible/beyond; parallel flags retained in tables. All opportunities displayed.",source)

    vals=[value(r,"residual_t_px") for r in stages if boolean(r["valid"])];lim=max(max(abs(np.array(vals))) if vals else 0,.1)*1.08
    fig,axes=plt.subplots(6,4,figsize=(13,13),sharex=True,sharey=True)
    for ai,arm in enumerate(ARMS):
        for t in range(1,13):
            ax=axes[ai*3+(t-1)//4,(t-1)%4]
            for k in range(4,8):
                rr=sorted([r for r in stages if r["arm"]==arm and int(r["transect_id"])==t and int(r["anchor_id"])==k],key=lambda r:int(r["stage_index"]))
                ys=[value(r,"residual_t_px") if boolean(r["valid"]) else np.nan for r in rr]
                ax.plot(LOADS,ys,"o-",color=COLORS[k-4],lw=1.2,ms=2.5,label=f"CHECK a{k}")
            ax.axhline(0,color="#aaaaaa",lw=.7);ax.set(title=f"{arm} | T{t:02d}",ylim=(-lim,lim),xticks=LOADS);ax.grid(alpha=.12)
            if (t-1)%4==0:ax.set_ylabel("Signed residual (native px)")
            if t>=9:ax.set_xlabel("Nominal load (kN)")
    h,l=axes[0,0].get_legend_handles_labels();fig.legend(h,l,loc="lower center",ncol=4,bbox_to_anchor=(.5,.025),fontsize=9)
    fig.suptitle("E024-R001 | every fixed CHECK trace, same tangent coordinates and shared signed scale",fontsize=12)
    fig.tight_layout(rect=[0,.07,1,.95]);fig.text(.02,.005,"10kN zero is a template-reference convention, NOT a measured zero error. T1a5 remains missing at all stages. No peak/filter/anchor tuning.\nOriginal and aligned are paired views of the same background matches; CHECK movement is not physical crack motion.",fontsize=9)
    export(fig,args.output,"all_check_signed_traces","Are residuals common across stages or independently drifting, and are they spatially uniform?","All12positions x2arms, each with CHECKa4..7 traces; stages10/30/40/50kN, shared signed nativepixel y-axis. Top12original, bottom12aligned. e0defined0. T1a5 absent throughout. No norm or magnitude-difference substitution, no unshown worst traces.",source)

    fig,axes=plt.subplots(1,2,figsize=(10,5),sharex=True,sharey=True)
    finite=[max(value(r,"matched_max_relative_t_px"),value(r,"cross_max_relative_t_px")) for r in pairs if boolean(r["complete_eligible_checks"])];lim=max(finite+[.1])*1.08
    for ai,(ax,arm) in enumerate(zip(axes,ARMS)):
        rows=by_arm[arm]
        for j in range(3):
            rr=[r for r in rows if int(r["stage_a"])==j and boolean(r["complete_eligible_checks"])]
            ax.scatter([value(r,"matched_max_relative_t_px") for r in rr],[value(r,"cross_max_relative_t_px") for r in rr],color=COLORS[j],s=30,alpha=.8,label=f"{LOADS[j]}-{LOADS[j+1]} kN")
        ax.plot([0,lim],[0,lim],color="#aaaaaa",ls="--",lw=1)
        stat=summary["by_arm"][ai]
        ax.text(.04,.96,f"Compatible /36:\nmatched {stat['states']['proxy_compatible']} -> cross {stat['cross_states']['proxy_compatible']}\nSECONDARY sensitivity",transform=ax.transAxes,va="top",fontsize=9)
        ax.set(title=arm,xlim=(0,lim),ylim=(0,lim),xlabel="Matched-ID M (native px)",ylabel="Cartesian CHECK M_cross (native px)");ax.set_aspect("equal");ax.grid(alpha=.15)
    h,l=axes[0].get_legend_handles_labels();fig.legend(h,l,loc="lower center",ncol=3,bbox_to_anchor=(.5,.065),fontsize=9)
    fig.suptitle("E024-R001 | background spatial-transfer stress, NOT a physical worst-case bound",fontsize=12)
    fig.tight_layout(rect=[0,.17,1,.94]);fig.text(.02,.01,"Cross-ID pairs combine DIFFERENT background patches; M_cross>=M by construction. They do not replace same-anchor primary drift.\nNo extrema bound for the actual crack centre is established. All36pairs/arm; shared axes, no confidence/generalisation claim.",fontsize=9)
    export(fig,args.output,"matched_vs_cross_check","How sensitive is the conditional screen to transferring across different CHECK patches?","All36perarm; horizontal same-IDM, vertical CartesianM_cross, shared pixelaxes. Identity-line inequality is nested by construction, NOT new evidence. Annotation compares predeclared primary versus labelled secondary working categories, not physical coverage or worst-case risk.",source)

if __name__=="__main__":main()
