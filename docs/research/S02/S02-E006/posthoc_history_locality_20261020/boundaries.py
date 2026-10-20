"""Source-only adjacent chunk/reference check, never cross-boundary model scoring."""
import argparse
import csv
import time
from pathlib import Path
import numpy as np
import pandas as pd
from analyse import DATA, Fields, raw_pair, write_json


def main(out):
    start = time.monotonic()
    with (DATA/'pt_frame_inventory.csv').open() as f:
        inv = list(csv.DictReader(f))
    loader = Fields(inv)
    rows = []
    for group in sorted({r['group'] for r in inv}):
        ordered = sorted([r for r in inv if r['group'] == group], key=lambda r: int(r['stage']))
        for prev, now in zip(ordered, ordered[1:]):
            n = int(now['stage'])
            if now['pt_member'] == prev['pt_member']:
                continue
            assert int(prev['stage']) == n-1
            for label, a, b in [('boundary', n-1, n), ('preceding_control', n-10, n-9)]:
                if (group, a) not in loader.rows or (group, b) not in loader.rows:
                    rows.append(dict(group=group, boundary_stage=n, kind=label, status='control_unavailable'))
                    continue
                if label == 'preceding_control' and loader.rows[(group, a)]['pt_member'] != loader.rows[(group, b)]['pt_member']:
                    rows.append(dict(group=group, boundary_stage=n, kind=label, status='control_crosses_other_boundary'))
                    continue
                p, head, raw = raw_pair(group, b)
                pp, ph, old = raw_pair(group, a)
                shared, ix, iy = np.intersect1d(raw[:, 0], old[:, 0], return_indices=True)
                reference = (raw[ix, 1:4]-raw[ix, 4:7])-(old[iy, 1:4]-old[iy, 4:7])
                delta = loader.get(group, b).astype(float)-loader.get(group, a).astype(float)
                global_shift = float(np.abs(delta.mean((1, 2))).mean())
                shape_shift = float(np.abs(delta-delta.mean((1, 2), keepdims=True)).mean())
                rows.append(dict(group=group, boundary_stage=n, kind=label, stage_a=a, stage_b=b,
                                 status='finite', mean_shift_mm=global_shift, shape_shift_mm=shape_shift,
                                 id_jaccard=len(shared)/(len(raw)+len(old)-len(shared)),
                                 xyz_minus_u_median_mm=float(np.median(np.linalg.norm(reference, axis=1))),
                                 xyz_minus_u_p95_mm=float(np.percentile(np.linalg.norm(reference, axis=1), 95)),
                                 csv_a=str(pp), csv_b=str(p), header_a=ph[1].strip(), header_b=head[1].strip()))
                assert time.monotonic()-start < 600
    d = pd.DataFrame(rows)
    d.to_csv(out/'all_chunk_boundary_source_pairs.csv', index=False)
    comparisons = []
    for metric in ['mean_shift_mm', 'shape_shift_mm', 'xyz_minus_u_median_mm', 'id_jaccard']:
        p = d[d.status == 'finite'].pivot(index=['group', 'boundary_stage'], columns='kind', values=metric).dropna()
        p['boundary_minus_control'] = p.boundary-p.preceding_control
        p['boundary_over_control'] = p.boundary/np.maximum(p.preceding_control, 1e-15)
        p['metric'] = metric
        comparisons.append(p.reset_index())
    cc = pd.concat(comparisons, ignore_index=True)
    cc.to_csv(out/'boundary_matched_comparisons.csv', index=False)
    result = {'scope': 'source-pair diagnostic only; no new prediction or scoring',
              'pairs': len(d), 'boundary_pairs': int((d.kind == 'boundary').sum()),
              'status_counts': d.status.value_counts().to_dict(),
              'wall_seconds': time.monotonic()-start,
              'metrics': {m: {'matched_boundaries': len(t), 'median_pair_ratio': float(t.boundary_over_control.median()),
                              'boundary_greater_than_control': int((t.boundary_minus_control > 0).sum()),
                              'boundary_p95': float(t.boundary.quantile(.95)),
                              'boundary_max': float(t.boundary.max())}
                          for m, t in cc.groupby('metric')}}
    write_json(out/'boundary_summary.json', result)
    print(result)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
