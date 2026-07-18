#!/usr/bin/env python3
"""Unlock c89 once, aggregate the frozen matrix, and render decision assets."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_mechanism_operator import MultiScaleMeshResidualOperator, PointwiseResidualOperator, StateStatistics
from train_cycle_forecast_data_efficiency import (
    ALLOWED_CONTEXTS, ALLOWED_TRAIN_ENDS, LOCKED_CYCLE, NEAR_EVENT_ORIGIN,
    build_model, field_metrics, input_dim, load_dataset, metric_row, rollout, sha256,
)

HEADLINE_HORIZONS = (1, 3, 5, 10)
RELIABLE = {
    "damage_mae": 0.020,
    "history_log_mae": 0.030,
    "derived_active_log_mae": 0.50,
    "derived_active_correlation": 0.80,
    "absolute_p99_iou": 0.50,
    "own_p99_iou": 0.50,
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def cell_dirs(root: Path) -> list[Path]:
    cells = sorted(path.parent for path in root.glob("**/RUN_MANIFEST.json"))
    expected = {("pointwise", c, 1) for c in ALLOWED_TRAIN_ENDS}
    expected |= {("temporal_mesh", c, k) for c in ALLOWED_TRAIN_ENDS for k in ALLOWED_CONTEXTS}
    found = set()
    for path in cells:
        manifest = json.loads((path / "RUN_MANIFEST.json").read_text())
        found.add((manifest["model"], int(manifest["train_end"]), int(manifest["context_k"])))
    missing = sorted(expected - found)
    if missing:
        raise ValueError(f"matrix incomplete; missing cells: {missing}")
    return cells


def args_for_manifest(manifest: dict):
    class A: pass
    a = A()
    a.model = manifest["model"]; a.context = int(manifest["context_k"])
    a.hidden = 96; a.pointwise_hidden = 400; a.local_layers = 3; a.coarse_layers = 2
    return a


def load_frozen_model(cell: Path, manifest: dict, device):
    checkpoint = torch.load(cell / "final_model.pt", map_location=device, weights_only=False)
    model = build_model(args_for_manifest(manifest)).to(device)
    model.load_state_dict(checkpoint["model"])
    statistics = StateStatistics(*(checkpoint["statistics"][name].to(device) for name in
        ("state_mean", "state_std", "residual_mean", "residual_std")))
    return model, statistics


def persistence_rows(state_np, areas):
    rows = []
    for train_end in ALLOWED_TRAIN_ENDS:
        for origin, max_h in ((train_end, min(10, 88 - train_end)), (NEAR_EVENT_ORIGIN, 12)):
            for horizon in range(1, max_h + 1):
                cycle = origin + horizon
                row = metric_row("persistence", train_end, 1, origin, cycle,
                                 state_np[origin - 1], state_np[cycle - 1], areas,
                                 "cutoff_rollout" if origin == train_end else "near_event_rollout")
                row["headline_horizon"] = horizon in HEADLINE_HORIZONS
                row["runtime_seconds"] = 0.0; row["parameter_count"] = 0
                rows.append(row)
        row = metric_row("persistence", train_end, 1, NEAR_EVENT_ORIGIN, LOCKED_CYCLE,
                         state_np[NEAR_EVENT_ORIGIN - 1], state_np[LOCKED_CYCLE - 1], areas,
                         "locked_c89_final")
        row["headline_horizon"] = False; row["runtime_seconds"] = 0.0; row["parameter_count"] = 0
        rows.append(row)
    return rows


def passes(row):
    return (float(row["damage_mae"]) <= RELIABLE["damage_mae"]
            and float(row["history_log_mae"]) <= RELIABLE["history_log_mae"]
            and float(row["derived_active_log_mae"]) <= RELIABLE["derived_active_log_mae"]
            and float(row["derived_active_correlation"]) >= RELIABLE["derived_active_correlation"]
            and float(row["absolute_p99_iou"]) >= RELIABLE["absolute_p99_iou"]
            and float(row["own_p99_iou"]) >= RELIABLE["own_p99_iou"]
            and 0.67 <= float(row["absolute_support_area_ratio"]) <= 1.50)


def choose_context(rows):
    candidates = [r for r in rows if r["model"] == "temporal_mesh"
                  and r["phase"] == "near_event_rollout" and int(r["horizon"]) == 10]
    score = {}
    for k in ALLOWED_CONTEXTS:
        selected = [r for r in candidates if int(r["context_k"]) == k]
        score[k] = float(np.mean([float(r["derived_active_log_mae"]) for r in selected]))
    return min(score, key=score.get), score


def render_heatmap(rows, out):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.8), constrained_layout=True)
    for ax, train_end in zip(axes, ALLOWED_TRAIN_ENDS):
        matrix = np.full((len(ALLOWED_CONTEXTS), len(HEADLINE_HORIZONS)), np.nan)
        for i, k in enumerate(ALLOWED_CONTEXTS):
            for j, h in enumerate(HEADLINE_HORIZONS):
                match = [r for r in rows if r["model"] == "temporal_mesh"
                         and int(r["train_end"]) == train_end and int(r["context_k"]) == k
                         and r["phase"] == "cutoff_rollout" and int(r["horizon"]) == h]
                if match: matrix[i, j] = float(match[0]["derived_active_log_mae"])
        vmax=np.nanpercentile(matrix, 95)
        image = ax.imshow(matrix, vmin=0, vmax=vmax, cmap="magma_r", aspect="auto")
        ax.set_title(f"train through c{train_end}"); ax.set_xticks(range(4), HEADLINE_HORIZONS)
        ax.set_yticks(range(4), ALLOWED_CONTEXTS); ax.set_xlabel("rollout horizon")
        if train_end == ALLOWED_TRAIN_ENDS[0]: ax.set_ylabel("context k")
        for i in range(4):
            for j in range(4):
                if np.isfinite(matrix[i, j]):
                    colour="white" if matrix[i,j] > .62*vmax else "black"
                    ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=8, color=colour)
    fig.colorbar(image, ax=axes, label="derived active-driver log-MAE")
    fig.savefig(out / "context_length_x_rollout_horizon_heatmap.png", dpi=220)
    plt.close(fig)


def render_rollout_growth(rows, out):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 4.8), constrained_layout=True)
    for k in ALLOWED_CONTEXTS:
        selected = sorted((r for r in rows if r["model"] == "temporal_mesh"
                           and int(r["train_end"]) == 67 and int(r["context_k"]) == k
                           and r["phase"] in ("near_event_rollout", "locked_c89_final")),
                          key=lambda r: int(r["horizon"]))
        nonlocked=[r for r in selected if int(r["horizon"]) <= 10]
        locked=[r for r in selected if int(r["horizon"]) == 13]
        line=ax.plot([int(r["horizon"]) for r in nonlocked],
                     [float(r["derived_active_log_mae"]) for r in nonlocked], marker="o", label=f"k={k}")[0]
        if locked:
            ax.plot([10,13],[float(nonlocked[-1]["derived_active_log_mae"]),float(locked[0]["derived_active_log_mae"])],
                    marker="o",ls="--",color=line.get_color())
    ax.axhline(RELIABLE["derived_active_log_mae"], color="black", ls="--", lw=1, label="active gate")
    ax.set(xlabel="horizon from observed c76", ylabel="derived active-driver log-MAE",
           title="Near-event recurrent rollout error growth")
    ax.legend(ncol=3); fig.savefig(out / "near_event_rollout_error_growth.png", dpi=220); plt.close(fig)


def render_fields(data, target, prediction, out, label):
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    xy = np.asarray(data["coordinates"])
    pred_active = prediction[:, 3] + 2 * np.log10(np.maximum(1 - prediction[:, 0], 1e-12))
    fem_active = target[:, 3] + 2 * np.log10(np.maximum(1 - target[:, 0], 1e-12))
    fields = [(target[:,0], prediction[:,0], prediction[:,0]-target[:,0], "damage"),
              (np.log10(np.maximum(target[:,1],1e-12)), np.log10(np.maximum(prediction[:,1],1e-12)),
               np.log10(np.maximum(prediction[:,1],1e-12))-np.log10(np.maximum(target[:,1],1e-12)), "history log10"),
              (target[:,3], prediction[:,3], prediction[:,3]-target[:,3], "raw driver log10"),
              (fem_active, pred_active, pred_active-fem_active, "active driver log10")]
    fig, axes = plt.subplots(4, 3, figsize=(11, 12), constrained_layout=True)
    for i, (truth, pred, resid, name) in enumerate(fields):
        common=(np.nanpercentile(np.r_[truth,pred],1),np.nanpercentile(np.r_[truth,pred],99))
        for j,(values,title) in enumerate(((truth,"FEM"),(pred,label),(resid,f"{label} - FEM"))):
            if j==2:
                bound=max(abs(np.nanpercentile(resid,1)),abs(np.nanpercentile(resid,99)))
                kw={"cmap":"RdBu_r","vmin":-bound,"vmax":bound}
            else: kw={"cmap":"viridis","vmin":common[0],"vmax":common[1]}
            sc=axes[i,j].scatter(xy[:,0],xy[:,1],c=values,s=.18,rasterized=True,**kw)
            axes[i,j].set_title(f"{name}: {title}"); axes[i,j].set_aspect("equal"); axes[i,j].axis("off")
            fig.colorbar(sc,ax=axes[i,j],shrink=.7)
    fig.savefig(out / "fem_field_residual_panel_c89.png", dpi=220); plt.close(fig)
    # Absolute and own-p99 support masks.
    areas=np.asarray(data["areas"],dtype=float); order=np.argsort(fem_active); cum=np.cumsum(areas[order])
    tau=fem_active[order[np.searchsorted(cum,.99*cum[-1])]]
    orderp=np.argsort(pred_active); cump=np.cumsum(areas[orderp]); taup=pred_active[orderp[np.searchsorted(cump,.99*cump[-1])]]
    fig,axes=plt.subplots(1,2,figsize=(9,4),constrained_layout=True)
    for ax,pmask,title in ((axes[0],pred_active>=tau,"common FEM p99"),(axes[1],pred_active>=taup,"own p99")):
        fmask=fem_active>=tau; code=fmask.astype(int)+2*pmask.astype(int)
        colours=["#d9d9d9","#377eb8","#ff7f00","#f2d13d"]
        ax.scatter(xy[:,0],xy[:,1],c=code,s=.25,cmap=ListedColormap(colours),vmin=-.5,vmax=3.5,rasterized=True)
        ax.set_title(title); ax.set_aspect("equal"); ax.axis("off")
    axes[0].legend(handles=[Patch(color="#d9d9d9",label="neither"),Patch(color="#377eb8",label="FEM only"),
                            Patch(color="#ff7f00",label="prediction only"),Patch(color="#f2d13d",label="overlap")],
                   loc="upper right",fontsize=8,frameon=True)
    fig.savefig(out / "fem_active_support_panel_c89.png",dpi=220); plt.close(fig)


def write_decision(rows, out, selected_k, context_scores):
    temporal = [r for r in rows if r["model"] == "temporal_mesh"]
    one_step = [r for r in temporal if r["phase"] == "cutoff_rollout" and int(r["horizon"]) == 1]
    reliable_train = [c for c in ALLOWED_TRAIN_ENDS if any(int(r["train_end"]) == c and passes(r) for r in one_step)]
    minimum = min(reliable_train) if reliable_train else None
    near = sorted((r for r in temporal if int(r["train_end"]) == 67 and int(r["context_k"]) == selected_k
                   and r["phase"] in ("near_event_rollout", "locked_c89_final")), key=lambda r:int(r["horizon"]))
    stable = [int(r["horizon"]) for r in near if passes(r)]
    first_failure = next((r for r in near if not passes(r)), None)
    locked = next(r for r in near if r["phase"] == "locked_c89_final")
    text = f"""# FEM Cycle Forecast Data-Efficiency Decision

