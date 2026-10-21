"""Compare saved Q4/T3 fields on Q4 Gauss support; never train or solve."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.tri import Triangulation
import numpy as np
from scipy.io import loadmat


def read_rows(path):
    if not path.is_file():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def q4_support(x, q):
    g = 1/np.sqrt(3)
    z = np.array([[-g, -g], [g, -g], [g, g], [-g, g]])
    sx = np.array([-1, 1, 1, -1])
    sy = np.array([-1, -1, 1, 1])
    N = (1+z[:, 0, None]*sx)*(1+z[:, 1, None]*sy)/4
    dxi = sx*(1+z[:, 1, None]*sy)/4
    deta = sy*(1+z[:, 0, None]*sx)/4
    a = np.einsum('qi,eij->eqj', dxi, x[q])
    b = np.einsum('qi,eij->eqj', deta, x[q])
    weights = a[:, :, 0]*b[:, :, 1]-a[:, :, 1]*b[:, :, 0]
    assert np.all(weights > 0)
    assert np.isclose(weights.sum(), 1., rtol=0, atol=1e-9)
    points = np.einsum('qi,eij->eqj', N, x[q])
    return N, weights, points


def t3_map(nodes, tri, points):
    xy = points.reshape(-1, 2)
    finder = Triangulation(nodes[:, 0], nodes[:, 1], tri).get_trifinder()
    ids = finder(xy[:, 0], xy[:, 1])
    assert np.all(ids >= 0), 'Uncovered common Gauss point; no extrapolation'
    conn = tri[ids]
    v = nodes[conn]
    a, b, p = v[:, 1]-v[:, 0], v[:, 2]-v[:, 0], xy-v[:, 0]
    det = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
    w1 = (p[:, 0]*b[:, 1]-p[:, 1]*b[:, 0])/det
    w2 = (a[:, 0]*p[:, 1]-a[:, 1]*p[:, 0])/det
    bary = np.column_stack([1-w1-w2, w1, w2])
    assert bary.min() >= -1e-9 and bary.max() <= 1+1e-9
    np.testing.assert_allclose(np.einsum('ij,ijk->ik', bary, v), xy, rtol=0, atol=1e-12)
    return conn, bary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fem', type=Path, required=True)
    p.add_argument('--pidl', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists()
    provenance = {}
    def record(path):
        provenance[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    record(Path(__file__))
    record(a.fem/'mesh.mat')
    record(a.fem/'trajectory.csv')
    record(a.fem.parents[1]/'analysis/reference_verification.json')
    m = loadmat(a.fem/'mesh.mat', simplify_cells=True)
    x = m['nodes'][:, :2]
    q = np.asarray(m['quads'], int)-1
    N, weights, points = q4_support(x, q)
    area = weights.sum(1)
    n = len(x)
    angle = float(m.get('angle_degrees', 0.))
    theta = np.deg2rad(angle)
    verification = json.loads((a.fem.parents[1]/'analysis/reference_verification.json').read_text())
    assert verification['model_contract']=='common-box-at1-seed1-20261021'
    assert verification['kkt_definition']=='normal_cone_unscaled_original_gradient_units'
    record(a.fem/'constraint_contract.mat')
    fr = read_rows(a.fem/'trajectory.csv')
    assert len(fr) == verification['accepted_prefix']
    f_by = {int(r['step']): r for r in fr}
    pr = read_rows(a.pidl/'trajectory.csv') if a.pidl else []
    p_by = {int(r['step']): r for r in pr}
    assert sorted(p_by) == list(range(1, len(pr)+1)), 'NN saved trajectory must be contiguous'
    available = sorted(f_by.keys() & p_by.keys())
    mapped = {}
    rejected = None
    pidl_exit = None
    if available:
        for path in [a.pidl/'mesh.npz', a.pidl/'settings.json', a.pidl/'trajectory.csv', a.pidl/'state_000.npz']:
            record(path)
        exit_path = a.pidl.parent/'exit.json'
        if exit_path.is_file():
            record(exit_path)
            pidl_exit = json.loads(exit_path.read_text())
        pm = np.load(a.pidl/'mesh.npz')
        px, tri = pm['nodes'], pm['triangles'].astype(int)
        settings = json.loads((a.pidl/'settings.json').read_text())
        assert float(settings.get('angle_degrees', 0.)) == angle
        assert settings['pff'] == 'AT1' and settings['split'] == 'AMOR' and not settings['fatigue']
        assert settings['network'] == dict(model_type='MLP', hidden_layers=8, neurons=400, seed=1, activation='TrainableReLU', init_coeff=3.)
        assert settings['material'] == dict(E=1., nu=.3, Gc=.01, ell=.01, eta=0.)
        assert settings['hard_initial_crack'] and settings['irreversibility_tolerance'] == .005
        assert settings['irreversibility_quadrature'] is None and settings['weight_decay'] == 1e-5
        assert settings['max_epochs'] == 10000
        assert settings['contract']=='common-box-at1-seed1-20261021'
        assert settings['damage_output']=='smooth sigmoid plus exact geometric crack boundary'
        assert verification['model_contract']==settings['contract']
        assert verification['kkt_definition']=='normal_cone_unscaled_original_gradient_units'
        np.testing.assert_allclose(settings['schedule'], np.asarray(m['schedule']).ravel(), rtol=0, atol=1e-14)
        conn, bary = t3_map(px, tri, points)
        # Reproduce the runner's torch.isclose mask on its float32 coordinates.
        p32 = px.astype(np.float32)
        top = np.flatnonzero(np.isclose(p32[:, 1], .5, rtol=1e-5, atol=1e-8))
        bot = np.flatnonzero(np.isclose(p32[:, 1], -.5, rtol=1e-5, atol=1e-8))
        free = np.setdiff1d(np.arange(len(px)), np.r_[top, bot])
        previous = np.load(a.pidl/'state_000.npz')['alpha'].ravel()
        crack=(np.abs(p32[:,1])<1e-10)&(p32[:,0]>=-.5-1e-10)&(p32[:,0]<=1e-10)
        assert crack.any() and np.all(previous[crack]==1) and np.all((previous>=0)&(previous<=1))
        for step in available:
            record(a.pidl/f'state_{step:03d}.npz')
            s = np.load(a.pidl/f'state_{step:03d}.npz')
            d, u, v, old = [s[k].ravel() for k in ['alpha', 'u', 'v', 'hist_alpha']]
            fu, fv = [s[k].ravel() for k in ['force_u', 'force_v']]
            assert int(s['step']) == step and abs(float(s['U'])-float(f_by[step]['U'])) < 1e-7
            nnrow = p_by[step]
            assert int(nnrow['step']) == step and abs(float(nnrow['U'])-float(s['U'])) < 1e-7
            assert str(s['timing']) == 'post_solve_pre_history_update'
            assert float(s.get('angle_degrees', 0.)) == angle
            finite = all(np.isfinite(z).all() for z in [d, u, v, old, fu, fv])
            finite = finite and all(np.isfinite(float(value)) for key, value in nnrow.items() if key != 'stop_reason')
            valid = finite and np.all(d[crack]==1) and np.all((d>=0)&(d<=1)) and d.min() >= -.005 and d.max() <= 1.005 and (old-d).max() <= .005
            if not valid:
                rejected = dict(step=step, U=float(s['U']), all_required_fields_and_rows_finite=bool(finite),
                    alpha_min=float(d.min()) if np.isfinite(d).all() else None,
                    alpha_max=float(d.max()) if np.isfinite(d).all() else None,
                    max_healing=float((old-d).max()) if np.isfinite(old-d).all() else None,
                    excluded_saved_steps=[k for k in sorted(p_by) if k >= step])
                break  # A saved rejected candidate is not an accepted prefix.
            assert np.array_equal(old, previous)
            numeric = dict(Rx_top=fu[top].sum(dtype=np.float64), Rx_bottom=fu[bot].sum(dtype=np.float64),
                alpha_min=d.min(), alpha_max=d.max(), max_healing=(old-d).max(),
                res_u=np.sqrt(np.square(fu[free].astype(float)).sum()+np.square(fv[free].astype(float)).sum()),
                E_el=s['E_el_elem'].sum(dtype=np.float64), E_d=s['E_d_elem'].sum(dtype=np.float64),
                E_hist=s['E_hist_elem'].sum(dtype=np.float64))
            if 'Ry_top' in nnrow:
                numeric.update(Ry_top=fv[top].sum(dtype=np.float64), Ry_bottom=fv[bot].sum(dtype=np.float64))
                numeric['Ralong_top']=numeric['Rx_top']*np.cos(theta)+numeric['Ry_top']*np.sin(theta)
                numeric['Ralong_bottom']=numeric['Rx_bottom']*np.cos(theta)+numeric['Ry_bottom']*np.sin(theta)
            for key, value in numeric.items():
                assert np.isclose(value, float(nnrow[key]), rtol=1e-4, atol=1e-7), (step, key, value, nnrow[key])
            U = float(s['U'])
            np.testing.assert_allclose(u[top], U*np.cos(theta), rtol=0, atol=2e-6)
            np.testing.assert_allclose(v[top], U*np.sin(theta), rtol=0, atol=2e-6)
            np.testing.assert_allclose(u[bot], 0, rtol=0, atol=2e-6)
            np.testing.assert_allclose(v[bot], 0, rtol=0, atol=2e-6)
            interpolate = lambda z: (z[conn]*bary).sum(1).reshape(weights.shape)
            mapped[step] = [interpolate(d), interpolate(u), interpolate(v)]
            previous = d
    common = sorted(mapped)
    metrics, saved = [], {}
    for step in sorted(f_by):
        record(a.fem/f'state_{step:03d}.mat')
        s = loadmat(a.fem/f'state_{step:03d}.mat', simplify_cells=True)
        assert s['timing'] == 'post_solve_pre_history_update'
        assert s['step'] == step and abs(float(s['U'])-float(f_by[step]['U'])) < 1e-14
        assert float(s.get('angle_degrees', 0.)) == angle
        assert float(s['res_u'])+float(s['res_pf']) <= 1e-4
        uv = s['displ'].ravel()
        fg = [np.einsum('qi,ei->eq', N, z[q]) for z in [s['p_field'].ravel(), uv[:n], uv[n:]]]
        saved[step] = [((v*weights).sum(1)/area) for v in fg]
        if step not in mapped:
            continue
        ng = mapped[step]
        delta = ng[0]-fg[0]
        du2 = (ng[1]-fg[1])**2+(ng[2]-fg[2])**2
        f, nn = f_by[step], p_by[step]
        rx, ry = float(nn['Rx_top']), float(nn.get('Ry_top', 0.))
        # For0degree the stored force_v also permits the unreported Ry.
        if 'Ry_top' not in nn:
            st = np.load(a.pidl/f'state_{step:03d}.npz')
            ry = float(st['force_v'].ravel()[top].sum(dtype=np.float64))
        fforce = s['forces'].ravel()
        ftop = np.asarray(m['top'], int)-1
        frx, fry = fforce[ftop].sum(), fforce[ftop+n].sum()
        metrics.append(dict(step=step, U=float(f['U']), angle_degrees=angle,
            damage_MAE=float((abs(delta)*weights).sum()),
            damage_RMSE=float(np.sqrt((delta**2*weights).sum())),
            displacement_vector_RMSE=float(np.sqrt((du2*weights).sum())),
            FEM_Rx=float(frx), FEM_Ry=float(fry), PIDL_Rx=rx, PIDL_Ry=ry,
            FEM_Ralong=float(frx*np.cos(theta)+fry*np.sin(theta)),
            PIDL_Ralong=float(rx*np.cos(theta)+ry*np.sin(theta)),
            FEM_E_el=float(f['E_el']), PIDL_E_el=float(nn['E_el']),
            FEM_E_d=float(f['E_d']), PIDL_E_d=float(nn['E_d']),
            PIDL_res_u=float(nn['res_u']), PIDL_stop_reason=nn['stop_reason']))
    a.out.mkdir(parents=True)
    figs = a.out/'figures'; figs.mkdir()
    if metrics:
        with (a.out/'matched_states.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(metrics[0])); w.writeheader(); w.writerows(metrics)
    summary = dict(FEM_states=len(fr), PIDL_saved_rows=len(pr), joint_bounds_BC_history_checked_states=len(common),
        prescribed_states=24, angle_degrees=angle,
        FEM_complete_valid_reference=verification['complete_valid_reference'],
        PIDL_complete=bool(a.pidl and (a.pidl/'COMPLETED.txt').exists() and len(common)==24 and pidl_exit and pidl_exit['exit_code']==0),
        PIDL_exit=pidl_exit, first_rejected_saved_candidate=rejected,
        mean_damage_MAE=float(np.mean([m['damage_MAE'] for m in metrics])) if metrics else None,
        common_support='Q4 2x2 Gauss points/Jacobian weights; T3 barycentric interpolation, no extrapolation',
        mapped_area=float(weights.sum()), spatial_Gauss_coverage=1. if available else None,
        joint_state_coverage=len(common)/24, physical_validation=False,model_contract='common-box-at1-seed1-20261021',FEM_PF_certificate='unscaled normal-cone KKT',
        PIDL_joint_equilibrium_status='not_assessed_no_phase_balance_certificate', scope='synthetic single trajectory/seed; no convergence inferred from loss stop')
    (a.out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (a.out/'input_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    if fr:
        U = [float(r['U']) for r in fr]
        fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.5), constrained_layout=True)
        for ax, key, label in zip(axes, ['Rx_top' if angle==0 else 'Ralong_top', 'E_el', 'E_d'], ['Reaction along load', 'Elastic energy', 'Fracture energy']):
            ax.plot(U, [float(r[key]) for r in fr], color='#0072B2', label='FEM Q4', lw=1.5)
            if metrics:
                nk = {'Rx_top':'PIDL_Ralong', 'Ralong_top':'PIDL_Ralong', 'E_el':'PIDL_E_el', 'E_d':'PIDL_E_d'}[key]
                ax.plot([r['U'] for r in metrics], [r[nk] for r in metrics], '--', color='#D55E00', label='PIDL T3', lw=1.5)
            ax.set(xlabel='Displacement magnitude U (normalized)', ylabel=label)
            ax.grid(alpha=.15); ax.legend(frameon=False)
        fig.suptitle(f'{angle:g} degrees: FEM {len(fr)}/24, matched {len(common)}/24', fontsize=11)
        for ext in ['png', 'pdf']: fig.savefig(figs/f'response.{ext}', dpi=180)
        plt.close(fig)
        selected = common[-1] if common else max(f_by)
        vals = [saved[selected][0]]
        titles = [f'FEM alpha, U={float(f_by[selected]["U"]):.2f}']
        if common:
            nv = (mapped[selected][0]*weights).sum(1)/area
            vals += [nv, nv-vals[0]]; titles += ['PIDL alpha', 'PIDL minus FEM']
        fig, axes = plt.subplots(1, len(vals), figsize=(4*len(vals), 3.6), squeeze=False, constrained_layout=True)
        for i, (v, title) in enumerate(zip(vals, titles)):
            ax = axes[0, i]; err = i==2
            b = max(float(abs(v).max()), 1e-8)
            art = PolyCollection(x[q], array=v, cmap='RdBu_r' if err else 'viridis', edgecolors='none', antialiased=False, rasterized=True)
            art.set_clim(*((-b,b) if err else (-.005,1.005))); ax.add_collection(art)
            ax.set(xlim=(-.5,.5), ylim=(-.5,.5), aspect='equal', xlabel='x', ylabel='y', title=title)
            fig.colorbar(art, ax=ax, label='Alpha difference' if err else 'Alpha', shrink=.8)
        for ext in ['png', 'pdf']: fig.savefig(figs/f'damage.{ext}', dpi=180)
        plt.close(fig)
        for stem in ['response', 'damage']:
            (figs/f'{stem}.md').write_text(f'''# How to read {stem}

## Question and data provenance

Compare saved FEM {a.fem} and PIDL {a.pidl}, same U and post_solve_pre_history_update. Script scripts/shear/analyze_manav_static_pair.py, ../matched_states.csv and ../summary.json. No solve, training or smoothing.

## How to read

Response panels show reaction along the applied displacement direction, elastic energy and fracture energy (normalized). Blue FEM and orange dashed PIDL; all available verified common states are included. Damage panels show highest common accepted U={float(f_by[selected]['U']):.17g}, selected irrespective of appearance; otherwise FEM only at highest accepted U. Q4 Gauss-weighted means, independent T3 barycentric values at exactly the same points, then Gauss-weighted cell means. Native Q4 and PIDL T3 damage share[-.005,1.005], signed difference uses symmetric limits. Error metrics integrate pointwise differences at all4Gauss points, not differences after cell averaging. No extrapolation; total support area={weights.sum():.17g}.

## Interpretation and limitations

Coverage FEM{len(fr)}/24, joint{len(common)}/24; mean pointwise Gauss-weighted damageMAE={summary['mean_damage_MAE']}. NN bounds/BC/history checked, its loss stop is not a joint-equilibrium certificate. Distinct discretizations, penalty tolerances and initial recovery/profile are retained. A partial prefix does not establish full-path agreement; synthetic one-seed agreement is not physical/road validation. No paired result exists when joint coverage is zero. Field differences include discretization and quadrature differences. Returned fields are never clipped or selected for apparent agreement.
''')
    (a.out/'README_analysis.md').write_text(json.dumps(summary, indent=2)+'\n\nAll comparisons use saved states at matched U and timing. FEM reference verification is upstream. NN rows failing finite damage, irreversibility or range conditions end the accepted prefix. No accuracy threshold was chosen after seeing results. Initial histories follow the declared distinct paper settings.\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
