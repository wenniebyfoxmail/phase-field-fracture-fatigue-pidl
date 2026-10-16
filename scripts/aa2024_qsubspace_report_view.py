#!/usr/bin/env python3
"""Display saved E019-D01 ratios only; no producer imports or diagnostic arithmetic."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
from datetime import datetime, timezone

PROJECT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
REPO = PROJECT / '.codex/worktrees/s03-e016-geometry-alignment-20261013'
SOURCE = PROJECT / 'local_archive/experiments/S03-E019-D01/S03-E019-D01-R001/analysis/report.json'
DEST = PROJECT / 'local_archive/experiments/S03-E019-D01/S03-E019-D01-R001-V01'
SOURCE_SHA = 'f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689'
PLAN = REPO / 'docs/research/S03/S03-E019/subspace_display_plan.md'
PLAN_SHA = 'fa0a408e2b78c54b1160b83b4ece5cad91d698550e671f55fc5f9eea984737bb'
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')
CASE_KEYS = ('case', 'Q_identity_ratio', 'Q_identity_pass',
             'Q_identity_role', 'Q_identity_outcome')
ARTIFACTS = ('q_identity_ratio.png', 'q_identity_ratio.pdf',
             'q_identity_ratio.md', 'plot_values.json', 'render.log')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_bytes(path, expected):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'not a regular nonsymlink file: {path}')
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError(f'byte identity mismatch: {path}')
    return data


def reject_constant(value):
    raise ValueError(f'nonstandard JSON constant: {value}')


def select_values(report):
    """Copy only saved scalar/status fields; never access report evidence."""
    if report['domain'] != 'synthetic' or report['protocol_revision'] != 'E019-D01_v1.1':
        raise ValueError('report identity mismatch')
    if report['tolerances'] != dict(rtol=1e-12, matrix=1e-12, vector=1e-15, square=1e-18):
        raise ValueError('original tolerances changed')
    cases = report['cases']
    if not isinstance(cases, list) or [c['case'] for c in cases] != ['C0', 'C1', 'C2', 'C3']:
        raise ValueError('case order mismatch')
    copied = [{k: c[k] for k in CASE_KEYS} for c in cases]
    c0 = copied[0]
    if (c0['Q_identity_ratio'] is not None or c0['Q_identity_pass'] is not None or
            c0['Q_identity_role'] != 'not_applicable' or
            c0['Q_identity_outcome'] != 'no_y_p_r_in_C0'):
        raise ValueError('C0 must be not applicable, not zero')
    for c in copied[1:]:
        value = c['Q_identity_ratio']
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1e8:
            raise ValueError('saved ratio outside fixed display range')
        clean = c['case'] == 'C1'
        if (c['Q_identity_pass'] is not clean or
                c['Q_identity_role'] != ('clean_baseline' if clean else 'predeclared_negative_control') or
                c['Q_identity_outcome'] != ('passed' if clean else
                    'expected_not_passed_at_original_tolerance')):
            raise ValueError('saved role/outcome mismatch')
        if clean and value != 0:
            raise ValueError('C1 saved exact zero changed')
    return dict(domain=report['domain'], protocol_revision=report['protocol_revision'],
                tolerances=dict(report['tolerances']), cases=copied)


def contains(outer, inner, margin=0.0):
    return (outer[0] + margin <= inner[0] <= inner[2] <= outer[2] - margin and
            outer[1] + margin <= inner[1] <= inner[3] <= outer[3] - margin)


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check_boxes(boxes, markers, canvas, axes):
    for name, box in {**boxes, **markers}.items():
        if not all(math.isfinite(v) for v in box) or not contains(canvas, box, 2.0):
            raise ValueError(f'canvas safety margin failed: {name}')
    for name in ('value_C1', 'value_C2', 'value_C3'):
        if not contains(axes, boxes[name]):
            raise ValueError(f'numeric annotation outside axes: {name}')
        for other in ('title', 'subtitle', 'value_C1', 'value_C2', 'value_C3'):
            if other != name and intersects(boxes[name], boxes[other]):
                raise ValueError(f'annotation overlap: {name}/{other}')
    return dict(canvas=list(canvas), axes=list(axes), text_boxes=boxes,
                marker_boxes=markers, safety_pixels=2, passed=True)


def make_figure(values):
    # Heavy display imports are delayed; unit tests do not import the plotting stack.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.markers import MarkerStyle

    with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'text.usetex': False, 'figure.autolayout': False,
                         'figure.constrained_layout.use': False,
                         'savefig.bbox': None, 'pdf.fonttype': 42}):
        fig, ax = plt.subplots(figsize=(9.6, 5.4), dpi=170)
        try:
            fig.subplots_adjust(left=.16, right=.97, bottom=.22, top=.78)
            labels = {
                'title': fig.text(.5, .965, 'E019-D01 | R001 saved report | synthetic',
                                  ha='center', va='top', fontsize=11),
                'subtitle': fig.text(.5, .905,
                    'C2/C3: prescribed negative controls; zero SVD',
                    ha='center', va='top', fontsize=10),
            }
            ax.set_yscale('symlog', linthresh=1)
            ax.set_ylim(0, 1e8)
            ax.set_xlim(-.4, 2.4)
            ax.set_xticks([0, 1, 2], ['C1\nclean', 'C2\ninput perturbation',
                                     'C3\nfactor perturbation'])
            labels['ylabel'] = ax.set_ylabel('Q-identity error ratio\n(dimensionless)', fontsize=10)
            ax.axhline(1, color='black', linestyle='--', linewidth=1.2)
            labels['threshold'] = ax.annotate('Original tolerance = 1',
                xy=(.98, 1), xycoords=('axes fraction', 'data'), xytext=(0, 5),
                textcoords='offset points', ha='right', va='bottom', fontsize=9)
            marker_specs = []
            for i, case in enumerate(values['cases'][1:]):
                value = case['Q_identity_ratio']
                marker, color = ('o', '#0072B2') if i == 0 else ('x', '#D55E00')
                # Size and edge width are explicit, so full stroke extents are checkable.
                ax.scatter([i], [value], marker=marker, color=color, s=49,
                           linewidths=1.4, clip_on=(i != 0), zorder=4)
                marker_specs.append((case['case'], i, value, marker))
                labels['value_' + case['case']] = ax.annotate(
                    '0 (exact)' if i == 0 else format(value, '.5g'), (i, value),
                    xytext=(0, 10 if i == 0 else -18), textcoords='offset points',
                    ha='center', va='bottom' if i == 0 else 'top', fontsize=10)
            fig.canvas.draw()  # Single explicit layout evaluation; no diagnostic calculations.
            renderer = fig.canvas.get_renderer()
            labels.update({f'xtick_{i}': t for i, t in enumerate(ax.get_xticklabels()) if t.get_visible()})
            labels.update({f'ytick_{i}': t for i, t in enumerate(ax.get_yticklabels()) if t.get_visible()})
            if ax.yaxis.get_offset_text().get_text():
                labels['yoffset'] = ax.yaxis.get_offset_text()
            boxes = {k: list(v.get_window_extent(renderer).extents) for k, v in labels.items()}
            markers = {}
            for case, x, y, marker in marker_specs:
                style = MarkerStyle(marker)
                path_box = style.get_path().transformed(style.get_transform()).get_extents()
                center = ax.transData.transform((x, y))
                scale, stroke = math.sqrt(49) * fig.dpi / 72, 1.4 * fig.dpi / 144
                markers['marker_' + case] = [float(center[0] + path_box.x0 * scale - stroke),
                    float(center[1] + path_box.y0 * scale - stroke),
                    float(center[0] + path_box.x1 * scale + stroke),
                    float(center[1] + path_box.y1 * scale + stroke)]
            qa = check_boxes(boxes, markers, list(fig.bbox.extents), list(ax.bbox.extents))
            # C2/C3 remain clipped to axes; require their entire markers inside it.
            for case in ('C2', 'C3'):
                if not contains(qa['axes'], markers['marker_' + case]):
                    raise ValueError('nonzero marker would be clipped: ' + case)
            return fig, qa
        except BaseException:
            plt.close(fig)
            raise


def sidecar(values):
    rows = '\n'.join(f"- {c['case']}: {c['Q_identity_ratio']!r}; {c['Q_identity_outcome']}"
                     for c in values['cases'][1:])
    return f'''# How to read `q_identity_ratio`

## Figure question
Can the saved synthetic R001 Q-identity ratios and original tolerance be read without clipping or overlap?
This is a display derivative, not a new diagnostic.

## Data provenance
- Run: S03-E019-D01-R001; view: S03-E019-D01-R001-V01; synthetic only.
- Sole scalar input: {SOURCE}
- Input SHA256: {SOURCE_SHA}
- Plotting script: scripts/aa2024_qsubspace_report_view.py
- Same saved cases C1/C2/C3, with original roles/outcomes; C0 is not applicable, not zero.
- No new mapping, weighting, interpolation or diagnostic arithmetic. Ratios copied directly.

## Visual grammar
Horizontal axis: all three applicable cases in saved order. Vertical axis: dimensionless Q-identity error ratio,
symlog with linthresh=1 and fixed range [0,1e8]. Original ratio definition:
max_i (|(Qr-r)_i| / (atol_vector + rtol * |r_i|)); the plotted ratio is copied, not recomputed here.
Original tolerances: rtol=1e-12, vector atol=1e-15 mm, matrix atol=1e-12, square atol=1e-18 mm^2.
Blue circle: clean C1. Orange crosses: prescribed input/factor negative controls C2/C3.
Black dashed line at 1: original tolerance. Exact zero stays zero; its marker can cross the axis edge,
not the canvas edge. Numbers use saved precision in this note and .5g in the nonzero plot labels.

## Panel guide
One panel shows all applicable saved ratios, their labels and the unchanged criterion line.

## Key numerical takeaway
{rows}
C2/C3 are predeclared negative controls; their saved non-passing outcomes are retained, not a new failure.

## Limitations and claim boundary
Synthetic mechanism illustration only. Layout QA is not independent scalar-ledger acceptance,
not identification of the actual E019 root cause, and not physical/material inversion or prediction validity.
The original E019 and D01 numerical acceptance pauses remain in force. This derivative does not replace
or overwrite the original report, numbers, figures, producer code or execution receipt.

## Related assets
- Copied values/statuses: plot_values.json
- Display receipt: render_receipt.json
- Alternate format: q_identity_ratio.pdf / q_identity_ratio.png
- Decision note: docs/research/S03/S03-E019/subspace_results.md
'''


def write_new_json(path, payload):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')


def render_once(started, bindings):
    """Called by the separately approved launcher, with process-wide budget active."""
    if Path.cwd() != REPO or SOURCE.resolve() != SOURCE or DEST.resolve() != DEST:
        raise ValueError('fixed path/cwd or ancestor symlink mismatch')
    if any(os.environ.get(k) != '1' for k in THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('single-thread CPU environment mismatch')
    if (os.environ.get('MPLCONFIGDIR') != str(DEST / '.mplconfig') or
            os.environ.get('XDG_CACHE_HOME') != str(DEST / '.cache')):
        raise ValueError('display cache must live in fresh view directory')
    checked_bytes(PLAN, PLAN_SHA)
    data = checked_bytes(SOURCE, SOURCE_SHA)
    values = select_values(json.loads(data, parse_constant=reject_constant))
    # Fixed destination created exactly once, only after source/schema validation.
    DEST.mkdir(exist_ok=False)
    receipt = dict(status='running', operation='render_saved_report_only',
        view_id=DEST.name, source_report=str(SOURCE), source_before_sha256=SOURCE_SHA,
        plan_sha256=PLAN_SHA, sources_before_sha256=bindings, pid=os.getpid(),
        hostname=socket.gethostname(), cwd=str(Path.cwd()), python=sys.executable,
        start_utc=datetime.now(timezone.utc).isoformat(), budget_seconds=60,
        thread_environment={k: os.environ[k] for k in THREADS},
        scope='display only; original numerical acceptance remains paused')
    fig = None
    try:
        with (DEST / 'render.log').open('x', encoding='utf-8') as log:
            log.write('render_saved_report_only; one attempt; synthetic; no diagnostic recomputation\n')
        fig, receipt['layout_qa'] = make_figure(values)
        import matplotlib.pyplot as plt
        with plt.rc_context({'savefig.bbox': None, 'pdf.fonttype': 42}):
            with (DEST / 'q_identity_ratio.png').open('xb') as handle:
                fig.savefig(handle, format='png', dpi=170)
            with (DEST / 'q_identity_ratio.pdf').open('xb') as handle:
                fig.savefig(handle, format='pdf')
        plt.close(fig)
        fig = None
        with (DEST / 'q_identity_ratio.md').open('x', encoding='utf-8') as handle:
            handle.write(sidecar(values))
        write_new_json(DEST / 'plot_values.json', values)
        checked_bytes(SOURCE, SOURCE_SHA)
        for name, expected in bindings.items():
            checked_bytes(REPO / name, expected)
        receipt.update(source_after_sha256=SOURCE_SHA, sources_after_sha256=bindings,
                       artifacts_sha256={n: digest((DEST / n).read_bytes()) for n in ARTIFACTS},
                       elapsed_seconds=time.monotonic() - started,
                       end_utc=datetime.now(timezone.utc).isoformat(), status='rendered')
        if receipt['elapsed_seconds'] >= 60:
            raise TimeoutError('render exceeded 60 seconds')
        write_new_json(DEST / 'render_receipt.json', receipt)
        with (DEST / 'render_receipt.json').open(encoding='utf-8') as handle:
            if json.load(handle) != receipt:
                raise ValueError('new receipt readback mismatch')
        if time.monotonic() - started >= 60:
            raise TimeoutError('final receipt check exceeded 60 seconds')
    except BaseException as exc:
        if fig is not None:
            import matplotlib.pyplot as plt
            plt.close(fig)
        receipt.update(status='failed', error=repr(exc), outputs_role='forensic_only',
                       elapsed_seconds=time.monotonic() - started)
        # This is the NEW, not-yet-frozen view receipt; never the old execution receipt.
        with (DEST / 'render_receipt.json').open('w', encoding='utf-8') as handle:
            json.dump(receipt, handle, indent=2, allow_nan=False)
            handle.write('\n')
        raise


if __name__ == '__main__':
    raise SystemExit('Use the reviewed budget/identity launcher; no direct render CLI.')