## Verdict

- Minimum reliable training cutoff among tested values: **{f'c{minimum}' if minimum else 'none of c20/c40/c60/c67 passed the predeclared full FEM-centred one-step gate'}**. Cutoffs below c20 were not tested.
- Nominal global history choice: **k={selected_k}**, selected before opening c89 by mean c76-origin h10 active log-MAE across training cutoffs ({context_scores}). Treat near-ties as no robust context advantage.
- Stable recurrent rollout under the full gate: **{max(stable) if stable else 0} cycles** from observed c76 for the c67-trained selected model.
- First near-event failure: **{f'h={first_failure["horizon"]}, target c{first_failure["target_cycle"]}' if first_failure else 'not observed through c89'}**.
- Locked c89: active log-MAE `{float(locked['derived_active_log_mae']):.4f}`, correlation `{float(locked['derived_active_correlation']):.4f}`, absolute-p99 IoU `{float(locked['absolute_p99_iou']):.4f}`, support ratio `{float(locked['absolute_support_area_ratio']):.3f}`.

## Interpretation

The minimum cutoff is sufficiency on the requested grid, not a universal lower bound. Persistence must remain visible because smooth one-step states can be easy without learning. Extra history is useful only when it extends the full FEM-centred support gate; lower log-MAE without p99 support overlap is not a stable rollout. A catastrophic c89 support expansion across every k means that more copies of the same four fields are insufficient and an additional regime-sensitive observation or state is required.

