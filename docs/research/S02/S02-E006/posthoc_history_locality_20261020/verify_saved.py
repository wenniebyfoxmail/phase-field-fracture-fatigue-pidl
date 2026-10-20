"""Separate Decimal aggregation from original archived score rows, no field/model calls."""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal, getcontext
from pathlib import Path
import pandas as pd
from analyse import SOURCE, read_json, write_json, identity


def main(out):
    getcontext().prec = 40
    sums, counts = defaultdict(Decimal), defaultdict(int)
    with (SOURCE/'per_case_scores.csv').open() as f:
        for r in csv.DictReader(f):
            key = (r['group'], int(r['horizon_stages']), r['arm'])
            sums[key] += Decimal(r['balanced_nmae'])
            counts[key] += 1
    summary = read_json(out/'summary.json')
    maxima = 0.
    for arm in ['H_INNOV', 'B_STAR', 'C_RAW']:
        values = [sums[k]/counts[k] for k in sums if k[2] == arm]
        assert len(values) == 38
        exact = sum(values)/38
        difference = abs(float(exact)-summary['overall'][arm])
        assert difference < 1e-12
        maxima = max(maxima, difference)
    df = pd.read_csv(out/'case_diagnostics.csv')
    assert len(df) == 2288 and df[['case_index', 'horizon']].drop_duplicates().shape[0] == 2288
    assert df.case_index.nunique() == 1144 and df.group.nunique() == 19
    offsets = pd.read_csv(out/'header_offset_summary.csv')
    assert offsets.groups_n.tolist() == [17, 8]
    contribution = pd.read_csv(out/'stage_net_contribution.csv')
    assert abs(contribution.weighted_gain.sum()-(summary['overall']['B_STAR']-summary['overall']['H_INNOV'])) < 1e-12
    group = df.groupby('group').gain_B_STAR.mean()
    bad = group[group < 0].index.tolist()
    assert len(bad) == 4 and all(g in bad for g in ['C_30Deg_20%_#1', 'C_30Deg_20%_#2', 'C_30Deg_20%_#3'])
    original = read_json(out/'source_identity.json')
    assert identity([Path(p) for p in original]) == original
    b = pd.read_csv(out/'all_chunk_boundary_source_pairs.csv')
    assert len(b) == 334 and b.status.eq('finite').all()
    assert not any(p.name.endswith('.pt') for p in out.iterdir())
    write_json(out/'verification.json', {'status': 'verified_descriptive_arithmetic',
               'original_score_Decimal_aggregation_max_abs': maxima,
               'native_score_reproduction_max_abs': summary['score_reproduction_max_abs'],
               'all_original_prediction_metadata_PT_identities_unchanged': True,
               'case_horizons': 2288, 'groups': 19, 'retained_negative_groups': bad,
               'zero_fits_and_forward': 'Source audit: scripts never access coefficients or import a training runner',
               'review_scope': 'Separate arithmetic and source-integrity check; not an external independent scientific review',
               'no_causal_or_physical_tip_validity_claim': True})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
