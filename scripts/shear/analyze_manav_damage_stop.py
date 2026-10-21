"""Saved nodal/Gauss support diagnosis at R012 validity stop; never solve."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat
from analyze_manav_static_pair import q4_support


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    r = a.run
    fem = r/'retrieved/fem'
    m = loadmat(fem/'mesh.mat', simplify_cells=True)
    paths = list(fem.glob('failed_state_*.mat'))
    assert len(paths) == 1
    s = loadmat(paths[0], simplify_cells=True)
    assert s['failure_stage'] == 'validity' and s['certificate_valid']
    x = m['nodes'][:, :2]; q = np.asarray(m['quads'], int)-1
    alpha, old = s['p_field'].ravel(), s['p_field_old'].ravel()
    N, w, _ = q4_support(x, q)
    gp = np.einsum('qi,ei->eq', N, alpha[q])
    hg = np.einsum('qi,ei->eq', N, old[q])
    previous = loadmat(fem/f'state_{int(s["step"])-1:03d}.mat', simplify_cells=True)['p_field']
    assert np.array_equal(old, previous)
    free = np.setdiff1d(np.arange(len(x)), np.asarray(m['crack'], int)-1)
    ids = np.flatnonzero(alpha > 1.005)
    keys = ['U','step','stag','failure_stage','rejection_reason','certificate_valid','res_u','res_pf','elapsed_seconds','step_seconds','timing']
    result = {k: s[k].item() if isinstance(s[k], np.generic) else s[k] for k in keys}
    result.update(reported_fresh_coupled_sum=float(s['res_u']+s['res_pf']),
        alpha_min=float(alpha.min()), alpha_max=float(alpha.max()), max_healing=float((old-alpha).max()),
        nodes_above_1_005=len(ids), nodes_above_1=int((alpha>1).sum()), nodes_total=len(x),
        GP_min=float(gp.min()), GP_max=float(gp.max()), GP_count_above_1_005=int((gp>1.005).sum()),
        GP_count_above_1=int((gp>1).sum()), GP_total=gp.size,
        GP_sampled_area_above_1_005=float(w[gp>1.005].sum()), GP_sampled_area_above_1=float(w[gp>1].sum()),
        max_GP_healing=float((hg-gp).max()), history_matches_last_accepted=True,
        last_native_alpha_equals_failed=bool(np.array_equal(s['native_last_completed']['alpha'],alpha)),
        last_native_free_PF_norm=float(np.linalg.norm(s['native_last_completed']['Rpf'][free])), raw_fields_not_clipped=True)
    (r/'analysis/failed_candidate_metrics.json').write_text(json.dumps(result, indent=2)+'\n')
    np.savetxt(r/'analysis/nodes_above_1_005.csv', np.column_stack([ids+1,x[ids],old[ids],alpha[ids]]), delimiter=',', header='node_1based,x,y,previous_alpha,failed_alpha', comments='')
    out = r/'analysis/figures'; out.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.2,4), constrained_layout=True)
    vals = [alpha.max()-1,gp.max()-1]
    ax.bar([0,1], vals, width=.55, color=['#D55E00','#0072B2'])
    ax.axhline(.005, color='#444444', ls='--', lw=1.3, label='Original upper limit minus 1')
    for i,v in enumerate(vals): ax.text(i,v+.00015,f'{v:.6g}',ha='center',fontsize=10)
    ax.set_xticks([0,1],[f'{len(x):,} nodal values',f'{gp.size:,} Gauss samples'])
    ax.set(ylabel='Maximum alpha minus 1',ylim=(0,.008),title=f'{r.name}: U={s["U"]:.2f}\nSame rejected field, different spatial supports')
    ax.legend(frameon=False,fontsize=8,loc='upper right')
    ax.spines[['right','top']].set_visible(False)
    for ext in ['png','pdf']: fig.savefig(out/f'nodal_gauss_range.{ext}',dpi=180)
    plt.close(fig)
    (out/'nodal_gauss_range.md').write_text(f'''# How to read nodal and Gauss ranges

## Question and data provenance

Which saved spatial support violates the frozen range at the rejected equilibrium candidate? Sources: {fem}/mesh.mat and {paths[0].name}; exact values ../failed_candidate_metrics.json and ../nodes_above_1_005.csv. Script scripts/shear/analyze_manav_damage_stop.py, Q4 shape/Jacobian helper analyze_manav_static_pair.py. Only interpolation of saved arrays, no assembly, fitting, clipping or re-solve.

## How to read

One panel compares max(alpha)-1 for all{len(x)}nodes (orange) and all{gp.size}Q4 2x2Gauss samples (blue) of exactly the same U={s['U']} rejected field. Dashed.005 is the unchanged upper-bound excess. Node max={alpha.max():.17g}, with{len(ids)}nodes above1.005; Gauss max={gp.max():.17g}, with{(gp>1.005).sum()}samples above1.005. Residual sum reported at this same field={result['reported_fresh_coupled_sum']:.17g}, below1e-4. PF vector norm is independently recomputed; mechanics norm is the producer scalar, not replayed.

## Interpretation and limitations

The final stop is the nodal-range criterion, after the coupled residual criterion passed. Discrete Gauss sampling does not bound the field between points and does not rescue the rejected state or change the original accepted prefix. {int((gp>1).sum())}Gauss samples exceed exact1; their quadrature-sampled area is{w[gp>1].sum():.12g}, an approximate reduction rather than exact exceedance-region area. This does not identify finite-penalty, inner tolerance or discretization as a unique cause. It does not supply a full U=.4 FEM reference, PIDL comparison, mesh-convergence evidence or physical validation.
''')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
