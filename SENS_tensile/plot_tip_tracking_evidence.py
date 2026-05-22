#!/usr/bin/env python3
"""Plot visual evidence for alpha-based crack-tip tracking.

Overlay on one alpha snapshot:
  - alpha field
  - all candidate nodes used by get_crack_tip: alpha > threshold and x > x_min
  - top-Linf candidate nodes
  - selected tip node
  - previous-cycle tracking/refinement center from x_tip history, when available

This is a diagnostic plot only. It does not change training outputs.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle


def _load_snapshot(archive: Path, cycle: int) -> tuple[Path, np.ndarray]:
    snap = archive / "alpha_snapshots" / f"alpha_cycle_{cycle:04d}.npy"
    if not snap.exists():
        available = sorted((archive / "alpha_snapshots").glob("alpha_cycle_*.npy"))
        hint = ", ".join(p.stem.rsplit("_", 1)[-1] for p in available[:10])
        raise FileNotFoundError(
            f"Missing {snap}. Available first cycles: {hint or 'none'}"
        )
    data = np.load(str(snap))
    if data.ndim != 2 or data.shape[1] < 3:
        raise ValueError(f"{snap} must have columns [x, y, alpha], got {data.shape}")
    return snap, data[:, :3]


def _tip_history_center(archive: Path, cycle: int) -> tuple[float, float] | None:
    """Return the center used at start of `cycle` by S2a if x_tip history exists.

    model_train uses previous-cycle x_tip_history[-1] at the start of cycle j.
    So for cycle 0 the fallback center is (0, 0); for cycle j>0 it is history[j-1].
    """
    for name in ("x_tip_alpha_vs_cycle.npy", "x_tip_vs_cycle.npy"):
        p = archive / "best_models" / name
        if p.exists():
            hist = np.load(str(p)).astype(float).ravel()
            if cycle <= 0:
                return (0.0, 0.0)
            if len(hist) >= cycle:
                return (float(hist[cycle - 1]), 0.0)
            if len(hist) > 0:
                return (float(hist[-1]), 0.0)
    return None


def _compute_candidates(
    data: np.ndarray,
    threshold: float,
    x_min: float,
    mouth_xy: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    x, y, alpha = data[:, 0], data[:, 1], data[:, 2]
    mask = (alpha > threshold) & (x > x_min)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return idx, np.array([], dtype=float), None
    dx = np.abs(x[idx] - mouth_xy[0])
    dy = np.abs(y[idx] - mouth_xy[1])
    linf = np.maximum(dx, dy)
    tip_idx = idx[int(np.argmax(linf))]
    return idx, linf, tip_idx


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path, help="Run archive directory")
    p.add_argument("--cycle", type=int, default=4)
    p.add_argument("--threshold", type=float, default=0.90)
    p.add_argument("--x-min", type=float, default=0.0)
    p.add_argument("--mouth-x", type=float, default=0.0)
    p.add_argument("--mouth-y", type=float, default=0.0)
    p.add_argument("--r-tip", type=float, default=None,
                   help="Draw refinement radius around the previous-cycle center")
    p.add_argument("--center-x", type=float, default=None,
                   help="Override tracking/refinement center x")
    p.add_argument("--center-y", type=float, default=0.0)
    p.add_argument("--top-n", type=int, default=20)
    p.add_argument("--zoom", action="store_true",
                   help="Zoom to crack-tip region instead of full domain")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    archive = args.archive.resolve()
    snap, data = _load_snapshot(archive, args.cycle)
    mouth = (float(args.mouth_x), float(args.mouth_y))
    cand_idx, cand_linf, tip_idx = _compute_candidates(
        data, args.threshold, args.x_min, mouth
    )

    if args.center_x is not None:
        center = (float(args.center_x), float(args.center_y))
    else:
        center = _tip_history_center(archive, args.cycle)

    out = args.out
    if out is None:
        out = archive / "diagnostics" / f"tip_tracking_evidence_cycle_{args.cycle:04d}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    csv_out = out.with_suffix(".csv")

    x, y, alpha = data[:, 0], data[:, 1], data[:, 2]
    fig, ax = plt.subplots(figsize=(7.2, 5.2), constrained_layout=True)
    tpc = ax.tripcolor(x, y, alpha, shading="gouraud", vmin=0.0, vmax=1.0, cmap="plasma")
    cb = fig.colorbar(tpc, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("alpha")

    if cand_idx.size:
        ax.scatter(x[cand_idx], y[cand_idx], s=9, c="#30d5c8", alpha=0.65,
                   linewidths=0, label=f"candidate alpha>{args.threshold:g}, x>{args.x_min:g}")
        top_order = np.argsort(-cand_linf)[: max(1, args.top_n)]
        top_idx = cand_idx[top_order]
        ax.scatter(x[top_idx], y[top_idx], s=34, facecolors="none",
                   edgecolors="white", linewidths=0.9, label=f"top {len(top_idx)} by Linf")
        for rank, idx0 in enumerate(top_idx[:10], start=1):
            ax.text(x[idx0] + 0.004, y[idx0] + 0.004, str(rank),
                    color="white", fontsize=7, weight="bold")

    ax.scatter([mouth[0]], [mouth[1]], s=80, marker="+", c="black",
               linewidths=1.5, label="crack mouth")
    if center is not None:
        ax.scatter([center[0]], [center[1]], s=90, marker="x", c="#49d36b",
                   linewidths=2.0, label="cycle-start tracking center")
        if args.r_tip is not None:
            ax.add_patch(Circle(center, float(args.r_tip), fill=False,
                                ec="#49d36b", lw=1.4, ls="--", alpha=0.95))

    if tip_idx is not None:
        tip_linf = max(abs(x[tip_idx] - mouth[0]), abs(y[tip_idx] - mouth[1]))
        ax.scatter([x[tip_idx]], [y[tip_idx]], s=140, marker="*",
                   c="#ff3b30", edgecolors="black", linewidths=0.5,
                   label=f"selected tip Linf={tip_linf:.4f}")
        text_dx = -0.16 if x[tip_idx] > 0.36 else 0.035
        text_ha = "right" if text_dx < 0 else "left"
        ax.annotate(
            f"selected ({x[tip_idx]:.4f}, {y[tip_idx]:.4f})",
            xy=(x[tip_idx], y[tip_idx]),
            xytext=(x[tip_idx] + text_dx, y[tip_idx] + 0.055),
            arrowprops={"arrowstyle": "->", "color": "#ff3b30", "lw": 1.2},
            fontsize=8,
            color="#ff3b30",
            ha=text_ha,
        )

    archive_label = archive.name if len(archive.name) <= 82 else archive.name[:79] + "..."
    title = f"{archive_label}\ncycle {args.cycle} tip-tracking evidence"
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    if args.zoom:
        xmax = 0.16
        if tip_idx is not None:
            xmax = max(0.16, min(0.55, x[tip_idx] + 0.08))
        if center is not None:
            xmax = max(xmax, min(0.55, center[0] + 0.08))
        ax.set_xlim(-0.05, xmax)
        ax.set_ylim(-0.12, 0.12)
    else:
        ax.set_xlim(-0.52, 0.52)
        ax.set_ylim(-0.52, 0.52)
    ax.legend(loc="upper right", fontsize=7, frameon=True)
    fig.savefig(str(out), dpi=220)
    plt.close(fig)

    rows = []
    if cand_idx.size:
        top_order = np.argsort(-cand_linf)[: max(1, args.top_n)]
        for rank, local_pos in enumerate(top_order, start=1):
            idx0 = int(cand_idx[local_pos])
            rows.append({
                "rank_linf": rank,
                "node_index": idx0,
                "x": float(x[idx0]),
                "y": float(y[idx0]),
                "alpha": float(alpha[idx0]),
                "linf_from_mouth": float(cand_linf[local_pos]),
                "is_selected_tip": bool(tip_idx is not None and idx0 == int(tip_idx)),
            })
    with open(csv_out, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["rank_linf", "node_index", "x", "y", "alpha",
                        "linf_from_mouth", "is_selected_tip"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[saved] {out}")
    print(f"[saved] {csv_out}")
    print(f"[summary] snapshot={snap.name} candidates={cand_idx.size} "
          f"selected_tip={None if tip_idx is None else (float(x[tip_idx]), float(y[tip_idx]))} "
          f"center={center}")


if __name__ == "__main__":
    main()
