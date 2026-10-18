"""Enlarge R001 raw CSV nodes for joint inspection, outside formal annotation."""
from pathlib import Path
import argparse
import json
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(base):
    packet = base / 'measurement_review_packet'
    protected = {p: p.read_bytes() for p in [packet / 'blank_measurements.csv',
                 packet / 'INTERNAL_source_key.json', packet / 'R001.png']}
    row, = [r for r in json.loads(protected[packet / 'INTERNAL_source_key.json'])
            if r['item_id'] == 'R001']
    source = Path(row['raw_file'])
    a = np.loadtxt(source, skiprows=4)
    fields = torch.load(base / 'pt_extracted' / row['pt_member'],
                        map_location='cpu', weights_only=True)
    pt = fields[row['pt_list_index']].numpy()[0, 1]
    # Reproduce exactly the common colour limits of the existing R001 packet.
    lo, hi = np.nanpercentile(np.r_[a[:, 5], pt.ravel()], [1, 99])
    windows = [(-2, 40, 43, 57), (8, 28, 47, 52.5)]
    titles = ['A. Left-side region around y = 50 mm',
              'B. Closer view of the transition (same raw points)']
    fig, axes = plt.subplots(2, 1, figsize=(12, 7.2), layout='constrained',
                             gridspec_kw={'height_ratios': [1.3, 1]})
    counts = []
    for ax, (xmin, xmax, ymin, ymax), title in zip(axes, windows, titles):
        sel = ((a[:, 1] >= xmin) & (a[:, 1] <= xmax)
               & (a[:, 2] >= ymin) & (a[:, 2] <= ymax))
        counts.append(int(sel.sum()))
        im = ax.scatter(a[sel, 1], a[sel, 2], c=a[sel, 5], s=27,
                        cmap='viridis', vmin=lo, vmax=hi, edgecolors='none')
        ax.set(xlim=(xmin, xmax), ylim=(ymin, ymax), aspect='equal', title=title,
               xlabel='Published CSV x / mm', ylabel='Published CSV y / mm')
        ax.tick_params(labelsize=11)
    cb = fig.colorbar(im, ax=axes, shrink=.8, fraction=.025, pad=.03, extend='both')
    cb.set_label('Published displacement_y / mm')
    fig.suptitle('R001 | Joint inspection only; excluded from formal remeasurement\n'
                 'Raw CSV nodes; no interpolation or smoothing; original R001 colour limits', fontsize=13)
    out = base / 'joint_inspection_R001_20261018'
    out.mkdir(exist_ok=True)
    fig.savefig(out / 'R001_raw_zoom.png', dpi=200)
    plt.close(fig)
    for p, before in protected.items():
        assert p.read_bytes() == before
    receipt = dict(item_id='R001', status='JOINT_INSPECTION_ONLY', source=str(source),
                   windows_xy_mm=windows, points_per_window=counts,
                   original_R001_colour_limits_mm=[float(lo), float(hi)],
                   interpolation=False, smoothing=False, formal_measurement=False,
                   endpoints_recorded=False, formal_files_unchanged=True,
                   future_frames=False, author_labels=False, training=False,
                   blinding_note='R001 has been discussed with AI assistance; do not describe a later R001 annotation as wholly blind to that assistance.')
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (out / 'R001_raw_zoom.md').write_text(f'''# How to read R001_raw_zoom.png

## Figure question
Does enlarging the left-side region near y=50 mm reveal a uniquely visible
right endpoint? This is joint visual inspection, not formal remeasurement.

## Data provenance
Item R001 uses the same current raw CSV as the original packet: `{source}`.
Source identity is retained here for provenance; repeat mappings are not shown.
Plotting script: docs/research/S02/S02-E006/plot_mendeley_joint_zoom.py.
The published PT channel is loaded only to reproduce the original R001 colour
limits, not to interpolate or select an endpoint. No future frames or author
lengths are used; no temporal interpretation of the source index is asserted.

## Visual grammar and panel guide
Axes are published CSV x/y in mm. Every dot is an original node; white spaces
between dots are sampling gaps and do not themselves imply a crack.
Colours represent displacement_y in source mm, shared across both panels and
the original R001 view: {lo:.6g} to {hi:.6g}, the original 1/99 percentile limits.
Colourbar triangles denote saturated values. Spatial aspect ratios are equal.
Panel A crops x=-2..40, y=43..57 mm; panel B crops x=8..28, y=47..52.5 mm.
There is no fitted line, endpoint marker, interpolation, sharpening or smoothing.

## Key numerical takeaway
Panels contain {counts[0]} and {counts[1]} raw nodes, respectively. Zooming only
enlarges their display; it adds no spatial samples. No tip coordinate or length
is recorded or scored, and no pass/fail claim is made.

## Limitations and claim boundary
A fading displacement contrast does not certify a physical crack tip or a
calibrated endpoint uncertainty. Joint discussion is excluded from formal human
remeasurement. R001 is now exposed to AI-assisted discussion; subsequent human
results must not be described as completely blind to that assistance.
The formal packet image, blank template and source key remain byte-identical.
No fitting, training or model retuning is performed.
''')
    print(json.dumps({k:v for k,v in receipt.items() if k != 'source'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base', type=Path)
    main(parser.parse_args().base)
