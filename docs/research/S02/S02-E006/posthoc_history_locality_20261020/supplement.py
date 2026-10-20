"""Additional descriptive arithmetic; no predictors, fits, or changes to scores."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from analyse import SOURCE, read_json, write_json, raw_pair


def run(out):
    df = pd.read_csv(out/'case_diagnostics.csv')
    raw = pd.read_csv(out/'raw_measurement_samples.csv')
    rows = []
    for r in raw.to_dict('records'):
        _, _, a = raw_pair(r['group'], r['origin_stage'])
        _, _, b = raw_pair(r['group'], r['origin_stage']-10)
        _, ia, ib = np.intersect1d(a[:, 0], b[:, 0], return_indices=True)
        # An explicit coordinate-semantic hypothesis, not a registered field or correction.
        dr = (a[ia, 1:4]-a[ia, 4:7])-(b[ib, 1:4]-b[ib, 4:7])
        r['xyz_minus_u_shared_id_median_difference_mm'] = float(np.median(np.linalg.norm(dr, axis=1)))
        r['xyz_minus_u_shared_id_p95_difference_mm'] = float(np.percentile(np.linalg.norm(dr, axis=1), 95))
        rows.append(r)
    pd.DataFrame(rows).to_csv(out/'raw_coordinate_semantic_probe.csv', index=False)
    # Balance nuisance strata by group x retained-stage-third x horizon, then compare only shared support.
    contrasts = []
    covariates = {'header_offset_flag': (0, 1), 'margin_bin': ('0-5', '>15'),
                  'threshold_range_px_third': (0, 2), 'past10_mean_shift_mm_third': (0, 2),
                  'current_roughness_ratio_third': (0, 2)}
    for col, (low, high) in covariates.items():
        for keys, adjustment in [(['group', 'horizon'], 'group_horizon'),
                                 (['group', 'stage_third', 'horizon'], 'group_stage_horizon')]:
            cells = df.groupby(keys+[col])[['gain_B_STAR', 'gain_C_RAW']].mean().reset_index()
            a = cells[cells[col] == low].set_index(keys)
            b = cells[cells[col] == high].set_index(keys)
            common = a.index.intersection(b.index)
            if len(common) == 0:
                continue
            diff = b.loc[common, ['gain_B_STAR', 'gain_C_RAW']]-a.loc[common, ['gain_B_STAR', 'gain_C_RAW']]
            bygroup = diff.groupby('group').mean()
            for comp in ['B_STAR', 'C_RAW']:
                contrasts.append(dict(proxy=col, adjustment=adjustment, high=str(high), low=str(low),
                                      comparator=comp, groups_n=len(bygroup), matched_cells=len(common),
                                      mean_high_minus_low_gain=float(bygroup['gain_'+comp].mean()),
                                      groups_positive=int((bygroup['gain_'+comp] > 0).sum())))
    pd.DataFrame(contrasts).to_csv(out/'matched_descriptive_contrasts.csv', index=False)
    # Exact contribution to the original group/horizon equal-weight mean (no equal-third substitution).
    df['cell_n'] = df.groupby(['group', 'horizon']).case_index.transform('count')
    df['weighted_gain'] = df.gain_B_STAR/df.cell_n/38.
    contribution = df.groupby('stage_third').weighted_gain.sum().reset_index()
    contribution['share_of_net_gain_pct'] = 100*contribution.weighted_gain/contribution.weighted_gain.sum()
    contribution.to_csv(out/'stage_net_contribution.csv', index=False)
    original = pd.read_csv(SOURCE/'per_case_scores.csv')
    join = original.merge(df[['case_index', 'horizon', 'stage_third']],
                          left_on=['case_index', 'horizon_stages'], right_on=['case_index', 'horizon'], validate='many_to_one')
    shape = []
    for third in range(3):
        d = join[(join.stage_third == third) & join.arm.isin(['B_STAR', 'C_RAW', 'H_INNOV'])]
        for ch in [0, 1]:
            for metric in ['mean_increment_error', 'centered_increment_nmae']:
                means = d.groupby(['group', 'horizon', 'arm'])[f'{metric}_{ch}'].mean().groupby('arm').mean()
                shape.append(dict(stage_third=third, channel=ch, diagnostic=metric,
                                  **{a: float(means[a]) for a in ['B_STAR', 'C_RAW', 'H_INNOV']},
                                  gain_B_STAR=float(means['B_STAR']-means['H_INNOV'])))
    pd.DataFrame(shape).to_csv(out/'stage_mean_shape_diagnostics.csv', index=False)
    group = df.groupby(['group', 'horizon'])[['gain_B_STAR', 'gain_C_RAW']].mean().groupby('group').mean()
    loo = {comp: [float(group.drop(g)['gain_'+comp].mean()) for g in group.index]
           for comp in ['B_STAR', 'C_RAW']}
    supplement = {'raw_coordinate_samples': len(rows), 'matched_contrasts': contrasts,
                  'stage_net_contribution': contribution.to_dict('records'),
                  'leave_one_release_group_out_gain_ranges': {c: [min(x), max(x)] for c, x in loo.items()},
                  'interpretation': 'Matched associations only; shared support and residual stage confounding remain. x-u is a tested semantic hypothesis, never a source correction.'}
    write_json(out/'supplement_summary.json', supplement)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
