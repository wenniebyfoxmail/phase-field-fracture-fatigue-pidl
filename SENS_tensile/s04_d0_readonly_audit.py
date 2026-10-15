"""Descriptive R002 audit of saved outputs only; no fit, prediction or selection.

All new decompositions are post-hoc explanations, not acceptance criteria.
Writes only the derived audit JSON, never to source run outputs.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np


def audit(run, geometry):
    rows = list(csv.DictReader((run/'percycle.csv').open()))
    models = json.loads((run/'models.json').read_text())
    receipt = json.loads((run/'receipt.json').read_text())
    selection = json.loads((run/'selection.json').read_text())
    assert receipt['run_id'] == 'S04-E016-D0-R002' and len(rows) == 1071
    with np.load(geometry) as g:
        area = g['areas'].copy()
    result = dict(source_run=str(run), geometry=str(geometry),
                  source_commit=receipt['code_commit'],
                  scope='post-hoc saved-output explanation; no fit/prediction/selection',
                  quantile_note='reference area-weighted q99 at fixed C20; descriptive only, not process-zone qualification',
                  selection=selection, folds={})
    for key in ('u011', 'u0115', 'u012', 'u013'):
        fold = dict(strata={}, bounds={}, C20={}, damage_early={}, damage_mse_shares={})
        for field in ('damage', 'alpha_bar', 'psi_raw_direct'):
            a = [r for r in rows if r['holdout'] == key and r['field'] == field]
            w = np.array([float(r['cycle_weight']) for r in a])
            v = lambda name: np.array([float(r[name]) for r in a])
            fold['bounds'][field] = dict(
                B0_mean_area=float(np.sum(w*v('B0_bound_area'))),
                B1_mean_area=float(np.sum(w*v('bound_violation_area'))),
                B0_min=float(v('B0_min').min()), B0_max=float(v('B0_max').max()),
                B1_min=float(v('B1_min').min()), B1_max=float(v('B1_max').max()))
            bystratum = []
            for s in range(3):
                mask = np.array([int(r['stratum']) == s for r in a])
                ws = w[mask]/w[mask].sum()
                t = {'stratum': s, 'n_cycles': int(mask.sum())}
                for scale in ('physical', 'transformed'):
                    b0 = float(np.sum(ws*v('B0_'+scale+'_mse')[mask]))
                    b1 = float(np.sum(ws*v('B1_'+scale+'_mse')[mask]))
                    t[scale] = dict(B0_rmse=b0**.5, B1_rmse=b1**.5,
                                    ratio=(b1/b0)**.5, mse_change=b1-b0)
                bystratum.append(t)
            fold['strata'][field] = bystratum
            if field == 'damage':
                for lo, hi in ((1, 2), (3, 20)):
                    m = np.array([lo <= int(r['cycle']) <= hi for r in a])
                    b0 = float(np.mean(v('B0_physical_mse')[m]))
                    b1 = float(np.mean(v('B1_physical_mse')[m]))
                    fold['damage_early'][f'C{lo}-{hi}'] = dict(B0_rmse=b0**.5,
                        B1_rmse=b1**.5, ratio=(b1/b0)**.5)
                for arm in ('B0', 'B1'):
                    total = np.sum(w*v(arm+'_physical_mse'))
                    fold['damage_mse_shares'][arm] = [float(
                        sum(float(r['cycle_weight'])*float(r[arm+'_physical_mse'])
                            for r in a if int(r['stratum']) == s)/total) for s in range(3)]
        with np.load(run/(key+'_C20.npz')) as snap:
            w = area[snap['ids']]; w = w/w.sum()
            pin, fem, corrected = [snap[name].copy() for name in ('pin', 'fem', 'B1')]
        delta = corrected-pin
        e0, e1 = pin-fem, corrected-fem
        mean = lambda x: float(np.sum(w*x, dtype=np.float64))
        scales = models['outer_'+key]['scales']
        for j, field in enumerate(('damage', 'alpha_bar', 'psi_raw_direct')):
            b0, b1 = mean(e0[:, j]**2), mean(e1[:, j]**2)
            correction_power = mean(delta[:, j]**2)
            cross = 2*mean(e0[:, j]*delta[:, j])
            assert np.isclose(b1-b0, correction_power+cross, rtol=1e-11, atol=1e-12)
            saved = next(r for r in rows if r['holdout'] == key and
                         r['field'] == field and int(r['cycle']) == 20)
            for arm, value in (('B0', b0), ('B1', b1)):
                assert np.isclose(value, float(saved[arm+'_physical_mse']), rtol=1e-11, atol=1e-14)
            t = dict(B0_rmse=b0**.5, B1_rmse=b1**.5,
                     correction_power=correction_power, cross_term=cross,
                     identity_error=(b1-b0)-(correction_power+cross),
                     fem_max=float(fem[:, j].max()), pin_max=float(pin[:, j].max()),
                     B1_max=float(corrected[:, j].max()))
            for name, values, error, mse in (('B0', pin[:, j], e0[:, j], b0),
                                             ('B1', corrected[:, j], e1[:, j], b1)):
                distance = np.maximum(-values, 0)
                if j == 0:
                    distance += np.maximum(values-1, 0)
                bad = distance > 0
                t[name+'_violation'] = dict(area=mean(bad), rms_distance=mean(distance**2)**.5,
                    max_distance=float(distance.max()), mse_share=mean(error**2*bad)/mse,
                    area_distance_gt_1e_3=mean(distance > 1e-3),
                    area_distance_gt_1e_2=mean(distance > 1e-2))
            if j == 2:
                order = np.argsort(fem[:, j]); cumulative = np.cumsum(w[order])
                threshold = fem[order[np.searchsorted(cumulative, .99)], j]
                tail = fem[:, j] >= threshold
                t['reference_q99_tail'] = dict(threshold=float(threshold), area=mean(tail),
                    B0_mse_share=mean(e0[:, j]**2*tail)/b0,
                    B1_mse_share=mean(e1[:, j]**2*tail)/b1,
                    B0_mse=mean(e0[:, j]**2*tail), B1_mse=mean(e1[:, j]**2*tail))
                peak = int(np.argmax(fem[:, j]))
                t['at_reference_peak'] = dict(fem=float(fem[peak, j]),
                    B0=float(pin[peak, j]), B1=float(corrected[peak, j]))
                sample = np.asarray(receipt['sample_ids'], dtype=int)
                t['sampled_geometry_maxima'] = {name: float(values[sample, j].max())
                    for name, values in (('FEM', fem), ('B0', pin), ('B1', corrected))}
                # Exact nonlinear identity, not a bias correction or new prediction.
                z0 = np.log1p(pin[:, j]/scales[1]); z1 = np.log1p(corrected[:, j]/scales[1])
                assert np.allclose(delta[:, j], (pin[:, j]+scales[1])*np.expm1(z1-z0), rtol=1e-10, atol=1e-10)
            fold['C20'][field] = t
        result['folds'][key] = fold
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--geometry', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.run.resolve(), args.geometry.resolve())
    assert args.out.resolve() != args.run.resolve()
    if args.out.exists():
        assert {p.name for p in args.out.iterdir()} <= {'saved_output_decomposition.json'}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'saved_output_decomposition.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({'status': 'saved-output checks passed', 'output': str(args.out),
                      'folds': list(result['folds']), 'new_fits': 0, 'new_predictions': 0}))
