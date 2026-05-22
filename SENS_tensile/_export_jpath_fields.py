#!/usr/bin/env python3
"""Export J-path PIDL fields (α, ψ⁺/elem, ᾱ/elem) at given cycles for FEM comparison.
Run on Taobo from SENS_tensile/. Outputs npy to /tmp/jpath_fields/."""
import sys
from pathlib import Path
sys.argv = ["x", "8", "400", "1", "TrainableReLU", "1.0"]
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "source"))
import numpy as np, torch
import config
from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from fit import _compute_psi_raw_per_elem

ARCH = HERE / ("hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1"
               "_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_jpath_lam0.1_nt100")
BM = ARCH / "best_models"
OUT = Path("/tmp/jpath_fields"); OUT.mkdir(exist_ok=True)
CYCLES = [40, 70, 82]
dev = config.device

pff, mat, net = construct_model(config.PFF_model_dict, config.mat_prop_dict,
    config.network_dict, config.domain_extrema, dev,
    williams_dict=config.williams_dict, fourier_dict=config.fourier_dict)
inp, T_conn, area_T, _ = prep_input_data(mat, pff, config.crack_dict, config.numr_dict,
    mesh_file=config.fine_mesh_file, device=dev)
fc = FieldComputation(net=net, domain_extrema=config.domain_extrema,
    lmbda=torch.tensor([0.0], device=dev), theta=config.loading_angle,
    alpha_constraint=config.numr_dict["alpha_constraint"],
    williams_dict=config.williams_dict, l0=config.mat_prop_dict["l0"],
    exact_bc_dict=config.exact_bc_dict)
fc.net = fc.net.to(dev); fc.domain_extrema = fc.domain_extrema.to(dev); fc.theta = fc.theta.to(dev)

# element centroids (PIDL mesh)
Tn = T_conn.cpu().numpy(); xy = inp.detach().cpu().numpy()
cen = np.stack([xy[Tn].mean(1)[:,0], xy[Tn].mean(1)[:,1]], axis=1)
np.save(OUT / "coords.npy", xy)
np.save(OUT / "elem_centroids.npy", cen)

for c in CYCLES:
    f = BM / f"trained_1NN_{c}.pt"
    if not f.exists(): print(f"MISSING {f}"); continue
    fc.net.load_state_dict(torch.load(str(f), map_location=dev)); fc.net.eval()
    fc.lmbda = torch.tensor([config.fatigue_dict["disp_max"]], device=dev)  # peak load
    u, v, a = fc.fieldCalculation(inp)
    np.save(OUT / f"alpha_c{c:02d}.npy", a.detach().cpu().numpy())
    # raw undegraded ψ⁺ per element
    psi = _compute_psi_raw_per_elem(inp, u, v, a, mat, pff, area_T, T_conn)
    psi = psi.detach().cpu().numpy().ravel()
    np.save(OUT / f"psi_c{c:02d}.npy", psi)
    # ᾱ (hist_fat) per element from checkpoint_step
    ck = BM / f"checkpoint_step_{c}.pt"
    abar = None
    if ck.exists():
        d = torch.load(str(ck), map_location=dev)
        if 'hist_fat' in d: abar = d['hist_fat'].cpu().numpy().ravel()
    if abar is not None: np.save(OUT / f"abar_c{c:02d}.npy", abar)
    print(f"c{c}: alpha_max={float(a.max()):.4f} | psi_max={psi.max():.2f} psi_p99={np.percentile(psi,99):.4f} "
          f"psi_median={np.median(psi):.5f} | abar_max={(abar.max() if abar is not None else float('nan')):.3f}")
print("DONE", OUT)
