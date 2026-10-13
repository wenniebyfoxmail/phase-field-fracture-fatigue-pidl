"""Origin-clean, fixed-horizon published-label exploration. No physical claims."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


FEATURES = ['x', 'y', 'recent_dx', 'cycle', 'opening', 'shear']
HISTORY = ['opening_change', 'shear_change', 'previous_opening_change',
           'previous_shear_change']
EXPECTED = {'F': 379, 'FF': 107}


def load_record(root, label, locks):
    names = [f'{label}-cracktip.csv']
    for channel in ['ux', 'uy']:
        for side in ['top', 'bottom']:
            names.append(f'{label}-{channel}-{side}.csv' if label == 'F'
                         else f'{label}_{channel}_{side}.csv')
    for name in names:
        digest = hashlib.md5((root / name).read_bytes()).hexdigest()
        if digest != locks[name]:
            raise ValueError(f'External identity mismatch: {name}')
    tip = np.loadtxt(root / names[0], delimiter=',', skiprows=1)
    if not np.isfinite(tip[:, :3]).all() or not (np.diff(tip[:, 0]) > 0).all():
        raise ValueError('Invalid direct tip chronology')
    targets = {int(row[0]): row[1:3] for row in tip}
    if any(int(row[0]) != row[0] for row in tip):
        raise ValueError('Noninteger cycle')
    response = {}
    coords = {}
    cycles = None
    for name in names[1:]:
        with (root / name).open() as handle:
            header = next(csv.reader(handle))
        keys = [int(value) for value in header[3:]]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate cycle column')
        values = np.loadtxt(root / name, delimiter=',', skiprows=1)
        if not np.isfinite(values).all() or values.shape[1] != len(keys) + 3:
            raise ValueError('Invalid response table')
        if cycles is None:
            cycles = keys
        elif cycles != keys:
            raise ValueError('Response channels have different cycles')
        channel = 'ux' if 'ux' in name else 'uy'
        side = 'top' if 'top' in name else 'bottom'
        coords[channel, side] = values[:, :2]
        keep = (values[:, 0] >= 1) & (values[:, 0] <= 49)
        if keep.sum() < 2:
            raise ValueError('Fixed ROI empty')
        response[channel, side] = values[keep, 3:].mean(axis=0)
    for side in ['top', 'bottom']:
        if not np.array_equal(coords['ux', side], coords['uy', side]):
            raise ValueError('Channel coordinate mismatch')
    signals = {
        n: np.array([response['uy', 'top'][i] - response['uy', 'bottom'][i],
                     response['ux', 'top'][i] - response['ux', 'bottom'][i]])
        for i, n in enumerate(cycles)
    }
    return build_rows(targets, signals)


def build_rows(targets, signals):
    common = set(targets) & set(signals)
    origins = sorted(n for n in common
                     if all(n + d in common for d in [-2000, -1000, 1000]))
    rows = []
    for n in origins:
        xy = targets[n]
        recent = targets[n][0] - targets[n - 1000][0]
        base = np.r_[xy, recent, n, signals[n]]
        history = np.r_[signals[n] - signals[n - 1000],
                        signals[n - 1000] - signals[n - 2000]]
        rows.append({'origin': n, 'target_cycle': n + 1000,
                     'features': np.r_[base, history].tolist(),
                     'target_dx': float(targets[n + 1000][0] - xy[0]),
                     'current_x': float(xy[0]), 'secant_dx': float(recent)})
    return rows


def ridge_predict(train_x, train_y, test_x, alpha=1.0):
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0, ddof=0)
    active = scale > 1e-12
    z = (train_x[:, active] - mean[active]) / scale[active]
    q = (test_x[:, active] - mean[active]) / scale[active]
    intercept = float(train_y.mean())
    beta = np.linalg.solve(z.T @ z + alpha * np.eye(z.shape[1]),
                           z.T @ (train_y - intercept))
    prediction = intercept + q @ beta
    state = {'mean': mean.tolist(), 'scale': scale.tolist(),
             'active': active.tolist(), 'beta': beta.tolist(),
             'intercept': intercept, 'alpha': alpha}
    return prediction, state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--locks', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=['prepare', 'fit'], required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    locks = json.loads(args.locks.read_text())
    result = {}
    for label in ['F', 'FF']:
        rows = load_record(args.data, label, locks)
        if len(rows) != EXPECTED[label]:
            raise ValueError('Frozen eligibility count mismatch')
        cut = len(rows) * 7 // 10
        if rows[cut - 1]['target_cycle'] > rows[cut]['origin']:
            raise ValueError('Fit target not available at first evaluation origin')
        result[label] = {'rows': rows, 'fit_count': cut,
                         'evaluation_count': len(rows) - cut}
    # Prepare writes the same origin-only matrix that fit will use, no fitting.
    (args.out / 'prepared.json').write_text(json.dumps(result, indent=2))
    if args.mode == 'prepare':
        return
    scored = []
    summary = {}
    models = {}
    for label, record in result.items():
        rows, cut = record['rows'], record['fit_count']
        x = np.array([row['features'] for row in rows])
        y = np.array([row['target_dx'] for row in rows])
        predictions = {'B0': np.zeros(len(rows) - cut),
                       'B1': np.array([r['secant_dx'] for r in rows[cut:]])}
        models[label] = {}
        for arm, width in [('M0', 6), ('M1', 10)]:
            predictions[arm], models[label][arm] = ridge_predict(
                x[:cut, :width], y[:cut], x[cut:, :width])
        if not all(np.isfinite(v).all() for v in predictions.values()):
            raise ValueError('Nonfinite prediction')
        errors = {arm: float(np.abs(values - y[cut:]).mean())
                  for arm, values in predictions.items()}
        summary[label] = {'fit_count': cut, 'evaluation_count': len(rows) - cut,
                          'mae_dx_mm': errors,
                          'M1_minus_M0_mm': errors['M1'] - errors['M0'],
                          'M1_beats_both_simple_controls':
                          errors['M1'] < min(errors['B0'], errors['B1'])}
        for i, row in enumerate(rows[cut:]):
            scored.append({'record': label, 'origin_cycle': row['origin'],
                           'target_cycle': row['target_cycle'],
                           'current_x_mm': row['current_x'],
                           'target_dx_mm': row['target_dx'],
                           **{f'{arm}_dx_mm': float(values[i])
                              for arm, values in predictions.items()}})
    summary['equal_record_mean_M1_minus_M0_mm'] = float(np.mean(
        [summary[label]['M1_minus_M0_mm'] for label in ['F', 'FF']]))
    summary['claim'] = 'development-exposed published DIC label diagnostic only'
    with (args.out / 'predictions.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scored[0]))
        writer.writeheader()
        writer.writerows(scored)
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2))
    (args.out / 'models.json').write_text(json.dumps(models, indent=2))


if __name__ == '__main__':
    main()
