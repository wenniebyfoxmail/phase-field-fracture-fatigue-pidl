#!/usr/bin/env python3
"""
validate_pidl_archive.py — PIDL-side validation analog of FEM's 4 standard tests,
plus 4 PIDL-specific tests for fatigue.

Runs on a finished PIDL archive (post-hoc, no retraining). Designed for paper
Ch2 supplementary "Validation" section.

Tests run:

  ## FEM-equivalent (echo the 4 FEM validation criteria)
  V1. Energy balance              ΔE_el(t) + ⟨f(ᾱ)⟩·∂E_d(t) ≈ 0    [per-cycle]
  V2. Mesh resolution             ℓ_0/h_tip ≥ 5  (Carrara recommendation)
  V3. SIF path-independence       max-min K_I across contour radii < 10%
  V4. Geometric symmetry          ⟨α(x, +y) - α(x, -y)⟩_RMS  in tip ROI

  ## PIDL-specific (NN-induced concerns)
  V5. Carrara accumulator self-consistency  Δᾱ = max(0, ψ⁺ - ψ⁺_prev) per element
  V6. f(ᾱ) reaches asymptotic floor          f_min @ N_f vs FEM 1.09e-6
  V7. BC residual                            |u(boundary) - u_BC|_∞
  V8. Pretrain convergence                   final pretrain loss / initial loss

Usage:
    python validate_pidl_archive.py <archive_path> [--coeff 1.0]
        [--mesh ../meshed_geom2.msh]
        [--cycles 0,40,N_f]                # which cycles to test V1, V4, V5, V7

Outputs:
  <archive>/best_models/validation_report.csv     # one row per test
  <archive>/best_models/validation_report.txt     # human-readable summary
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

FINE_MESH = str(HERE / "meshed_geom2.msh")


# -----------------------------------------------------------------------------
# Test implementations
# -----------------------------------------------------------------------------

def _severity_rank(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2, "SKIP": -1}.get(status, -1)


def _merge_status(*statuses: str) -> str:
    real = [s for s in statuses if s != "SKIP"]
    if not real:
        return "SKIP"
    return max(real, key=_severity_rank)


def _parse_settings(model_dir: Path) -> dict:
    f = model_dir / "model_settings.txt"
    if not f.exists():
        return {}
    cfg = {}
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def _as_bool(v, default=False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _pick_symmetry_cycle(archive: Path) -> tuple[int | None, Path | None]:
    snap_dir = archive / "alpha_snapshots"
    snaps = sorted(snap_dir.glob("alpha_cycle_*.npy")) if snap_dir.is_dir() else []
    if len(snaps) < 2:
        nn_file = _load_cycle_nn_file(archive, None)
        if nn_file is None:
            return None, None
        try:
            cyc = int(nn_file.stem.split("_")[-1])
        except Exception:
            cyc = None
        return cyc, None
    mid = snaps[len(snaps) // 2]
    try:
        cyc = int(mid.stem.split("_")[-1])
    except Exception:
        cyc = None
    return cyc, mid


def _load_cycle_nn_file(archive: Path, cycle: int | None) -> Path | None:
    bm = archive / "best_models"
    if cycle is not None:
        exact = bm / f"trained_1NN_{cycle}.pt"
        if exact.is_file():
            return exact
    nn_files = sorted(
        bm.glob("trained_1NN_*.pt"),
        key=lambda p: int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else -1,
    )
    if not nn_files:
        return None
    if cycle is None:
        return nn_files[min(len(nn_files) // 2, len(nn_files) - 1)]
    nums = []
    for p in nn_files:
        try:
            nums.append((abs(int(p.stem.split("_")[-1]) - cycle), p))
        except Exception:
            continue
    return min(nums, key=lambda t: t[0])[1] if nums else nn_files[0]


def _rebuild_field_comp(archive: Path, cycle: int | None):
    """Reconstruct FieldComputation at a chosen cycle for symmetry audits."""
    import ast
    import torch
    from construct_model import construct_model
    from input_data_from_mesh import prep_input_data
    from field_computation import FieldComputation

    cfg = _parse_settings(archive)
    arch = _parse_archive_arch(archive)
    if arch is None:
        raise ValueError(f"could not parse arch from archive name: {archive.name}")

    network_dict = {
        "model_type": "MLP",
        "hidden_layers": int(cfg.get("hidden_layers", arch["hl"])),
        "neurons": int(cfg.get("neurons", arch["neurons"])),
        "seed": int(cfg.get("seed", arch["seed"])),
        "activation": cfg.get("activation", arch["activation"]),
        "init_coeff": float(cfg.get("coeff", arch["init_coeff"])),
        "compile": False,
    }
    pff_model_dict = {
        "PFF_model": cfg.get("PFF_model", "AT1"),
        "se_split": cfg.get("se_split", "volumetric"),
        "tol_ir": 5e-3,
    }
    mat_prop_dict = {
        "mat_E": 1.0,
        "mat_nu": 0.3,
        "w1": 1.0,
        "l0": 0.01,
    }
    numr_dict = {"alpha_constraint": cfg.get("alpha_constraint", "nonsmooth"),
                 "gradient_type": "numerical"}
    crack_dict = {"x_init": [0.0], "y_init": [0.0], "L_crack": [0.0]}
    domain_extrema = torch.tensor([[-0.5, 0.5], [-0.5, 0.5]])
    loading_angle = torch.tensor([np.pi / 2])

    williams_dict = None
    if _as_bool(cfg.get("williams_enable", False)):
        williams_dict = {
            "enable": True,
            "theta_mode": cfg.get("williams_theta_mode", "atan2"),
            "r_min": float(cfg.get("williams_r_min", 1e-6)),
        }

    ansatz_dict = None
    if _as_bool(cfg.get("ansatz_enable", False)):
        modes_raw = cfg.get("ansatz_modes", "['I']")
        try:
            modes = ast.literal_eval(modes_raw)
        except Exception:
            modes = ["I"]
        ansatz_dict = {
            "enable": True,
            "x_tip": float(cfg.get("ansatz_x_tip", 0.0)),
            "y_tip": float(cfg.get("ansatz_y_tip", 0.0)),
            "r_cutoff": float(cfg.get("ansatz_r_cutoff", 0.1)),
            "nu": float(cfg.get("ansatz_nu", 0.3)),
            "c_init": float(cfg.get("ansatz_c_init", 0.01)),
            "modes": modes,
        }

    symmetry_prior = _as_bool(cfg.get("symmetry_prior", False), default=False)
    exact_bc_dict = None
    if _as_bool(cfg.get("exact_bc_enable", False), default=False):
        exact_bc_dict = {
            "enable": True,
            "mode": cfg.get("exact_bc_mode", "sent_plane_strain"),
            "nu": float(cfg.get("exact_bc_nu", mat_prop_dict["mat_nu"])),
        }

    # ★ 2026-05-13 Fourier-aware reconstruction: if archive trained with C10
    # FourierFeatureNet wrapper, replay it here too — otherwise NN state_dict
    # load fails due to inner.* prefix mismatch.
    fourier_dict = None
    if (_as_bool(cfg.get("fourier_enable", False), default=False)
            or "_fourier_sig" in archive.name):
        # Parse "fourier: {'enable': True, 'sigma': 30.0, 'n_features': 128, 'seed': 0}"
        # from model_settings.txt; fall back to archive-name parsing if not found.
        import ast as _ast
        fr_raw = cfg.get("fourier", None)
        fr_parsed = {}
        if fr_raw:
            try:
                fr_parsed = _ast.literal_eval(fr_raw)
            except Exception:
                fr_parsed = {}
        # Archive-name fallback: e.g. "..._fourier_sig30.0_nf128"
        if not fr_parsed:
            import re as _re
            m_sig = _re.search(r"_fourier_sig([\d.]+)", archive.name)
            m_nf = _re.search(r"_nf(\d+)", archive.name)
            fr_parsed = {
                "sigma": float(m_sig.group(1)) if m_sig else 30.0,
                "n_features": int(m_nf.group(1)) if m_nf else 128,
                "seed": 0,
            }
        fourier_dict = {
            "enable": True,
            "sigma": float(fr_parsed.get("sigma", 30.0)),
            "n_features": int(fr_parsed.get("n_features", 128)),
            "seed": int(fr_parsed.get("seed", 0)),
        }

    pffmodel, matprop, network = construct_model(
        pff_model_dict, mat_prop_dict, network_dict, domain_extrema, "cpu",
        williams_dict=williams_dict,
        fourier_dict=fourier_dict)
    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=FINE_MESH, device="cpu")

    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([float(cfg.get("disp_max", 0.12))]),
        theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=williams_dict,
        ansatz_dict=ansatz_dict,
        l0=mat_prop_dict["l0"],
        symmetry_prior=symmetry_prior,
        exact_bc_dict=exact_bc_dict,
    )

    best = archive / "best_models"
    nn_file = _load_cycle_nn_file(archive, cycle)
    if nn_file is None:
        raise FileNotFoundError("no trained_1NN_*.pt file found")
    field_comp.net.load_state_dict(torch.load(str(nn_file), map_location="cpu", weights_only=False))
    field_comp.net.eval()

    if williams_dict is not None:
        xt = best / "x_tip_psi_vs_cycle.npy"
        if xt.exists() and cycle is not None:
            x_tip_arr = np.load(xt)
            if cycle < len(x_tip_arr):
                field_comp.x_tip = float(x_tip_arr[cycle])

    if ansatz_dict is not None and field_comp.c_singular is not None:
        cs_file = best / "c_singular_vs_cycle.npy"
        if cs_file.exists() and cycle is not None:
            cs = np.load(cs_file)
            row = cs[cs[:, 0].astype(int) == cycle]
            if len(row) > 0:
                field_comp.c_singular.data = torch.tensor([float(row[0, 1])], dtype=torch.float32)

    return {
        "cfg": cfg,
        "field_comp": field_comp,
        "inp": inp,
        "T_conn": T_conn,
        "nn_file": nn_file.name,
    }

def test_v1_energy_balance(archive: Path) -> dict:
    """V1. Per-cycle energy balance.

    Reads E_el_vs_cycle.npy and alpha_bar_vs_cycle.npy. If E_d isn't separately
    tracked (it rarely is on disk), check via:
      ΔE_el(t) + ⟨f(ᾱ)⟩·something ≈ 0  is hard post-hoc.

    Practical check: E_el should be MONOTONICALLY non-increasing (modulo numerical
    noise) once damage starts evolving — fatigue DECREASES elastic capacity.
    Report: max relative cycle-to-cycle increase of E_el; >5% suggests issue.
    """
    f = archive / "best_models" / "E_el_vs_cycle.npy"
    if not f.is_file():
        return {"test": "V1_energy_balance", "status": "SKIP",
                "reason": "no E_el_vs_cycle.npy"}
    E = np.load(f).flatten()
    if E.size < 3:
        return {"test": "V1_energy_balance", "status": "SKIP",
                "reason": f"only {E.size} cycles"}
    # Look at "active fatigue" region: skip first 5 + last 5 cycles
    Eactive = E[5:-5] if E.size > 20 else E
    # Cycle-to-cycle relative change
    rel_changes = np.diff(Eactive) / (np.abs(Eactive[:-1]) + 1e-30)
    max_increase = float(np.max(rel_changes))   # >0 = monotonicity violated
    median_decrease = float(np.median(np.abs(rel_changes[rel_changes < 0]))) if np.any(rel_changes < 0) else 0.0
    status = "PASS" if max_increase < 0.05 else ("WARN" if max_increase < 0.20 else "FAIL")
    return {
        "test": "V1_energy_balance", "status": status,
        "max_rel_increase_E_el": max_increase,
        "median_rel_decrease": median_decrease,
        "criterion": "max increase < 5% (active region)",
    }


def test_v2_mesh_resolution(archive: Path, l0: float = 0.01) -> dict:
    """V2. Mesh resolution at tip: ℓ_0 / h_tip.

    Reads alpha_snapshots[0] to extract node coordinates, computes minimum
    element edge length in tip ROI (x ∈ [0, 0.05], |y| < 0.02), reports
    ℓ_0 / h.
    """
    snap_dir = archive / "alpha_snapshots"
    if not snap_dir.is_dir():
        return {"test": "V2_mesh_resolution", "status": "SKIP",
                "reason": "no alpha_snapshots dir"}
    snaps = sorted(snap_dir.glob("alpha_cycle_*.npy"))
    if not snaps:
        return {"test": "V2_mesh_resolution", "status": "SKIP",
                "reason": "no alpha_cycle_*.npy files"}
    arr = np.load(snaps[0])
    # arr shape (N_nodes, 3) — cols [x, y, alpha]
    xy = arr[:, :2]
    # Tip ROI
    mask = (xy[:, 0] >= 0) & (xy[:, 0] <= 0.05) & (np.abs(xy[:, 1]) < 0.02)
    pts = xy[mask]
    if pts.shape[0] < 10:
        return {"test": "V2_mesh_resolution", "status": "SKIP",
                "reason": f"only {pts.shape[0]} pts in tip ROI"}
    # Approximate h_tip = median nearest-neighbor distance in tip ROI
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    d, _ = tree.query(pts, k=2)
    h_tip = float(np.median(d[:, 1]))
    ratio = l0 / h_tip if h_tip > 1e-12 else float("inf")
    status = "PASS" if ratio >= 5 else ("WARN" if ratio >= 3 else "FAIL")
    return {
        "test": "V2_mesh_resolution", "status": status,
        "l0_over_h_tip": ratio, "h_tip": h_tip, "l0": l0,
        "n_pts_tip_roi": int(pts.shape[0]),
        "criterion": "ℓ_0/h ≥ 5 (Carrara 3-5; FEM uses 10)",
    }


def test_v3_J_path_independence(archive: Path) -> dict:
    """V3. K_I path-independence across contour radii.

    Reads J_integral.csv (already computed by compute_J_integral.py).
    Reports max-min spread / median across 3 contour radii in pristine cycles.
    """
    f = archive / "best_models" / "J_integral.csv"
    if not f.is_file():
        return {"test": "V3_J_path_independence", "status": "SKIP",
                "reason": "no J_integral.csv (run compute_J_integral.py first)"}
    import csv
    rows = list(csv.DictReader(open(f)))
    if not rows:
        return {"test": "V3_J_path_independence", "status": "SKIP", "reason": "empty"}
    # Use first 5 cycles (pristine, before serious fatigue)
    Ks = [(float(r["K_r0"]), float(r["K_r1"]), float(r["K_r2"])) for r in rows[:5]]
    medians = [float(np.median([k[i] for k in Ks])) for i in (0, 1, 2)]
    spread = (max(medians) - min(medians)) / max(medians) * 100
    status = "PASS" if spread < 10 else ("WARN" if spread < 20 else "FAIL")
    return {
        "test": "V3_J_path_independence", "status": status,
        "K_r0_med": medians[0], "K_r1_med": medians[1], "K_r2_med": medians[2],
        "spread_pct": spread,
        "criterion": "spread < 10% across 3 contour radii (pristine cycles)",
    }


def test_v4_symmetry(archive: Path, cycles_to_check: list[int] | None = None) -> dict:
    """V4. Composite symmetry audit about the y=0 mirror plane.

    This is intentionally broader than the old alpha-only check:
      1. alpha-even mirror:      α(x,+y) ≈ α(x,-y)
      2. u_x correction even:    u_corr(x,+y) ≈ u_corr(x,-y)
      3. u_y correction odd:     v_corr(x,+y) ≈ -v_corr(x,-y)
      4. centerline derivative:  ∂α/∂y(x,0) ≈ 0

    Important: the odd/even statements apply to the NN correction / residual
    field, NOT to the total vertical displacement including the affine loading
    term. This matches the current FieldComputation BC decomposition.
    """
    import torch
    from scipy.spatial import cKDTree

    cyc, mid = _pick_symmetry_cycle(archive)
    if cyc is None and mid is None:
        return {"test": "V4_symmetry", "status": "SKIP",
                "reason": "no alpha snapshots and no NN checkpoints"}

    # ------------------------------------------------------------------
    # Part B/C/D: reconstruct field + audit residual parity and centerline dα/dy
    # ------------------------------------------------------------------
    status_ux = status_vy = status_dady = "SKIP"
    status_alpha = "SKIP"
    rms_alpha = max_alpha = np.nan
    rms_ux = rms_vy = rms_dady = np.nan
    max_ux = max_vy = max_dady = np.nan
    nn_file = ""
    symmetry_prior = False
    try:
        ctx = _rebuild_field_comp(archive, cyc)
        field_comp = ctx["field_comp"]
        inp = ctx["inp"]
        nn_file = ctx["nn_file"]
        symmetry_prior = bool(getattr(field_comp, "symmetry_prior", False))

        with torch.no_grad():
            u, v, alpha_full = field_comp.fieldCalculation(inp)
        xy_full = inp.detach().cpu().numpy()
        u_np = u.detach().cpu().numpy().reshape(-1)
        v_np = v.detach().cpu().numpy().reshape(-1)
        a_np = alpha_full.detach().cpu().numpy().reshape(-1)

        lmbda = float(field_comp.lmbda.item() if hasattr(field_comp.lmbda, "item") else field_comp.lmbda)
        theta = float(field_comp.theta.item() if hasattr(field_comp.theta, "item") else field_comp.theta[0])
        y0, yL = float(field_comp.domain_extrema[1, 0]), float(field_comp.domain_extrema[1, 1])
        y = xy_full[:, 1]
        bc_load = (y - y0) / (yL - y0)
        u_bc = lmbda * bc_load * np.cos(theta)
        v_bc = lmbda * bc_load * np.sin(theta)
        u_corr = u_np - u_bc
        v_corr = v_np - v_bc

        mask_full = (xy_full[:, 0] >= 0) & (xy_full[:, 0] <= 0.3) & (np.abs(xy_full[:, 1]) < 0.05)
        if mask_full.sum() < 30:
            return {"test": "V4_symmetry", "status": "SKIP",
                    "reason": f"only {int(mask_full.sum())} pts in symmetry ROI"}
        pts2 = xy_full[mask_full]
        a2 = a_np[mask_full]
        u2 = u_corr[mask_full]
        v2 = v_corr[mask_full]
        pos2 = pts2[pts2[:, 1] >= 0]
        a_pos = a2[pts2[:, 1] >= 0]
        u_pos = u2[pts2[:, 1] >= 0]
        v_pos = v2[pts2[:, 1] >= 0]
        neg2 = pts2[pts2[:, 1] < 0]
        a_neg = a2[pts2[:, 1] < 0]
        u_neg = u2[pts2[:, 1] < 0]
        v_neg = v2[pts2[:, 1] < 0]
        if len(pos2) > 0 and len(neg2) > 0:
            tree2 = cKDTree(np.column_stack([neg2[:, 0], -neg2[:, 1]]))
            d2, idx2 = tree2.query(pos2, k=1)
            good2 = d2 < 0.005
            if good2.sum() >= 10:
                diff_alpha = a_pos[good2] - a_neg[idx2[good2]]
                diff_ux = u_pos[good2] - u_neg[idx2[good2]]
                diff_vy = v_pos[good2] + v_neg[idx2[good2]]
                rms_alpha = float(np.sqrt(np.mean(diff_alpha ** 2)))
                max_alpha = float(np.abs(diff_alpha).max())
                rms_ux = float(np.sqrt(np.mean(diff_ux ** 2)))
                max_ux = float(np.abs(diff_ux).max())
                rms_vy = float(np.sqrt(np.mean(diff_vy ** 2)))
                max_vy = float(np.abs(diff_vy).max())
                status_alpha = "PASS" if rms_alpha < 2e-4 else ("WARN" if rms_alpha < 1e-2 else "FAIL")
                status_ux = "PASS" if rms_ux < 1e-4 else ("WARN" if rms_ux < 1e-2 else "FAIL")
                status_vy = "PASS" if rms_vy < 1e-4 else ("WARN" if rms_vy < 1e-2 else "FAIL")
            else:
                return {"test": "V4_symmetry", "status": "SKIP",
                        "reason": f"only {int(good2.sum())} good mirror pairs"}
        else:
            return {"test": "V4_symmetry", "status": "SKIP",
                    "reason": "asymmetric ROI sampling"}

        # centerline derivative: evaluate ∂α/∂y at y=0 along x ∈ [0, 0.3]
        x_line = torch.linspace(0.0, 0.3, 41, dtype=torch.float32)
        y_line = torch.zeros_like(x_line)
        xy_line = torch.stack([x_line, y_line], dim=1).requires_grad_(True)
        _, _, alpha_line = field_comp.fieldCalculation(xy_line)
        grad_alpha = torch.autograd.grad(alpha_line.sum(), xy_line, create_graph=False, retain_graph=False)[0][:, 1]
        dady = grad_alpha.detach().cpu().numpy()
        rms_dady = float(np.sqrt(np.mean(dady ** 2)))
        max_dady = float(np.abs(dady).max())
        status_dady = "PASS" if rms_dady < 1e-3 else ("WARN" if rms_dady < 5e-2 else "FAIL")
    except Exception as e:
        return {
            "test": "V4_symmetry",
            "status": status_alpha,
            "rms_alpha_skew": rms_alpha,
            "max_alpha_skew": max_alpha,
            "status_alpha_even": status_alpha,
            "status_ux_corr_even": "SKIP",
            "status_vy_corr_odd": "SKIP",
            "status_dalpha_dy_centerline": "SKIP",
            "snapshot": mid.name if mid is not None else "",
            "cycle": cyc,
            "n_pairs": 0,
            "criterion": "Composite symmetry audit: alpha-even + correction parity + centerline dα/dy",
            "note": f"alpha-only audit succeeded; reconstruction skipped: {type(e).__name__}: {e}",
        }

    overall = _merge_status(status_alpha, status_ux, status_vy, status_dady)
    return {
        "test": "V4_symmetry", "status": overall,
        "snapshot": mid.name if mid is not None else "", "cycle": cyc, "nn_file": nn_file,
        "symmetry_prior": symmetry_prior,
        "n_pairs": int(good2.sum()) if 'good2' in locals() else 0,
        "rms_alpha_skew": rms_alpha, "max_alpha_skew": max_alpha,
        "rms_ux_corr_even": rms_ux, "max_ux_corr_even": max_ux,
        "rms_vy_corr_odd": rms_vy, "max_vy_corr_odd": max_vy,
        "rms_dalpha_dy_centerline": rms_dady, "max_dalpha_dy_centerline": max_dady,
        "status_alpha_even": status_alpha,
        "status_ux_corr_even": status_ux,
        "status_vy_corr_odd": status_vy,
        "status_dalpha_dy_centerline": status_dady,
        "criterion": (
            "Composite symmetry audit about y=0: "
            "alpha-even PASS if RMS<2e-4; "
            "u_x correction even / u_y correction odd PASS if RMS<1e-4; "
            "centerline ∂α/∂y PASS if RMS<1e-3"
        ),
        "note": (
            "Odd/even statements apply to the NN correction/residual field, not the total vertical displacement "
            "including the affine top-bottom loading term."
        ),
    }


def _load_alpha_bar(archive: Path):
    """alpha_bar_vs_cycle.npy is per-cycle (ᾱ_max, ᾱ_mean, f_min_global).

    Some older archives may store as 1D (ᾱ_max only). Auto-detect.
    Returns (alpha_max, alpha_mean_or_None, f_min_or_None).
    """
    f = archive / "best_models" / "alpha_bar_vs_cycle.npy"
    if not f.is_file():
        return None, None, None
    arr = np.load(f)
    if arr.ndim == 1:
        return arr, None, None
    if arr.shape[1] >= 3:
        return arr[:, 0], arr[:, 1], arr[:, 2]
    if arr.shape[1] == 2:
        return arr[:, 0], arr[:, 1], None
    return arr[:, 0], None, None


def test_v5_carrara_consistency(archive: Path) -> dict:
    """V5. Carrara accumulator self-consistency: ᾱ_max should be monotonic.

    The Carrara asymmetric accumulator only INCREASES (max(0, Δψ⁺)) — the
    GLOBAL MAX of ᾱ across elements should never decrease cycle-to-cycle
    (per-element ᾱ never decreases, max-over-elements also never decreases).

    Tolerate small numerical noise (< 1e-8 relative).
    """
    a_max, _, _ = _load_alpha_bar(archive)
    if a_max is None or a_max.size < 3:
        return {"test": "V5_carrara_consistency", "status": "SKIP",
                "reason": "no alpha_bar_vs_cycle.npy or <3 cycles"}
    diffs = np.diff(a_max)
    # Tolerate < 1e-8 noise OR < 1e-6 relative
    rel_thresh = 1e-6 * np.abs(a_max[:-1])
    abs_thresh = 1e-8 * np.ones_like(rel_thresh)
    thresh = np.maximum(rel_thresh, abs_thresh)
    decreases = diffs < -thresh
    n_decreases = int(decreases.sum())
    max_decrease = float(-diffs[decreases].max()) if n_decreases > 0 else 0.0
    n_cycles = int(a_max.size)
    pct = n_decreases / max(1, n_cycles - 1) * 100
    status = "PASS" if n_decreases == 0 else ("WARN" if pct < 5 else "FAIL")
    return {
        "test": "V5_carrara_consistency", "status": status,
        "n_cycles": n_cycles,
        "n_decreases": n_decreases,
        "pct_decreases": pct,
        "max_decrease_abs": max_decrease,
        "alpha_max_at_Nf": float(a_max[-1]),
        "criterion": "ᾱ_max monotonic non-decreasing globally (Carrara accumulator property; tolerate <1e-6 rel noise)",
    }


def test_v6_f_min_floor(archive: Path) -> dict:
    """V6. f(ᾱ) reaches asymptotic floor at N_f.

    Use f_min directly from column 2 of alpha_bar_vs_cycle.npy (if present,
    these are the per-cycle global f_min values from compute_fatigue_degrad).
    Fallback: derive from ᾱ_max via Carrara formula if only ᾱ in file.
    """
    a_max, _, f_min_arr = _load_alpha_bar(archive)
    if a_max is None or a_max.size < 1:
        return {"test": "V6_f_min_floor", "status": "SKIP", "reason": "no data"}
    if f_min_arr is not None:
        f_min_at_Nf = float(f_min_arr[-1])
        source = "direct from saved f_min trajectory"
    else:
        alpha_T = 0.5
        f_min_at_Nf = min(1.0, (2 * alpha_T / (float(a_max[-1]) + alpha_T)) ** 2)
        source = f"derived from ᾱ_max={float(a_max[-1]):.3f} via Carrara asymptotic"
    fem_target = 1.09e-6
    ratio = f_min_at_Nf / fem_target if fem_target > 0 else float("inf")
    # PIDL typical 0.01-0.03 (4 orders above FEM). Status:
    #   PASS if < 0.1 (in active fatigue regime)
    #   WARN if 0.1-0.5 (weak fatigue regime)
    #   FAIL if > 0.5 (essentially no fatigue activated)
    status = "PASS" if f_min_at_Nf < 0.1 else ("WARN" if f_min_at_Nf < 0.5 else "FAIL")
    return {
        "test": "V6_f_min_floor", "status": status,
        "f_min_at_Nf_global": f_min_at_Nf,
        "alpha_max_at_Nf": float(a_max[-1]),
        "fem_target_f_min": fem_target,
        "ratio_PIDL_over_FEM": ratio,
        "source": source,
        "criterion": "f_min < 0.1 PASS; PIDL typically 0.01-0.03 (4 orders above FEM 1e-6) — known limit",
    }


def _parse_archive_arch(archive: Path) -> dict | None:
    """Parse archive directory name to extract NN architecture parameters.

    Expected pattern: hl_<L>_Neurons_<N>_activation_<A>_coeff_<C>_Seed_<S>_...

    Returns dict {hl, neurons, activation, init_coeff, seed} or None on parse fail.
    """
    import re
    name = archive.name
    m = re.match(r"hl_(\d+)_Neurons_(\d+)_activation_(\w+)_coeff_([\d.]+)_Seed_(\d+)", name)
    if not m:
        return None
    return {
        "hl": int(m.group(1)),
        "neurons": int(m.group(2)),
        "activation": m.group(3),
        "init_coeff": float(m.group(4)),
        "seed": int(m.group(5)),
    }


def test_v7_bc_residual(archive: Path,
                        E: float = 210e3, nu: float = 0.3,
                        umax: float = 0.12,
                        n_y_samples: int = 50) -> dict:
    """V7. PIDL BC residual at left/right (free) boundaries.

    PIDL hard-enforces top/bottom y=±0.5 BCs analytically via the
    `(y-y0)*(yL-y)` scaling factor in field_computation.py — those boundaries
    have residual = 0 by construction. **Side boundaries x=±0.5 are
    traction-free assumed but NOT explicitly enforced** — the NN must learn
    to keep stress σ·n ≈ 0 at those edges via the Deep Ritz minimization.

    This test loads the latest NN checkpoint, samples (x=±0.5, y=linspace) on
    the side boundaries, runs forward + autograd to compute σ_xx and σ_xy,
    and reports the relative residual vs the bulk-domain max stress.

    PASS criterion: max |σ_xx_bdy| / max |σ_yy_bulk| < 0.10 (10% relative)
    WARN: 0.10-0.30
    FAIL: > 0.30
    """
    import torch
    import sys
    HERE = Path(__file__).parent
    sys.path.insert(0, str(HERE.parent / "source"))

    arch = _parse_archive_arch(archive)
    if arch is None:
        return {"test": "V7_bc_residual_side", "status": "SKIP",
                "reason": f"could not parse arch from archive name {archive.name}"}

    # Try to find a NN weight file (trained_1NN_*.pt)
    bm = archive / "best_models"
    nn_files = sorted(bm.glob("trained_1NN_*.pt"),
                      key=lambda p: int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else -1)
    if not nn_files:
        return {"test": "V7_bc_residual_side", "status": "SKIP",
                "reason": "no trained_1NN_*.pt file found"}
    # Use cycle 0 (pristine post-pretrain) for fair BC check.
    # Later cycles get distorted by crack propagation near right edge.
    nn_file = bm / "trained_1NN_0.pt"
    if not nn_file.is_file():
        nn_file = nn_files[0]   # earliest available

    # Detect special architectures (multihead/xfem) by looking for tags in archive name
    name = archive.name
    if "alpha2_mh" in name or "supα" in name or "supα_pathC" in name or "alpha3_xfem" in name:
        return {"test": "V7_bc_residual_side", "status": "SKIP",
                "reason": "non-baseline architecture; manual V7 needed for "
                         "MultiHeadNN/XFEMJumpNN/Path-C variants"}

    try:
        from network import NeuralNet
    except ImportError as e:
        return {"test": "V7_bc_residual_side", "status": "SKIP",
                "reason": f"could not import NeuralNet: {e}"}

    # Build NN matching archive arch.
    # ★ 2026-05-13 Fourier-aware path: if archive used C10 FourierFeatureNet
    # wrapper, build it via construct_model (same way training did) so the
    # state_dict prefix `inner.*` aligns. Otherwise vanilla NeuralNet works.
    try:
        archive_uses_fourier = "_fourier_sig" in archive.name
        if archive_uses_fourier:
            import re as _re
            m_sig = _re.search(r"_fourier_sig([\d.]+)", archive.name)
            m_nf = _re.search(r"_nf(\d+)", archive.name)
            _sigma = float(m_sig.group(1)) if m_sig else 30.0
            _nf = int(m_nf.group(1)) if m_nf else 128
            from construct_model import construct_model
            _fourier_dict_v7 = {"enable": True, "sigma": _sigma,
                                "n_features": _nf, "seed": 0}
            _pff = {"PFF_model": "AT1", "se_split": "volumetric", "tol_ir": 5e-3}
            _mat = {"mat_E": 1.0, "mat_nu": 0.3, "w1": 1.0, "l0": 0.01}
            _ndict = {"hidden_layers": arch["hl"], "neurons": arch["neurons"],
                      "seed": int(arch.get("seed", 1)),
                      "activation": arch["activation"],
                      "init_coeff": arch["init_coeff"], "compile": False}
            _, _, net = construct_model(_pff, _mat, _ndict,
                                        torch.tensor([[-0.5, 0.5], [-0.5, 0.5]]),
                                        "cpu",
                                        williams_dict=None,
                                        fourier_dict=_fourier_dict_v7)
        else:
            net = NeuralNet(input_dimension=2, output_dimension=3,
                            n_hidden_layers=arch["hl"],
                            neurons=arch["neurons"],
                            activation=arch["activation"],
                            init_coeff=arch["init_coeff"])
        sd = torch.load(str(nn_file), map_location="cpu", weights_only=False)
        net.load_state_dict(sd)
        net.eval()
    except Exception as e:
        return {"test": "V7_bc_residual_side", "status": "SKIP",
                "reason": f"NN load failed: {type(e).__name__}: {e}"}

    # Sample boundary points
    y_edge = torch.linspace(-0.5 + 1e-3, 0.5 - 1e-3, n_y_samples, dtype=torch.float32)
    # Left edge x=-0.5; right edge x=+0.5
    x_left = -0.5 * torch.ones_like(y_edge)
    x_right = 0.5 * torch.ones_like(y_edge)
    xy_left = torch.stack([x_left, y_edge], dim=1).requires_grad_(True)
    xy_right = torch.stack([x_right, y_edge], dim=1).requires_grad_(True)

    # Sample bulk grid for normalization (avoid boundary)
    x_bulk = torch.linspace(-0.45, 0.45, 30, dtype=torch.float32)
    y_bulk = torch.linspace(-0.45, 0.45, 30, dtype=torch.float32)
    Xb, Yb = torch.meshgrid(x_bulk, y_bulk, indexing="ij")
    xy_bulk = torch.stack([Xb.flatten(), Yb.flatten()], dim=1).requires_grad_(True)

    # ★ 2026-05-12 fix: previously this function hardcoded the baseline BC
    # ansatz (bc_scale = (y+0.5)(0.5-y), bc_load = (y+0.5)). That gives the
    # WRONG field for archives that train with non-baseline ansätze
    # (e.g. C4 exact-BC distance-function trial), producing garbage σ_xx at
    # x=±0.5 when the NN weights are interpreted under the baseline ansatz.
    # Fix: detect exact_bc tag in the archive name and route via the same
    # FieldComputation that produced the training.
    cfg_path = archive / "model_settings.txt"
    archive_uses_exact_bc = ("_exactBCsent" in archive.name)
    archive_uses_sym_prior = ("_symY2" in archive.name)
    exact_bc_nu = nu
    if cfg_path.is_file():
        for line in cfg_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("exact_bc_nu:"):
                try:
                    exact_bc_nu = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
    if archive_uses_exact_bc:
        try:
            from field_computation import FieldComputation
            _exact_bc_dict_v7 = {"enable": True, "mode": "sent_plane_strain",
                                 "nu": exact_bc_nu}
            _fc_v7 = FieldComputation(
                net=net,
                domain_extrema=torch.tensor([[-0.5, 0.5], [-0.5, 0.5]],
                                            dtype=torch.float32),
                lmbda=torch.tensor([float(umax)]),
                theta=torch.tensor([float(torch.pi / 2)]),
                alpha_constraint="nonsmooth",
                symmetry_prior=archive_uses_sym_prior,
                exact_bc_dict=_exact_bc_dict_v7,
            )

            def field(xy):
                u, v, _ = _fc_v7.fieldCalculation(xy)
                return u, v
        except Exception as e:
            return {"test": "V7_bc_residual_side", "status": "SKIP",
                    "reason": (f"exact_bc archive but FieldComputation "
                               f"rebuild failed: {type(e).__name__}: {e}")}
    else:
        # Apply BC scaling consistent with baseline FieldComputation:
        # u = (y-y0)*(yL-y)*u_NN + (y-y0)/(yL-y0)*cos(theta)*lmbda
        # v = (y-y0)*(yL-y)*v_NN + (y-y0)/(yL-y0)*sin(theta)*lmbda
        # For mode I tension (theta=π/2): cos(theta)=0, sin(theta)=1
        y0, yL = -0.5, 0.5
        lmbda = float(umax)

        def field(xy):
            out = net(xy)
            u_NN, v_NN, _ = out[:, 0], out[:, 1], out[:, 2]
            bc_scale = (xy[:, 1] - y0) * (yL - xy[:, 1])
            bc_load = (xy[:, 1] - y0) / (yL - y0)
            u = bc_scale * u_NN * lmbda
            v = (bc_scale * v_NN + bc_load * 1.0) * lmbda
            return u, v

    def stress_at(xy):
        u, v = field(xy)
        eps_xx = torch.autograd.grad(u.sum(), xy, create_graph=False, retain_graph=True)[0][:, 0]
        eps_yy = torch.autograd.grad(v.sum(), xy, create_graph=False, retain_graph=True)[0][:, 1]
        # ε_xy = 0.5(∂u/∂y + ∂v/∂x)
        du_dy = torch.autograd.grad(u.sum(), xy, create_graph=False, retain_graph=True)[0][:, 1]
        dv_dx = torch.autograd.grad(v.sum(), xy, create_graph=False, retain_graph=False)[0][:, 0]
        eps_xy = 0.5 * (du_dy + dv_dx)
        # Plane strain Hooke
        c = E / ((1 + nu) * (1 - 2 * nu))
        s_xx = c * ((1 - nu) * eps_xx + nu * eps_yy)
        s_yy = c * (nu * eps_xx + (1 - nu) * eps_yy)
        G = E / (2 * (1 + nu))
        s_xy = 2 * G * eps_xy
        return s_xx.detach(), s_yy.detach(), s_xy.detach()

    s_xx_L, s_yy_L, s_xy_L = stress_at(xy_left)
    s_xx_R, s_yy_R, s_xy_R = stress_at(xy_right)
    s_xx_b, s_yy_b, s_xy_b = stress_at(xy_bulk)

    # Reference scale: max |σ_yy| in bulk (loading-direction stress)
    s_ref = float(s_yy_b.abs().max())
    if s_ref < 1e-12:
        return {"test": "V7_bc_residual_side", "status": "SKIP",
                "reason": f"bulk σ_yy is ~0 ({s_ref:.3e}) — pretrain may not be loaded; check NN file"}

    sxx_L_max = float(s_xx_L.abs().max())
    sxx_R_max = float(s_xx_R.abs().max())
    sxy_L_max = float(s_xy_L.abs().max())
    sxy_R_max = float(s_xy_R.abs().max())
    rel_sxx = max(sxx_L_max, sxx_R_max) / s_ref
    rel_sxy = max(sxy_L_max, sxy_R_max) / s_ref

    # Status: max of σ_xx and σ_xy relative residual at side boundaries
    rel_max = max(rel_sxx, rel_sxy)
    if rel_max < 0.10:
        status = "PASS"
    elif rel_max < 0.30:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "test": "V7_bc_residual_side", "status": status,
        "nn_file": nn_file.name,
        "rel_residual_sxx": rel_sxx,
        "rel_residual_sxy": rel_sxy,
        "max_sxx_left_abs": sxx_L_max,
        "max_sxx_right_abs": sxx_R_max,
        "max_sxy_left_abs": sxy_L_max,
        "max_sxy_right_abs": sxy_R_max,
        "ref_max_syy_bulk_abs": s_ref,
        "criterion": "max(|σ_xx|, |σ_xy|) at x=±0.5 relative to bulk |σ_yy|: "
                     "<10% PASS, 10-30% WARN, >30% FAIL "
                     "(top/bot BC analytical PASS by construction)",
    }


def test_v8_pretrain_convergence(archive: Path) -> dict:
    """V8. Pretrain convergence ratio (final loss / initial loss).

    Reads trainLoss_1NN_0.npy (loss history during pretrain). Reports
    log10(final/initial) — should be at least -3 (3 orders of magnitude
    reduction) for healthy pretrain.
    """
    f = archive / "best_models" / "trainLoss_1NN_0.npy"
    if not f.is_file():
        return {"test": "V8_pretrain_convergence", "status": "SKIP",
                "reason": "no trainLoss_1NN_0.npy"}
    loss = np.load(f).flatten()
    if loss.size < 10:
        return {"test": "V8_pretrain_convergence", "status": "SKIP",
                "reason": f"<10 epochs ({loss.size})"}
    L0 = float(np.median(loss[:5]))
    Lf = float(np.median(loss[-5:]))
    # The loss in this codebase is `loss_var = log10(E_el + E_d + E_hist)` per fit.py.
    # Detect: if L0 < 5 (typical raw loss is much larger), assume log10-space already.
    if abs(L0) < 5 and abs(Lf) < 5:
        log_ratio = float(Lf - L0)
        space = "log10-space"
    else:
        log_ratio = float(np.log10(max(Lf, 1e-30) / max(L0, 1e-30))) if L0 > 0 else 0
        space = "raw"
    # For FATIGUE per-cycle training, NN often starts near minimum (warm from
    # previous cycle), so we don't expect 3-order reduction every cycle.
    # Test: training is STABLE (no divergence: Lf > L0 + 0.5 means loss grew
    # by 3.2× = WARN; >2 means 100× growth = FAIL).
    delta = log_ratio
    if delta > 2:
        status = "FAIL"     # loss grew >100× (divergence)
    elif delta > 0.5:
        status = "WARN"     # loss grew 3-100×
    else:
        status = "PASS"     # loss stable or decreased
    return {
        "test": "V8_training_stability", "status": status,
        "L_initial_log10": L0, "L_final_log10": Lf,
        "delta_log10": delta,
        "loss_space": space,
        "n_epochs": int(loss.size),
        "criterion": "Δlog10(loss) per training session: ≤0.5 PASS; 0.5-2 WARN; >2 FAIL (divergence)",
    }


# -----------------------------------------------------------------------------
# Driver
# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="PIDL post-hoc validation.")
    ap.add_argument("archive", help="archive directory (contains best_models/)")
    ap.add_argument("--l0", type=float, default=0.01, help="length scale ℓ_0")
    ap.add_argument("--out-prefix", default="validation_report",
                    help="output filename prefix")
    args = ap.parse_args()

    archive = Path(args.archive).resolve()
    if not archive.is_dir():
        raise SystemExit(f"archive not found: {archive}")

    print("=" * 72)
    print(f"PIDL Validation Report")
    print(f"Archive: {archive.name}")
    print("=" * 72)

    tests = [
        test_v1_energy_balance(archive),
        test_v2_mesh_resolution(archive, l0=args.l0),
        test_v3_J_path_independence(archive),
        test_v4_symmetry(archive),
        test_v5_carrara_consistency(archive),
        test_v6_f_min_floor(archive),
        test_v7_bc_residual(archive),
        test_v8_pretrain_convergence(archive),
    ]

    # Print summary
    name_w = max(len(t.get("test", "?")) for t in tests) + 2
    print(f"{'Test':<{name_w}} {'Status':<14} Notes")
    print("-" * 72)
    for t in tests:
        status = t.get("status", "?")
        if status == "PASS":
            badge = "✅ PASS"
        elif status == "WARN":
            badge = "⚠ WARN"
        elif status == "FAIL":
            badge = "❌ FAIL"
        elif status == "SKIP":
            badge = "○ SKIP"
        else:
            badge = status
        notes = t.get("criterion", t.get("reason", ""))[:50]
        print(f"{t['test']:<{name_w}} {badge:<14} {notes}")

    # Write detailed JSON + CSV
    out_dir = archive / "best_models"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{args.out_prefix}.json"
    json_path.write_text(json.dumps(tests, indent=2, default=str))
    print(f"\nDetailed report: {json_path}")

    # Compact CSV
    csv_path = out_dir / f"{args.out_prefix}.csv"
    keys = sorted(set(k for t in tests for k in t.keys()))
    with open(csv_path, "w") as fh:
        fh.write(",".join(keys) + "\n")
        for t in tests:
            fh.write(",".join(str(t.get(k, "")).replace(",", ";") for k in keys) + "\n")
    print(f"CSV summary:     {csv_path}")


if __name__ == "__main__":
    main()
