#!/usr/bin/env python3
"""
audit_active_driver_definitions.py — Apr 28 audit Hit 14

The Mac MIT-4 reframe + Dir 6.3 framework table identifies the "active
fatigue driver" element via max g·ψ⁺_raw at α ∈ [0.5, 0.95]. Auditor Hit 14:
this definition is fragile. Compare three driver definitions on one
archive (baseline coeff=1.0 Umax=0.12 c50, the canonical MIT-4 cycle):

  D1: max g(α)·ψ⁺_raw      restricted to α ∈ [0.5, 0.95]   (current MIT-4 def)
  D2: max Δᾱ-per-cycle     full domain (Carrara accumulator increment)
  D3: max ψ⁺_raw·H(Δψ⁺)    full domain (loading-step Heaviside-gated peak)

For each definition: report the chosen element's index, position, α, ᾱ,
ψ⁺_raw, g·ψ⁺, Δᾱ. If D1, D2, D3 pick different elements → claim is fragile.
If they coincide → claim is robust.

Also vary the α window for D1: [0.3, 0.5], [0.5, 0.7], [0.5, 0.95] to
quantify sensitivity.

Output: console table + saves audit_active_driver_results.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

# config.py reads sys.argv; pass dummy
_saved = sys.argv
sys.argv = ["active_driver_audit", "8", "400", "1", "TrainableReLU", "1.0"]
from config import (domain_extrema, loading_angle, network_dict, mat_prop_dict,
                    numr_dict, PFF_model_dict, crack_dict)
sys.argv = _saved

from construct_model import construct_model
from input_data_from_mesh import prep_input_data
from field_computation import FieldComputation
from compute_energy import gradients, strain_energy_with_split

DEVICE = torch.device("cpu")
FINE_MESH = str(HERE / "meshed_geom2.msh")

ARCHIVE = HERE / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12"
CYCLES_TO_AUDIT = [10, 30, 50, 70]   # earlier + MIT-4 c50 + later


def load_psi_at_cycle(field_comp, inp, T_conn, area_T, matprop, pffmodel,
                      umax, ckpt_path):
    """Reload NN at cycle, recompute ψ⁺_raw + g·ψ⁺ + α_elem per element."""
    field_comp.lmbda = torch.tensor(umax, device=DEVICE)
    field_comp.net.load_state_dict(
        torch.load(str(ckpt_path), map_location=DEVICE, weights_only=True))
    field_comp.net.eval()
    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        s11, s22, s12, _, _ = gradients(inp, u, v, alpha, area_T, T_conn)
        if T_conn is None:
            alpha_elem = alpha
        else:
            alpha_elem = (alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]]
                          + alpha[T_conn[:, 2]]) / 3
        _, E_el_p = strain_energy_with_split(s11, s22, s12, alpha_elem,
                                             matprop, pffmodel)
        g_alpha, _ = pffmodel.Edegrade(alpha_elem)
    return (E_el_p.detach().cpu().numpy(),
            g_alpha.detach().cpu().numpy(),
            alpha_elem.detach().cpu().numpy())


def main():
    pffmodel, matprop, network = construct_model(
        PFF_model_dict, mat_prop_dict, network_dict, domain_extrema, DEVICE,
        williams_dict=None,
    )
    inp, T_conn, area_T, _ = prep_input_data(
        matprop, pffmodel, crack_dict, numr_dict,
        mesh_file=FINE_MESH, device=DEVICE,
    )
    field_comp = FieldComputation(
        net=network, domain_extrema=domain_extrema,
        lmbda=torch.tensor([0.0], device=DEVICE), theta=loading_angle,
        alpha_constraint=numr_dict["alpha_constraint"],
        williams_dict=None, l0=mat_prop_dict["l0"],
    )
    inp_np = inp.detach().cpu().numpy()
    T_np = (T_conn.cpu().numpy() if isinstance(T_conn, torch.Tensor)
            else T_conn)
    cx = (inp_np[T_np[:, 0], 0] + inp_np[T_np[:, 1], 0] + inp_np[T_np[:, 2], 0]) / 3.0
    cy = (inp_np[T_np[:, 0], 1] + inp_np[T_np[:, 1], 1] + inp_np[T_np[:, 2], 1]) / 3.0

    rows = []
    for c in CYCLES_TO_AUDIT:
        nn_ckpt = ARCHIVE / "best_models" / f"trained_1NN_{c}.pt"
        ck_ckpt = ARCHIVE / "best_models" / f"checkpoint_step_{c}.pt"
        if not nn_ckpt.is_file() or not ck_ckpt.is_file():
            print(f"  [skip] cycle {c}: missing files")
            continue

        psi, g_alpha, alpha_elem = load_psi_at_cycle(
            field_comp, inp, T_conn, area_T, matprop, pffmodel,
            umax=0.12, ckpt_path=nn_ckpt
        )
        gpsi = g_alpha * psi

        # Need previous cycle's psi to compute Δψ⁺ and Δᾱ
        prev_c = max(0, c - 1)
        nn_prev = ARCHIVE / "best_models" / f"trained_1NN_{prev_c}.pt"
        if nn_prev.is_file():
            psi_prev, g_alpha_prev, _ = load_psi_at_cycle(
                field_comp, inp, T_conn, area_T, matprop, pffmodel,
                umax=0.12, ckpt_path=nn_prev
            )
            gpsi_prev = g_alpha_prev * psi_prev
        else:
            gpsi_prev = np.zeros_like(gpsi)

        delta_psi = np.maximum(0.0, gpsi - gpsi_prev)        # H(Δψ⁺) · Δψ⁺
        delta_alpha = delta_psi    # Carrara linear: Δᾱ = ReLU(Δ(g·ψ⁺))

        # hist_fat
        ck = torch.load(str(ck_ckpt), map_location='cpu', weights_only=True)
        hist_fat = ck.get('hist_fat')
        if hist_fat is None:
            print(f"  [warn] cycle {c}: no hist_fat in checkpoint")
            hist_fat_np = np.zeros_like(psi)
        else:
            hist_fat_np = hist_fat.detach().cpu().numpy().ravel()

        print(f"\n========== cycle {c} ==========")

        # D1: max g·ψ⁺_raw at α ∈ [0.5, 0.95] (current MIT-4 def)
        for win_lo, win_hi, label in [(0.5, 0.95, "D1a [0.5,0.95]"),
                                       (0.3, 0.5,  "D1b [0.3,0.5]"),
                                       (0.5, 0.7,  "D1c [0.5,0.7]"),
                                       (0.7, 0.95, "D1d [0.7,0.95]")]:
            mask = (alpha_elem >= win_lo) & (alpha_elem <= win_hi)
            if mask.sum() == 0:
                print(f"  {label}: no elements in window")
                continue
            idx_within = mask.nonzero()[0]
            sub_gpsi = gpsi[mask]
            sub_max_local = sub_gpsi.argmax()
            elem = idx_within[sub_max_local]
            print(f"  {label:>16}: elem #{elem:>5}  pos=({cx[elem]:>6.4f},{cy[elem]:>+6.4f})  "
                  f"α={alpha_elem[elem]:.3f}  ᾱ={hist_fat_np[elem]:.2f}  "
                  f"ψ⁺={psi[elem]:.3e}  g·ψ⁺={gpsi[elem]:.3e}  Δᾱ={delta_alpha[elem]:.3e}")
            rows.append([c, label, int(elem), float(cx[elem]), float(cy[elem]),
                         float(alpha_elem[elem]), float(hist_fat_np[elem]),
                         float(psi[elem]), float(gpsi[elem]), float(delta_alpha[elem])])

        # D2: max Δᾱ-per-cycle (full domain)
        elem = int(delta_alpha.argmax())
        print(f"  {'D2 max Δᾱ':>16}: elem #{elem:>5}  pos=({cx[elem]:>6.4f},{cy[elem]:>+6.4f})  "
              f"α={alpha_elem[elem]:.3f}  ᾱ={hist_fat_np[elem]:.2f}  "
              f"ψ⁺={psi[elem]:.3e}  g·ψ⁺={gpsi[elem]:.3e}  Δᾱ={delta_alpha[elem]:.3e}")
        rows.append([c, "D2 max Δᾱ", elem, float(cx[elem]), float(cy[elem]),
                     float(alpha_elem[elem]), float(hist_fat_np[elem]),
                     float(psi[elem]), float(gpsi[elem]), float(delta_alpha[elem])])

        # D3: max ψ⁺_raw · H(Δψ⁺) (full domain)
        H_delta_psi = (delta_psi > 0).astype(float)
        psi_loaded = psi * H_delta_psi
        elem = int(psi_loaded.argmax())
        print(f"  {'D3 ψ⁺·H(Δψ⁺)':>16}: elem #{elem:>5}  pos=({cx[elem]:>6.4f},{cy[elem]:>+6.4f})  "
              f"α={alpha_elem[elem]:.3f}  ᾱ={hist_fat_np[elem]:.2f}  "
              f"ψ⁺={psi[elem]:.3e}  g·ψ⁺={gpsi[elem]:.3e}  Δᾱ={delta_alpha[elem]:.3e}")
        rows.append([c, "D3 ψ⁺·H", elem, float(cx[elem]), float(cy[elem]),
                     float(alpha_elem[elem]), float(hist_fat_np[elem]),
                     float(psi[elem]), float(gpsi[elem]), float(delta_alpha[elem])])

        # Reference: max ψ⁺_raw (no filter)
        elem = int(psi.argmax())
        print(f"  {'(ref) max ψ⁺':>16}: elem #{elem:>5}  pos=({cx[elem]:>6.4f},{cy[elem]:>+6.4f})  "
              f"α={alpha_elem[elem]:.3f}  ᾱ={hist_fat_np[elem]:.2f}  "
              f"ψ⁺={psi[elem]:.3e}  g·ψ⁺={gpsi[elem]:.3e}  Δᾱ={delta_alpha[elem]:.3e}")

        # Reference: max ᾱ
        elem = int(hist_fat_np.argmax())
        print(f"  {'(ref) max ᾱ':>16}: elem #{elem:>5}  pos=({cx[elem]:>6.4f},{cy[elem]:>+6.4f})  "
              f"α={alpha_elem[elem]:.3f}  ᾱ={hist_fat_np[elem]:.2f}  "
              f"ψ⁺={psi[elem]:.3e}  g·ψ⁺={gpsi[elem]:.3e}  Δᾱ={delta_alpha[elem]:.3e}")

    # Save CSV
    out_csv = HERE / "audit_active_driver_results.csv"
    cols = ["cycle", "definition", "elem_idx", "cx", "cy", "alpha", "alpha_bar",
            "psi_raw", "gpsi", "delta_alpha"]
    with open(out_csv, "w") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(v) for v in r) + "\n")
    print(f"\n→ {out_csv.relative_to(HERE.parent)}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
