import torch
import numpy as np
from pathlib import Path
from utils import parse_mesh, hist_alpha_init

# Prepare input data
def prep_input_data(matprop, pffmodel, crack_dict, numr_dict, mesh_file, device,
                    sidecar_S1_dict=None, sidecar_label=""):
    '''
    Input data is prepared from the .msh file.
    If gradient_type = numerical:
        X, Y = nodal coordinates
        T_conn = connectivity
    If gradient_type = autodiff:
        X, Y = coordinate of the Gauss point in one point Gauss quadrature
        T_conn = None
    area_T: area of elements

    hist_alpha = initial alpha field

    sidecar_S1_dict : optional dict — if provided with enable=True, the parsed
        mesh is refined near the tip via 1-to-4 red refinement (with green
        closure) BEFORE conversion to tensors. The base Deep Ritz / Carrara
        loss is untouched; only collocation density changes. See
        docs/sidecar_true_adaptive_sampling.md.
    '''
    assert Path(mesh_file).suffix == '.msh', "Mesh file should be a .msh file"

    # Parse in numerical mode to get nodal coords + connectivity (needed by
    # the refinement helper). We re-derive autodiff Gauss points below if
    # gradient_type == 'autodiff'.
    X, Y, T_conn_np, area_np = parse_mesh(filename=mesh_file, gradient_type='numerical')

    if sidecar_S1_dict is not None and sidecar_S1_dict.get("enable", False):
        from sidecar_sampling import maybe_refine_for_sidecar
        X, Y, T_conn_np, area_np = maybe_refine_for_sidecar(
            X, Y, T_conn_np, area_np, sidecar_S1_dict, label=sidecar_label
        )

    if numr_dict["gradient_type"] == 'autodiff':
        X_pts = (X[T_conn_np[:, 0]] + X[T_conn_np[:, 1]] + X[T_conn_np[:, 2]]) / 3.0
        Y_pts = (Y[T_conn_np[:, 0]] + Y[T_conn_np[:, 1]] + Y[T_conn_np[:, 2]]) / 3.0
    else:
        X_pts, Y_pts = X, Y

    inp = torch.from_numpy(np.column_stack((X_pts, Y_pts))).to(torch.float).to(device)
    T_conn = torch.from_numpy(T_conn_np).to(torch.long).to(device)
    area_T = torch.from_numpy(area_np).to(torch.float).to(device)
    if numr_dict["gradient_type"] == 'autodiff':
        T_conn = None

    hist_alpha = hist_alpha_init(inp, matprop, pffmodel, crack_dict)

    return inp, T_conn, area_T, hist_alpha