## Interpretation boundary

This is real FEM eta=0 evidence for within-trajectory temporal forecasting only. Exactly one complete compatible trajectory was available, so leave-one-trajectory-out validation was impossible. The result does not establish transfer across geometry, load amplitude, material parameters, mesh, or physical trajectory.

## Firewall

Every cell normalized and trained only on c1 through its declared cutoff. Architecture, optimizer, seed, metrics, thresholds, and 3000-step budget were frozen before c89 was opened. Context selection used nonlocked c77-c86 targets only. c89 was evaluated once after all checkpoints and the context choice were frozen.

## Reliability gate

Damage MAE <= 0.020; history log-MAE <= 0.030; derived-active log-MAE <= 0.50 and correlation >= 0.80; absolute and own-p99 IoU >= 0.50; absolute support-area ratio in [0.67, 1.50]. These are benchmark engineering gates, not universal fracture constants.
"""
    (out / "decision.md").write_text(text, encoding="utf-8")


def main(args):
    args.out.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    data, states, graph = load_dataset(args.dataset, device)
    state_np=np.asarray(data["states"],dtype=np.float32); areas=np.asarray(data["areas"],dtype=float)
    rows=[]; locked_predictions={}
    cells=cell_dirs(args.runs)
    for cell in cells:
        manifest=json.loads((cell/"RUN_MANIFEST.json").read_text())
        if manifest["dataset_sha256"] != sha256(args.dataset): raise ValueError(f"dataset hash mismatch: {cell}")
        rows.extend(read_csv(cell/"nonlocked_metrics.csv"))
    selected_k, scores=choose_context(rows)
    selection={"selected_context_k":selected_k,"selection_metric":"mean near-event c76-origin h10 active log-MAE across train cutoffs","scores":scores,"c89_opened":False}
    (args.out/"PRE_C89_SELECTION.json").write_text(json.dumps(selection,indent=2)+"\n")
    selection_hash=sha256(args.out/"PRE_C89_SELECTION.json")
    # Only now predict to c89 and index the locked target.
    for cell in cells:
        manifest=json.loads((cell/"RUN_MANIFEST.json").read_text()); model,statistics=load_frozen_model(cell,manifest,device)
        started=time.time(); known=states[NEAR_EVENT_ORIGIN-int(manifest["context_k"]):NEAR_EVENT_ORIGIN]
        prediction=rollout(model,known,NEAR_EVENT_ORIGIN,LOCKED_CYCLE-NEAR_EVENT_ORIGIN,graph,statistics)[LOCKED_CYCLE].cpu().numpy()
        elapsed=time.time()-started
        target=state_np[LOCKED_CYCLE-1]
        row=metric_row(manifest["model"],int(manifest["train_end"]),int(manifest["context_k"]),NEAR_EVENT_ORIGIN,LOCKED_CYCLE,prediction,target,areas,"locked_c89_final")
        row["headline_horizon"]=False; row["runtime_seconds"]=elapsed; row["parameter_count"]=manifest["parameter_count"]
        rows.append(row); locked_predictions[f"{manifest['model']}_c{manifest['train_end']}_k{manifest['context_k']}"]=prediction
    rows.extend(persistence_rows(state_np,areas))
    rows=sorted(rows,key=lambda r:(r["model"],int(r["train_end"]),int(r["context_k"]),r["phase"],int(r["horizon"])))
    write_csv(args.out/"data_efficiency_matrix.csv",rows)
    np.savez_compressed(args.out/"locked_c89_predictions.npz",**locked_predictions)
    render_heatmap(rows,args.out); render_rollout_growth(rows,args.out)
    key=f"temporal_mesh_c67_k{selected_k}"; render_fields(data,state_np[88],locked_predictions[key],args.out,f"temporal k={selected_k}")
    write_decision(rows,args.out,selected_k,scores)
    manifest={"schema":"fem_cycle_forecast_matrix_v1","dataset":str(args.dataset.resolve()),"dataset_sha256":sha256(args.dataset),
              "cell_count":len(cells),"selection_file_sha256_before_c89":selection_hash,"selected_context_k":selected_k,
              "c89_opened_once_after_selection":True,"trajectory_count":1,"leave_one_trajectory_out":False,
              "primary_assets":["data_efficiency_matrix.csv","context_length_x_rollout_horizon_heatmap.png",
                                "near_event_rollout_error_growth.png","fem_field_residual_panel_c89.png",
                                "fem_active_support_panel_c89.png","decision.md"]}
    (args.out/"RUN_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--dataset",type=Path,required=True); p.add_argument("--runs",type=Path,required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--device",default="cpu"); main(p.parse_args())
