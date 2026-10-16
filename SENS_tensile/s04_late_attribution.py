"""9984226 scalar-only diagnostic engine. No producer, model or archive loader.

The pure functions consume already supplied scalar rows. There is intentionally
no real-data CLI: its exact four-source adapter and execution card require a
separate approved step. Engineering checks use only generated CSV strings.
"""
import csv
import io
import json
import math
from pathlib import Path

COUNTS = dict(u011=121, u0115=99, u012=82, u013=55)
FIELDS = ('holdout', 'cycle', 'stratum', 'cycle_weight',
          'V0_physical_mse', 'V1_physical_mse')
KNOWN_REAL_RATIO = 1.0160831289564436
PLAN_COMMIT = '9984226de5eb659b9ed6f82803a22c91a92e5f82'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(value, label):
    value = float(value)
    require(math.isfinite(value), 'nonfinite '+label)
    return value


def parse_csv(text):
    """Parse supplied TEXT, never a path. Only six authorised scalar columns."""
    reader = csv.DictReader(io.StringIO(text))
    require(reader.fieldnames is not None and
            len(reader.fieldnames) == len(set(reader.fieldnames)) and
            set(FIELDS) <= set(reader.fieldnames), 'missing/duplicate CSV fields')
    rows = []
    for row in reader:
        require(None not in row and all(row[k] is not None for k in FIELDS),
                'malformed CSV row')
        rows.append({k: row[k] for k in FIELDS})
        require(len(rows) <= 357, 'excess rows')
    return rows


