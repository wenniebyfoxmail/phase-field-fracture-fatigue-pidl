"""Check whether the boundary mean-step signal is also present before PT interpolation."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from analyse import write_json


def main(out):
    d = pd.read_csv(out/'all_chunk_boundary_source_pairs.csv')
    rows = []
    for r in d.to_dict('records'):
        a = np.loadtxt(r['csv_b'], skiprows=4)
        b = np.loadtxt(r['csv_a'], skiprows=4)
        _, ia, ib = np.intersect1d(a[:, 0], b[:, 0], return_indices=True)
        delta = a[ia, 4:6]-b[ib, 4:6]
        r['raw_shared_node_mean_shift_mm'] = float(np.abs(delta.mean(0)).mean())
        r['raw_shared_node_shape_shift_mm'] = float(np.abs(delta-delta.mean(0)).mean())
        # Same source node IDs, not a fit/registration and not material-point certification.
        rows.append(r)
    table = pd.DataFrame(rows)
    table.to_csv(out/'boundary_raw_vs_pt_source_pairs.csv', index=False)
    result = {}
    for name in ['mean_shift_mm', 'shape_shift_mm', 'raw_shared_node_mean_shift_mm', 'raw_shared_node_shape_shift_mm']:
        pp = table.pivot(index=['group', 'boundary_stage'], columns='kind', values=name)
        ratio = pp.boundary/np.maximum(pp.preceding_control, 1e-15)
        result[name] = {'median_boundary_over_control': float(ratio.median()),
                        'boundary_greater': int((pp.boundary > pp.preceding_control).sum()),
                        'pairs': len(pp), 'boundary_median': float(pp.boundary.median()),
                        'control_median': float(pp.preceding_control.median())}
    write_json(out/'boundary_raw_vs_pt_summary.json', result)
    print(result)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
