"""Score frozen increments against hypothetical labels. No model or fitting imports."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import signal
import socket
import subprocess
import sys
import time


RECORDS = ('F', 'FF')
ARMS = ('B0', 'B1', 'M0', 'M1')
COLUMNS = ['record', 'origin_cycle', 'target_cycle', 'current_x_mm',
           'target_dx_mm'] + [a + '_dx_mm' for a in ARMS]
EPSILONS = [0, .00214, .00428, .00856, .01712, .03424, .06848]
SCENARIOS = ['zero', 'constant_positive', 'constant_negative',
             'drift_positive', 'drift_negative', 'alternating_positive',
             'alternating_negative', 'midpoint_step_positive',
             'midpoint_step_negative']


def check(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b, tol):
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol


def read_json(path):
    return json.loads(Path(path).read_text())


def validate_config(cfg):
    check(cfg['expected_evaluation_rows'] == {'F': 114, 'FF': 33}, 'row contract')
    check(cfg['epsilon_mm'] == EPSILONS, 'epsilon contract')
    check(cfg['scenario_ids'] == SCENARIOS, 'scenario contract')
    check(cfg['record_weights'] == {'F': .5, 'FF': .5}, 'aggregation contract')
    check(cfg['arms'] == list(ARMS) and cfg['horizon_cycles'] == 1000, 'arm/horizon contract')
    check(cfg['zero_tolerance_mm'] == 1e-10 and
          cfg['baseline_reproduction_atol_mm'] == 1e-10, 'tolerance contract')
    check(cfg['runtime_cap_seconds_if_later_executed'] == 60 and
          cfg['memory_cap_mb_if_later_executed'] == 1024, 'budget contract')
    for key in ['training', 'fitting', 'model_forward', 'recompute_secant',
                'recompute_absolute_forecast', 'random_simulation',
                'optimisation', 'feature_noise_correction', 'epsilon_is_calibrated']:
        check(cfg[key] is False, 'forbidden operation: ' + key)


def scores(rows, errors):
    check(bool(rows), 'empty record')
    mae = {a: math.fsum(abs(r[a + '_dx_mm'] -
                (r['target_dx_mm'] + (errors[r['target_cycle']] -
                 errors[r['origin_cycle']])) ) for r in rows) / len(rows)
           for a in ARMS}
    mae['D_mm'] = mae['M1'] - mae['M0']
    mae['M0_minus_B1_mm'] = mae['M0'] - mae['B1']
    mae['M1_minus_B1_mm'] = mae['M1'] - mae['B1']
    return mae


def nodes(rows):
    return sorted({r[k] for r in rows for k in ['origin_cycle', 'target_cycle']})


def node_errors(keys, epsilon, scenario):
    check(len(keys) >= 2 and keys == sorted(set(keys)), 'invalid endpoint nodes')
    check(epsilon >= 0 and math.isfinite(epsilon), 'invalid epsilon')
    check(scenario in SCENARIOS, 'unknown scenario')
    m = len(keys)
    sign = -1 if scenario.endswith('_negative') else 1
    errors = {}
    for j, key in enumerate(keys):
        if scenario == 'zero':
            e = 0.0
        elif scenario.startswith('constant_'):
            e = sign * epsilon
        elif scenario.startswith('drift_'):
            e = sign * epsilon * (2 * j / (m - 1) - 1)
        elif scenario.startswith('alternating_'):
            e = sign * epsilon * (-1) ** j
        else:
            e = sign * epsilon * (-1 if j < m // 2 else 1)
        check(abs(e) <= epsilon + 1e-15, 'node error outside box')
        errors[key] = e
    return errors


def edge_extrema(q1, q0, y, epsilon):
    lo, hi = y - 2 * epsilon, y + 2 * epsilon
    candidates = [lo, hi] + [q for q in (q0, q1) if lo <= q <= hi]
    values = [abs(q1 - z) - abs(q0 - z) for z in candidates]
    return min(values), max(values)


def bounds(rows, epsilon):
    b = scores(rows, {t: 0.0 for t in nodes(rows)})
    pairs = [edge_extrema(r['M1_dx_mm'], r['M0_dx_mm'],
                         r['target_dx_mm'], epsilon) for r in rows]
    lower_row = math.fsum(p[0] for p in pairs) / len(rows)
    upper_row = math.fsum(p[1] for p in pairs) / len(rows)
    lower_lip, upper_lip = b['D_mm'] - 4 * epsilon, b['D_mm'] + 4 * epsilon
    return {'D0_mm': b['D_mm'], 'lower_lipschitz_mm': lower_lip,
            'upper_lipschitz_mm': upper_lip, 'lower_row_mm': lower_row,
            'upper_row_mm': upper_row, 'lower_mm': max(lower_row, lower_lip),
            'upper_mm': min(upper_row, upper_lip)}


def mean_dict(a, b):
    check(a.keys() == b.keys(), 'aggregation schema mismatch')
    return {key: (a[key] + b[key]) / 2 for key in a}


def validate_inputs(input_root, cfg, source_data, lock):
    """Validate old rows and baseline; no reconstruction of trained model output."""
    tol = cfg['baseline_reproduction_atol_mm']
    for name, expected in lock.items():
        check(hashlib.md5((source_data / name).read_bytes()).hexdigest() == expected,
              'external data lock mismatch: ' + name)
    prepared = read_json(input_root / 'prepared.json')
    summary = read_json(input_root / 'summary.json')
    with (input_root / 'predictions.csv').open(newline='') as handle:
        reader = csv.DictReader(handle)
        check(reader.fieldnames == COLUMNS, 'prediction schema mismatch')
        raw = list(reader)
    groups = {r: [] for r in RECORDS}
    for row in raw:
        check(row['record'] in groups, 'unknown record')
        r = {'record': row['record']}
        for key in COLUMNS[1:]:
            r[key] = int(row[key]) if key.endswith('_cycle') else float(row[key])
            check(math.isfinite(r[key]), 'nonfinite prediction row')
        check(r['target_cycle'] - r['origin_cycle'] == 1000, 'non1000 edge')
        groups[r['record']].append(r)
    for record, rows in groups.items():
        n = cfg['expected_evaluation_rows'][record]
        check(len(rows) == n, 'evaluation count mismatch')
        origins = [r['origin_cycle'] for r in rows]
        check(origins == sorted(set(origins)), 'duplicate/unordered origins')
        p = prepared[record]
        check(p['fit_count'] == {'F': 265, 'FF': 74}[record], 'fit split mismatch')
        check(p['evaluation_count'] == n, 'prepared count mismatch')
        expected = p['rows'][p['fit_count']:]
        check(len(expected) == n, 'prepared tail mismatch')
        coordinates = {}
        for r, exp in zip(rows, expected):
            for key, pk in [('origin_cycle', 'origin'), ('target_cycle', 'target_cycle'),
                            ('current_x_mm', 'current_x'), ('target_dx_mm', 'target_dx'),
                            ('B1_dx_mm', 'secant_dx')]:
                check(close(r[key], exp[pk], tol), 'prepared row mismatch: ' + key)
            check(r['B0_dx_mm'] == 0, 'persistence mismatch')
            for cycle, x in [(r['origin_cycle'], r['current_x_mm']),
                             (r['target_cycle'], r['current_x_mm'] + r['target_dx_mm'])]:
                if cycle in coordinates:
                    check(close(coordinates[cycle], x, tol), 'inconsistent shared coordinate')
                coordinates[cycle] = x
        baseline = scores(rows, {k: 0 for k in nodes(rows)})
        for arm in ARMS:
            check(close(baseline[arm], summary[record]['mae_dx_mm'][arm], tol),
                  'baseline MAE mismatch: ' + arm)
        check(close(baseline['D_mm'], summary[record]['M1_minus_M0_mm'], tol),
              'baseline difference mismatch')
    baseline_mean = mean_dict(*(scores(groups[r], {n: 0 for n in nodes(groups[r])})
                                for r in RECORDS))
    check(close(baseline_mean['D_mm'], summary['equal_record_mean_M1_minus_M0_mm'], tol),
          'equal-record baseline mismatch')
    return groups


def analyse(groups, cfg):
    tol = cfg['zero_tolerance_mm']
    bounds_table, scenarios_table = [], []
    previous = {}
    for epsilon in cfg['epsilon_mm']:
        this_bounds = {r: bounds(groups[r], epsilon) for r in RECORDS}
        this_bounds['equal_record'] = mean_dict(*this_bounds.values())
        for record, b in this_bounds.items():
            check(b['lower_mm'] <= b['D0_mm'] + tol and
                  b['upper_mm'] >= b['D0_mm'] - tol, 'baseline outside envelope')
            if record in previous:
                check(b['lower_mm'] <= previous[record]['lower_mm'] + tol and
                      b['upper_mm'] >= previous[record]['upper_mm'] - tol,
                      'envelope not nested')
            previous[record] = b
            bounds_table.append({'record': record, 'epsilon_mm': epsilon, **b,
                                 'certified_M1_worse': b['lower_mm'] > tol})
        for scenario in cfg['scenario_ids']:
            metrics = {r: scores(groups[r], node_errors(nodes(groups[r]), epsilon, scenario))
                       for r in RECORDS}
            metrics['equal_record'] = mean_dict(*metrics.values())
            for record, m in metrics.items():
                b = this_bounds[record]
                check(b['lower_mm'] - tol <= m['D_mm'] <= b['upper_mm'] + tol,
                      'scenario outside envelope')
                if scenario.startswith('constant_') or epsilon == 0 or scenario == 'zero':
                    check(close(m['D_mm'], b['D0_mm'], tol), 'bias/zero invariance failed')
                scenarios_table.append({'record': record, 'epsilon_mm': epsilon,
                    'scenario': scenario, **m,
                    'sign': 'M1_better_witness' if m['D_mm'] < -tol else
                            ('M1_worse' if m['D_mm'] > tol else 'numerically_unresolved')})
    return bounds_table, scenarios_table


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def compact_summary(bs, ss, cfg):
    result = {}
    for record in [*RECORDS, 'equal_record']:
        b = [r for r in bs if r['record'] == record]
        s = [r for r in ss if r['record'] == record]
        witnesses = [r for r in s if r['sign'] == 'M1_better_witness']
        result[record] = {
            'baseline_D_mm': b[0]['D0_mm'],
            'universal_sufficient_radius_mm': b[0]['D0_mm'] / 4,
            'certified_grid_epsilon_mm': [r['epsilon_mm'] for r in b if r['certified_M1_worse']],
            'first_tested_witness_epsilon_mm': min((r['epsilon_mm'] for r in witnesses), default=None),
            'witnesses': [{k: r[k] for k in ['epsilon_mm', 'scenario', 'D_mm']}
                          for r in witnesses],
            'bounds': b}
    return {'source_run': cfg['source_run'], 'amendment': cfg['amendment_id'],
            'result': result, 'original_verdict': 'unchanged_negative_label_diagnostic',
            'training': False, 'fitting': False, 'model_forward': False,
            'uncertainty_calibrated': False,
            'interpretation': 'Deterministic conditional bounds; witnesses are mathematical examples only.'}


def plot_tables(bs, ss, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), sharex=True, sharey=True)
    styles = {'zero': ('#777777', '-'), 'constant_positive': ('#999999', ':'),
              'constant_negative': ('#bbbbbb', '--'), 'drift_positive': ('#0072B2', '-'),
              'drift_negative': ('#0072B2', '--'), 'alternating_positive': ('#D55E00', '-'),
              'alternating_negative': ('#D55E00', '--'), 'midpoint_step_positive': ('#009E73', '-'),
              'midpoint_step_negative': ('#009E73', '--')}
    for ax, record in zip(axes, [*RECORDS, 'equal_record']):
        b = [r for r in bs if r['record'] == record]
        x = [r['epsilon_mm'] * 1000 for r in b]
        ax.fill_between(x, [r['lower_mm'] for r in b], [r['upper_mm'] for r in b],
                        color='#aaaaaa', alpha=.22, label='Conservative envelope (not CI)')
        ax.plot(x, [r['lower_mm'] for r in b], color='#333333', lw=1.2)
        ax.plot(x, [r['upper_mm'] for r in b], color='#333333', lw=1.2)
        for scenario, (color, style) in styles.items():
            s = [r for r in ss if r['record'] == record and r['scenario'] == scenario]
            ax.plot([r['epsilon_mm'] * 1000 for r in s], [r['D_mm'] for r in s],
                    color=color, ls=style, lw=1.3, marker='.', ms=4,
                    label=scenario.replace('_', ' '))
        ax.axhline(0, color='black', lw=1)
        ax.set_title({'F': 'F: 114 fixed predictions', 'FF': 'FF: 33 fixed predictions',
                      'equal_record': 'Equal-record mean (1/2 each)'}[record])
        ax.set_xlabel('Assumed coordinate-error bound epsilon (micrometres)')
        ax.grid(alpha=.15)
    axes[0].set_ylabel('MAE(M1) - MAE(M0) (mm)\nPositive: history arm worse')
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=5, fontsize=8,
               bbox_to_anchor=(.5, .005), frameon=False)
    fig.suptitle('S02-E005-R002 | fixed-increment label sensitivity | horizon 1000 cycles\n'
                 'Development-exposed F/FF labels; hypothetical error bounds; no refit or physical accuracy claim', fontsize=11)
    fig.tight_layout(rect=[0, .18, 1, .88])
    fig.savefig(out / 'label_sensitivity.png', dpi=160)
    plt.close(fig)


def readme(summary):
    lines = ['# Fixed-prediction label sensitivity', '',
        'Source: S02-E005-R001 frozen increments; S02-E005-A001 v1-draft numerical contract.',
        'Execution: S02-E005-R002, deterministic CPU scoring only; no fitting/model forward.', '',
        'Read baseline first, then each record envelope, then same-named error paths. All seven radii and nine paths shown.',
        'The grey band is a conservative deterministic envelope, not a confidence interval or attainable global optimum.', '',
        '| Record | Original M1-M0 (mm) | Certified grid radii (micrometres) | First tested reversal witness (micrometres) |',
        '|---|---:|---|---|']
    for record, r in summary['result'].items():
        radii = ', '.join(f'{e*1000:g}' for e in r['certified_grid_epsilon_mm'])
        witness = r['first_tested_witness_epsilon_mm']
        lines.append(f"| {record} | {r['baseline_D_mm']:.9f} | {radii} | " +
                     ('none' if witness is None else f'{witness*1000:g}') + ' |')
    lines += ['', '## Interpretation and limits', '',
        'Lower bound > 1e-10 mm certifies M1 worse only under the assumed coordinate-error box.',
        'A lower bound crossing zero is not a demonstrated reversal. A negative concrete scenario is a consistent mathematical witness, not a likely or measured error.',
        'The baseline is contained in every error class. All scenario labels share endpoint errors across adjacent windows; predictors, including B1, remain frozen.',
        'Constant coordinate offsets cancel in increment labels; absolute position bias remains unidentified.',
        'No actual F/FF uncertainty, physical tip accuracy, input-noise correction, retraining benefit, causal mechanism, or road generalisation is established.',
        'Original S02-E005 negative verdict is unchanged. No expanded grid or tuning follows from this analysis.', '',
        '## Figure', '',
        'label_sensitivity.png uses bounds.csv and scenarios.csv: F, FF and equal-record panels share units/scales; all fixed scenarios are displayed.',
        'Overlapping zero/constant paths are expected. A visual sign change must be confirmed by the exact CSV.',
        'Next action: await applicable repeatability and processing-provenance information, then compare its definition with the assumed error class; SD is not automatically a hard bound.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--source-data', type=Path, required=True)
    parser.add_argument('--data-lock', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    cfg = read_json(args.config)
    validate_config(cfg)
    auth = read_json(args.authorization)
    check(auth['protocol_review'] == 'PROTOCOL_REVIEW_PASS' and
          auth['code_review'] == 'CODE_REVIEW_PASS' and
          auth['scope'] == 'fixed_prediction_scoring_only', 'execution review absent')
    check(auth['training_authorized'] is False, 'training must remain forbidden')
    code_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    check(auth['code_commit'] == code_commit, 'reviewed commit mismatch')
    check(not subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip(),
          'reviewed worktree must be clean')
    out = args.out.resolve()
    check(not out.exists(), 'output already exists')
    input_root = Path(cfg['input_root']).resolve()
    check(input_root not in out.parents and out not in input_root.parents, 'input/output overlap')
    start = time.monotonic()
    def timeout_handler(*_):
        raise TimeoutError('60 second cap')
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)
    original = {name: (input_root / name).read_bytes() for name in cfg['input_files']}
    groups = validate_inputs(input_root, cfg, args.source_data, read_json(args.data_lock))
    bs, ss = analyse(groups, cfg)
    summary = compact_summary(bs, ss, cfg)
    out.mkdir(parents=True)
    write_csv(out / 'bounds.csv', bs)
    write_csv(out / 'scenarios.csv', ss)
    # Plot the exact serialized scoring tables, not separately recomputed data.
    with (out / 'bounds.csv').open() as f:
        plot_b = [{k: (v if k in ['record', 'certified_M1_worse'] else float(v))
                   for k, v in r.items()} for r in csv.DictReader(f)]
    with (out / 'scenarios.csv').open() as f:
        plot_s = [{k: (v if k in ['record', 'scenario', 'sign'] else float(v))
                   for k, v in r.items()} for r in csv.DictReader(f)]
    plot_tables(plot_b, plot_s, out)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    text = readme(summary)
    (out / 'README_analysis.md').write_text(text)
    (out / 'label_sensitivity.md').write_text(text)
    for name, data in original.items():
        check((input_root / name).read_bytes() == data, 'source modified: ' + name)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mb = rss / (1024 ** 2 if sys.platform == 'darwin' else 1024)
    check(rss_mb <= 1024, 'observed peak RSS exceeds budget')
    receipt = {'run_id': 'S02-E005-R002', 'code_commit': code_commit,
        'source_run': cfg['source_run'], 'input_root': str(input_root),
        'out': str(out), 'hostname': socket.gethostname(), 'pid': os.getpid(),
        'python': sys.version, 'platform': platform.platform(), 'command': sys.argv,
        'elapsed_seconds': time.monotonic() - start, 'peak_rss_mb': rss_mb,
        'budget_enforcement': '60s wall-clock alarm; peak RSS checked after analysis/plot',
        'input_files_unchanged': True, 'training': False, 'fitting': False,
        'model_forward': False, 'execution_status': 'succeeded',
        'bounds_rows': len(bs), 'scenarios_rows': len(ss), 'authorization': auth}
    (out / 'execution_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    signal.alarm(0)
    print(json.dumps({'execution_status': 'succeeded', 'elapsed_seconds': receipt['elapsed_seconds'],
                      'result': {r: {k: v for k, v in info.items() if k != 'bounds'}
                                 for r, info in summary['result'].items()}}, indent=2))


if __name__ == '__main__':
    main()