def validate(rows):
    require(len(rows) == 357, '357 rows required')
    parsed = {}
    for row in rows:
        require(set(FIELDS) <= set(row), 'missing row fields')
        key = row['holdout']
        require(key in COUNTS, 'undeclared holdout')
        cycle = int(row['cycle'])
        require(str(cycle) == str(row['cycle']), 'noninteger cycle')
        require(1 <= cycle <= COUNTS[key], 'cycle outside complete prefix')
        stratum = min((cycle-1)//20, 2)
        require(str(stratum) == str(row['stratum']), 'wrong stratum')
        n = 20 if stratum < 2 else COUNTS[key]-40
        weight = finite(row['cycle_weight'], 'weight')
        require(abs(weight-1/(3*n)) < 1e-16, 'original cycle weight changed')
        m0 = finite(row['V0_physical_mse'], 'V0 MSE')
        m1 = finite(row['V1_physical_mse'], 'V1 MSE')
        require(m0 >= 0 and m1 >= 0, 'negative MSE')
        require((key, cycle) not in parsed, 'duplicate state key')
        parsed[key, cycle] = (m0, m1)
    require(set(parsed) == {(k, c) for k, n in COUNTS.items()
                            for c in range(1, n+1)}, 'incomplete prefix')
    return [dict(cycle=c, V0_physical_mse=parsed['u011', c][0],
                 V1_physical_mse=parsed['u011', c][1]) for c in range(41, 122)]


def describe(rows, expected_ratio):
    """Expected ratio must come from approved source binding, or a toy oracle.

    No default real reference prevents a generated result from masquerading as
    a verification of the known real value. All 357 rows are validated; only
    U0.11 C41..121 are decomposed. No other fold means or R/G/Q are recomputed.
    """
    late = validate(rows)
    m0 = math.fsum(r['V0_physical_mse']/81 for r in late)
    m1 = math.fsum(r['V1_physical_mse']/81 for r in late)
    require(m0 > 1e-24, 'unidentifiable late baseline')
    # sqrt separately avoids overflow in m1/m0; no denominator floor.
    ratio = math.sqrt(m1)/math.sqrt(m0)
    expected_ratio = finite(expected_ratio, 'reference ratio')
    require(expected_ratio >= 0 and math.isfinite(ratio) and
            abs(ratio-expected_ratio) <= 1e-12, 'known late ratio disagreement')
    for row in late:
        d = row['V1_physical_mse']-row['V0_physical_mse']
        tau = 1e-10+1e-10*abs(row['V0_physical_mse'])
        row.update(D=d, tau=tau, positive_excess=max(d, 0.),
                   numeric_class='harm' if d > tau else 'improve' if d < -tau else 'tie')
    plus = math.fsum(r['positive_excess'] for r in late)
    minus = math.fsum(max(-r['D'], 0.) for r in late)
    net = plus-minus
    tolerance = math.fsum(r['tau'] for r in late)
    require(all(math.isfinite(v) for v in (plus, minus, net, tolerance)),
            'nonfinite sum')
    require(abs(net-math.fsum(r['D'] for r in late)) <= tolerance,
            'MSE decomposition closure')
    counts = {k: sum(r['numeric_class'] == k for r in late)
              for k in ('harm', 'improve', 'tie')}
    require(sum(counts.values()) == 81, 'count closure')
    ranked = sorted(late, key=lambda r: (-r['positive_excess'], r['cycle']))
    identifiable = plus > tolerance
    k50 = None
    cumulative = []
    if identifiable:
        for i in range(81):
            cumulative.append(math.fsum(r['positive_excess'] for r in ranked[:i+1])/plus)
            if k50 is None and math.fsum(r['positive_excess'] for r in ranked[:i+1]) >= .5*plus:
                k50 = i+1
    main_cycles = [] if k50 is None else [r['cycle'] for r in ranked[:k50]]
    if k50 is None:
        branch = 'STOP_UNIDENTIFIABLE_POSITIVE_EXCESS'
    elif k50 == 1:
        branch = 'PROPOSE_SINGLE_STATE_PROVENANCE_CHECK'
    elif counts['harm'] >= 41:
        branch = 'PROPOSE_PHASE_OBJECTIVE_REPRESENTATION_QUESTIONS'
    else:
        branch = 'PROPOSE_CONTRIBUTING_STATES_PROVENANCE_CHECK'
    maximum = next((r for r in ranked if r['D'] > 0), None)
    summary = dict(status='DESCRIPTIVE_ONLY' if identifiable else 'INCONCLUSIVE',
                   plan_commit=PLAN_COMMIT, holdout='u011', cycles=[41, 121], n=81,
                   state='nominal-peak s4 post-history', horizon=0,
                   units='raw archive units squared', S_plus=plus, S_minus=minus,
                   S_net=net, late_mean_MSE_difference=net/81, sum_tau=tolerance,
                   late_RMSE_ratio=ratio, expected_ratio=expected_ratio, k50=k50,
                   k50_over_81=None if k50 is None else k50/81,
                   contributing_cycles=main_cycles, counts=counts,
                   count_fractions={k: v/81 for k, v in counts.items()}, branch=branch,
                   max_positive=None if maximum is None else
                   dict(cycle=maximum['cycle'], D=maximum['D']),
                   C121_provenance_check_proposed=121 in main_cycles,
                   source_identity='SUPPLIED_ROWS_NOT_AUTHENTICATED_BY_ENGINE',
                   blocked=['physical cause', 'gradient conflict', 'spatial support',
                            'NN necessity', 'new weights', 'confirmation generalisation'],
                   fitting_invoked=False)
    return late, summary, cumulative


def report(late, summary, cumulative, out, *, generated):
    """Output only into a fresh caller-owned directory; no source mutation."""
    require(generated is True, 'real report requires separately reviewed source adapter')
    out = Path(out)
    out.mkdir(exist_ok=False)
    summary = dict(summary, evidence_domain='GENERATED ENGINEERING ONLY',
                   real_data_read=False)
    with (out/'diagnostic.csv').open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(late[0]))
        writer.writeheader()
        writer.writerows(late)
    with (out/'summary.json').open('x') as file:
        json.dump(summary, file, indent=2, allow_nan=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), constrained_layout=True)
    a, b = axes
    a.bar([r['cycle'] for r in late], [r['D'] for r in late],
          color=['#b35806' if r['D'] > 0 else '#2166ac' for r in late], width=.85)
    a.axhline(0, color='black', lw=1)
    a.set(xlabel='Physical cycle (all 81)', ylabel='V1 MSE - V0 MSE\n(raw archive units squared)',
          title='A | Signed MSE difference; zero = V1 equals V0')
    if cumulative:
        b.step(range(1, 82), cumulative, where='post', color='#336d8b')
        b.axhline(.5, color='gray', ls='--', lw=1)
        b.axvline(summary['k50'], color='#b35806', ls=':', lw=1)
        b.text(.98, .08, 'k50 = '+str(summary['k50'])+'/81',
               transform=b.transAxes, ha='right')
    else:
        b.text(.5, .5, 'Positive excess unidentifiable\nNo denominator floor; stop',
               transform=b.transAxes, ha='center')
    b.set(xlabel='Rank (positive excess descending; ties: cycle ascending)',
          ylabel='Cumulative share of S_plus', ylim=(0, 1.03),
          title='B | 50% definition, not a success threshold')
    fig.suptitle('GENERATED ENGINEERING ONLY — U0.11 C41–121 | s4 / horizon 0\n'
                 'Development-layout fixture; descriptive error localisation, NOT physical attribution',
                 fontsize=10)
    fig.savefig(out/'diagnostic.png', dpi=120)
    plt.close(fig)
    with (out/'README_analysis.md').open('x') as file:
        file.write('# Generated small-table engineering check\n\n'
                   'Source: generated six-column CSV string; NO real data read. '
                   'Mirrors viewed synthetic-development layout, not its values.\n'
                   'Read diagnostic.csv, summary.json, then panels A and B. All 81 cycles retained.\n'
                   'D = m1-m0; S_plus = sum(max(D,0)); S_minus = sum(max(-D,0)); '
                   'S_net = S_plus-S_minus; late mean = S_net/81. Original full-stratum '
                   'weight 1/(3*81) is NOT used for this mean. Units: raw archive units squared.\n'
                   'Rank positive excess descending, exact ties by ascending cycle; '
                   'k50 is the minimum count reaching half S_plus. Report improvement '
                   'offsets and all harm/improve/tie counts alongside it.\n'
                   'Engineering behaviour only; no actual late-contribution result, physical '
                   'cause, independent samples, gradient conflict, new weights or NN necessity. '
                   'RMSE percentages are not additively attributable to cycles.\n')


if __name__ == '__main__':
    raise SystemExit('No real-data entry point. Separate source adapter, review and run approval required.')
