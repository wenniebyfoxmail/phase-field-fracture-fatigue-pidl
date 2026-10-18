#!/usr/bin/env python3
"""F01 synthetic display only. Separate approval is required to run this CLI.

No numerical acceptance, factorisation, Matplotlib or historical completion.
"""
import time
START = time.monotonic()

import argparse
from contextlib import contextmanager
import hashlib
import importlib.abc
import json
import math
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import warnings
import xml.etree.ElementTree as ET
from unittest.mock import patch

from aa2024_runtime_guard import install_cli

GUARD = install_cli() if __name__ == '__main__' else None
BLOCKED_IMPORTS = ('matplotlib', 'scipy', 'aa2024_q_recheck', 'aa2024_q_verify')


class Stop(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


class ImportFence(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name+'.') for name in BLOCKED_IMPORTS):
            raise Stop('forbidden import: '+fullname)
        return None


def install_fence():
    require(not any(name == root or name.startswith(root+'.')
                    for name in sys.modules for root in BLOCKED_IMPORTS), 'forbidden module already loaded')
    fence = ImportFence()
    sys.meta_path.insert(0, fence)
    return fence


if __name__ == '__main__':
    warnings.simplefilter('error')
    install_fence()
import numpy as np

ARMS = ('old', 'proxy', 'intact')
KEYS = ('source_xy', 'scale', 'r', 'old_r', 'proxy_r', 'intact_r')
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS')
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments')
INPUT = BASE/'S03-E019-D03/S03-E019-D03-B003'
OUTPUT = BASE/'S03-E019-D03-F01/S03-E019-D03-F01-V001'
CODE = ('aa2024_saved_svg.py', 'test_aa2024_saved_svg.py', 'aa2024_runtime_guard.py')
NOTICE = 'SYNTHETIC DISPLAY ONLY | B003 INCOMPLETE / UNACCEPTED | no numerical acceptance'
FACTOR_APIS = ('qr', 'svd', 'solve', 'lstsq', 'pinv', 'eig', 'eigh', 'cholesky',
               'eigvals', 'eigvalsh', 'inv', 'tensorinv', 'tensorsolve', 'matrix_rank', 'cond', 'norm', 'det', 'slogdet')
# Explicit eleven-stop RGB display interpolation, not Matplotlib pixel equivalence.
COLORS = ('#053061', '#2166ac', '#4393c3', '#92c5de', '#d1e5f0', '#f7f7f7',
          '#fddbc7', '#f4a582', '#d6604d', '#b2182b', '#67001f')


def guard(phase=None, _expected=GUARD):
    if _expected is not None:
        if GUARD is not _expected:
            _expected.fatal('display_guard_reference_lost')
        _expected.check(phase)


class Budget:
    def __init__(self, start=START, clock=time.monotonic):
        self.start, self.clock = start, clock

    def remaining(self):
        guard()
        seconds = 60-(self.clock()-self.start)
        if seconds <= 0:
            raise TimeoutError('F01 entire display soft60s incomplete; no retry')
        return seconds

    def check(self):
        self.remaining()


def forbidden(*args, **kwargs):
    raise Stop('factorisation/solve forbidden in display')


@contextmanager
def numerical_fence():
    from contextlib import ExitStack
    with ExitStack() as stack:
        for name in FACTOR_APIS:
            stack.enter_context(patch.object(np.linalg, name, side_effect=forbidden))
        stack.enter_context(np.errstate(all='raise'))
        yield


def safe_path(path, *, regular=False):
    path = Path(path)
    require(path.is_absolute(), 'absolute path required')
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'symlink forbidden: '+str(part))
    if regular:
        require(stat.S_ISREG(path.stat().st_mode), 'regular file required')


def digest(path, budget):
    safe_path(path, regular=True)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            budget.check()
            h.update(block)
    budget.check()
    return h.hexdigest()


def git(repo, budget, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True,
                                   timeout=budget.remaining()).strip()


def identity(repo, source, budget):
    head = git(repo, budget, 'rev-parse', 'HEAD')
    require(not git(repo, budget, 'status', '--porcelain'), 'clean tree required')
    git(repo, budget, 'merge-base', '--is-ancestor', source, head)
    changed = git(repo, budget, 'diff', '--name-only', source, head).splitlines()
    require(all(name.startswith('docs/') for name in changed), 'only later docs allowed')
    hashes = {name: digest(Path(__file__).with_name(name), budget) for name in CODE}
    return head, hashes


def input_fingerprints(root, budget):
    require(root == INPUT, 'exact unaccepted synthetic B003 input required')
    result = {}
    for name in ('certificate.npz', 'report.json'):
        path = root/name
        safe_path(path, regular=True)
        before = path.stat()
        value = digest(path, budget)
        after = path.stat()
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'input changed during hash')
        result[name] = dict(sha256=value, bytes=after.st_size,
                            device=after.st_dev, inode=after.st_ino, mtime_ns=after.st_mtime_ns)
    return result


def load_members(path, loader=None):
    # No enumeration or decoding of other NPZ members.
    if loader is None:
        loader = np.load
    with loader(path, allow_pickle=False) as container:
        return {name: container[name] for name in KEYS}


def permissions(source, output, authorized):
    require(authorized is True and source == INPUT and output == OUTPUT,
            'explicit exact synthetic-only input/output authority required')


def strict_json(text):
    def bad_constant(value):
        raise Stop('nonfinite JSON constant: '+value)
    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, 'duplicate JSON key')
            obj[key] = value
        return obj
    return json.loads(text, parse_constant=bad_constant, object_pairs_hook=unique_pairs)


def prepare(arrays, report, *, points=648):
    require(set(arrays) == set(KEYS), 'exact selected array keys')
    for name in KEYS:
        value = arrays[name]
        expected = (points, 2) if name == 'source_xy' else (2*points,)
        require(isinstance(value, np.ndarray) and value.dtype == np.dtype('float64') and
                value.shape == expected and np.isfinite(value).all(), 'array contract '+name)
    require(np.all(arrays['scale'] > 0), 'strictly positive scale')
    xy = arrays['source_xy']
    require(float(np.max(xy[:, 0])) > float(np.min(xy[:, 0])) and
            float(np.max(xy[:, 1])) > float(np.min(xy[:, 1])), 'two-dimensional coordinate extent')
    require(isinstance(report, dict) and report.get('schema') == 'E019-D03-U01-v1', 'saved report schema')
    rows = report.get('rows')
    require(isinstance(rows, list) and len(rows) == 3, 'three saved rows')
    display_rows = []
    for arm, row in zip(ARMS, rows):
        require(isinstance(row, dict) and row.get('arm') == arm, 'saved row order')
        values = {}
        for key in ('J_Q_mm2', 'gap2_mm2', 'J_k_mm2'):
            number = row.get(key)
            require(type(number) in (int, float) and math.isfinite(number) and number >= 0,
                    'nonnegative finite saved scalar '+key)
            values[key] = float(number)
        require(math.isfinite(values['J_Q_mm2']+values['gap2_mm2']), 'display stack overflow')
        display_rows.append(dict(arm=arm, **values))
    require(all(row['J_Q_mm2'] == display_rows[0]['J_Q_mm2'] for row in display_rows), 'one saved J_Q across arms')
    # Display-only division. No Q, projection, Gram, norm, or square ledger recomputation.
    maps = [(arrays[key]/arrays['scale']).reshape(points, 2) for key in ('r', 'old_r', 'proxy_r', 'intact_r')]
    require(all(np.isfinite(value).all() for value in maps), 'display division finite')
    bound = max(float(np.max(np.abs(value))) for value in maps)
    return dict(xy=xy, maps=maps, bound=bound or 1e-15, zero_range=(bound == 0), rows=display_rows)


def color(value, bound):
    require(math.isfinite(value) and math.isfinite(bound) and bound > 0 and abs(value) <= bound,
            'colour input range')
    fraction = max(0., min(1., (value/bound+1)/2))
    location = fraction*10
    index = min(9, int(location)); offset = location-index
    a, b = COLORS[index], COLORS[index+1]
    rgb = [round(int(a[k:k+2], 16)*(1-offset)+int(b[k:k+2], 16)*offset) for k in (1, 3, 5)]
    return '#'+''.join(format(v, '02x') for v in rgb)


def element(parent, tag, text=None, **attrs):
    obj = ET.SubElement(parent, tag, {key.replace('_', '-'): str(val) for key, val in attrs.items()})
    if text is not None:
        obj.text = str(text)
    return obj


def text(parent, x, y, value, size=14, anchor='start'):
    return element(parent, 'text', value, x=x, y=y, font_size=size, text_anchor=anchor)


def canvas(width, height, title, provenance):
    root = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg', 'viewBox': f'0 0 {width} {height}',
                              'width': str(width), 'height': str(height), 'role': 'img',
                              'font-family': 'sans-serif', 'font-size': '14'})
    element(root, 'title', title)
    element(root, 'desc', NOTICE+'; viewer fonts/layout not visually accepted; SVG only')
    element(root, 'metadata', json.dumps(provenance, sort_keys=True, allow_nan=False))
    element(root, 'rect', x=0, y=0, width=width, height=height, fill='white')
    text(root, 40, 35, title, 22)
    text(root, 40, 65, NOTICE, 15)
    return root


def residual_svg(data, provenance, budget):
    root = canvas(1460, 730, 'F01 | all 648 synthetic points | deweighted saved residuals [mm]', provenance)
    xy, bound = data['xy'], data['bound']
    xmin, xmax = float(np.min(xy[:, 0])), float(np.max(xy[:, 0]))
    ymin, ymax = float(np.min(xy[:, 1])), float(np.max(xy[:, 1]))
    factor = min(260/(xmax-xmin), 150/(ymax-ymin))
    require(math.isfinite(factor), 'display coordinate scale')
    text(root, 40, 95, 'Display only: D^-1 r; identical coordinates, equal aspect, shared symmetric colour range.')
    for row, component in enumerate(('U', 'V')):
        for col, name in enumerate(('Q retained',)+ARMS):
            budget.check()
            left, top = 90+300*col, 150+245*row
            width, height = (xmax-xmin)*factor, (ymax-ymin)*factor
            element(root, 'rect', x=left+(260-width)/2, y=top+(150-height)/2,
                    width=width, height=height, fill='none', stroke='#555555')
            text(root, left+130, top-18, name+' / '+component, 16, 'middle')
            for i, ((x, y), values) in enumerate(zip(xy, data['maps'][col])):
                value = float(values[row])
                sx = left+130+(float(x)-(xmin+xmax)/2)*factor
                sy = top+75-(float(y)-(ymin+ymax)/2)*factor
                require(math.isfinite(sx) and math.isfinite(sy), 'finite SVG coordinate')
                element(root, 'circle', cx=format(sx, '.9g'), cy=format(sy, '.9g'), r=2.1,
                        fill=color(value, bound), data_panel=f'{row}:{col}', data_point=i,
                        data_mm=repr(value), data_x_mm=repr(float(x)), data_y_mm=repr(float(y)))
            for value, loc in ((xmin, left+130-(xmax-xmin)*factor/2), (xmax, left+130+(xmax-xmin)*factor/2)):
                text(root, loc, top+172, format(value, '.4g'), 12, 'middle')
            text(root, left+130, top+195, 'synthetic x [mm]', 13, 'middle')
            text(root, left-12, top+(150-height)/2+5, format(ymax, '.4g'), 12, 'end')
            text(root, left-12, top+(150+height)/2+5, format(ymin, '.4g'), 12, 'end')
            text(root, left, top+218, 'synthetic y [mm]; positive upwards', 12)
    for i in range(100):
        value = bound*(1-2*(i+.5)/100)
        element(root, 'rect', x=1330, y=155+i*3.2, width=22, height=3.3, fill=color(value, bound))
    text(root, 1320, 135, '[mm]', 13)
    text(root, 1360, 162, format(bound, '.4g'), 12)
    text(root, 1360, 320, '0', 12)
    text(root, 1360, 475, format(-bound, '.4g'), 12)
    if data['zero_range']:
        text(root, 40, 665, 'All values zero: +/-1e-15 mm is a display-only range, not a numerical tolerance.')
    text(root, 40, 695, 'No smoothing, interpolation, selection, model fitting or numerical acceptance. Viewer fonts may differ.')
    return ET.tostring(root, encoding='unicode', xml_declaration=False)


def ledger_svg(data, provenance, budget):
    root = canvas(1020, 660, 'F01 | saved square ledger [mm^2] | synthetic only', provenance)
    rows = data['rows']
    peak = max(max(row['J_Q_mm2']+row['gap2_mm2'], row['J_k_mm2']) for row in rows)
    ceiling = peak or 1e-18
    text(root, 40, 100, 'Saved scalars only: blue J_Q + orange gap^2; black dot J_k. No ledger recomputation.')
    element(root, 'path', d='M 100 150 L 100 480 L 900 480', fill='none', stroke='#333333')
    for tick in range(5):
        y = 480-tick*75
        text(root, 85, y+5, format(ceiling*tick/4, '.4g'), 13, 'end')
    for col, row in enumerate(rows):
        budget.check()
        center = 260+240*col
        floor = 300*(row['J_Q_mm2']/ceiling)
        gap = 300*(row['gap2_mm2']/ceiling)
        element(root, 'rect', x=center-40, y=480-floor, width=80, height=floor, fill='#0072B2',
                data_arm=row['arm'], data_quantity='J_Q_mm2', data_value=repr(row['J_Q_mm2']))
        element(root, 'rect', x=center-40, y=480-floor-gap, width=80, height=gap, fill='#E69F00',
                data_arm=row['arm'], data_quantity='gap2_mm2', data_value=repr(row['gap2_mm2']))
        element(root, 'circle', cx=center, cy=480-300*(row['J_k_mm2']/ceiling), r=5, fill='black',
                data_arm=row['arm'], data_quantity='J_k_mm2', data_value=repr(row['J_k_mm2']))
        text(root, center, 510, row['arm'], 16, 'middle')
    text(root, 100, 135, 'weighted squared residual [mm^2]', 14)
    text(root, 100, 550, 'Blue: J_Q     Orange: gap^2     Black dot: J_k', 16)
    if not peak:
        text(root, 100, 580, 'All saved scalars zero: 1e-18 mm^2 is an axis range only, not a tolerance.')
    text(root, 40, 620, 'Squares are shown stacked; RMS is not added. Values and historical B003 completion remain unverified.')
    return ET.tostring(root, encoding='unicode', xml_declaration=False)


def sidecar(stem, provenance, data):
    guide = ('U/V rows; Q retained then old/proxy/intact columns. All 648 points, equal aspect, positive y upwards. '
             'Shared symmetric eleven-stop RdBu_r-style RGB interpolation; deweighting is display only. '
             f'Colour half-range {data["bound"]!r} mm; zero-range flag {data["zero_range"]}.') if stem == 'residuals' else (
             'Three arms: blue J_Q with orange gap^2 stacked above, black dots saved J_k, units mm^2. '
             'Squares add visually, RMS does not. No recalculated ledger or error allocation.')
    return ('# '+stem+'\n\n## Figure question\n\nCan saved, unaccepted synthetic values be displayed without factorisation or font-manager import?\n\n'
            '## Data provenance\n\n'+json.dumps(provenance, indent=2, allow_nan=False)+
            '\n\n## How to read / Visual grammar / Panel guide\n\n'+guide+
            '\n\n## Key numerical takeaway\n\nSaved scalar rows only, not independently recomputed:\n\n'+
            json.dumps(data['rows'], indent=2, allow_nan=False)+
            '\n\n## Limitations and claim boundary\n\nB003 remains incomplete. Current hashes do not authenticate its historical generation. '
            'No numerical acceptance, physical inversion, prediction, phase-field identification or real-data access. '
            'SVG-only, not a pixel-equivalent Matplotlib PNG/PDF. Text uses viewer fonts; layout and font appearance await separate visual QA. '
            'No caching, interpolation or smoothing. Existing tolerances are not changed or evaluated.\n\n'
            '## Related assets\n\nSame-directory derived_receipt.json; source files in provenance; no producer receipt recreated.\n')


def exclusive_text(path, value, budget):
    budget.check(); guard('display_write')
    safe_path(path)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value)
    budget.check()


def main():
    budget = Budget(); budget.check()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-unaccepted-synthetic', action='store_true')
    args = parser.parse_args()
    permissions(args.input, args.output, args.allow_unaccepted_synthetic)
    require(all(os.environ.get(key) == '1' for key in THREADS) and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'single CPU environment')
    repo = Path(__file__).resolve().parents[1]
    initial = identity(repo, args.source_commit, budget)
    safe_path(args.output)
    require(not args.output.exists(), 'fresh output directory required')
    args.output.mkdir(parents=True, exist_ok=False)
    GUARD.bind_events(args.output)
    try:
        with numerical_fence():
            guard('display_input_hash')
            before = input_fingerprints(args.input, budget)
            arrays = load_members(args.input/'certificate.npz'); budget.check()
            # JSON is parsed as a whole; only schema and rows are consumed for display.
            report = strict_json((args.input/'report.json').read_text()); budget.check()
            data = prepare(arrays, report); budget.check()
            require(input_fingerprints(args.input, budget) == before, 'inputs changed during read')
            provenance = dict(source_run='S03-E019-D03-B003', source_status='incomplete_unaccepted_synthetic',
                              input_root=str(args.input), input_files=before, selected_npz_members=list(KEYS),
                              run_id='S03-E019-D03-F01-V001', source_commit=args.source_commit,
                              runtime_head=initial[0], renderer='aa2024_saved_svg.py',
                              historical_authenticity='not_established_by_current_hash', actual_svd=0, actual_qr=0)
            guard('display_in_memory')
            documents = dict(residuals=residual_svg(data, provenance, budget), square_ledger=ledger_svg(data, provenance, budget))
            for stem, document in documents.items():
                exclusive_text(args.output/(stem+'.svg'), document, budget)
                exclusive_text(args.output/(stem+'.md'), sidecar(stem, provenance, data), budget)
            require(input_fingerprints(args.input, budget) == before, 'inputs changed during display')
            require(identity(repo, args.source_commit, budget) == initial, 'runtime source identity changed')
            names = ('residuals.svg', 'residuals.md', 'square_ledger.svg', 'square_ledger.md', 'runtime_guard_events.log')
            artifacts = {name: digest(args.output/name, budget) for name in names}
            require(artifacts['runtime_guard_events.log'] == hashlib.sha256(b'').hexdigest(), 'nonempty guard event')
            receipt = dict(status='derived_display_completed_not_visual_or_numerical_acceptance',
                           provenance=provenance, source_sha256=initial[1], artifacts_sha256=artifacts,
                           python_version=sys.version, numpy_version=np.__version__, hostname=socket.gethostname(),
                           pid=os.getpid(), command=sys.argv, runtime_guard=GUARD.receipt_state(),
                           elapsed_before_receipt=time.monotonic()-START)
            exclusive_text(args.output/'derived_receipt.json', json.dumps(receipt, indent=2, allow_nan=False), budget)
            require(input_fingerprints(args.input, budget) == before, 'inputs changed before completion')
            require(identity(repo, args.source_commit, budget) == initial, 'source changed before completion')
            exclusive_text(args.output/'derived_completion.json', json.dumps(dict(
                derived_receipt_sha256=digest(args.output/'derived_receipt.json', budget))), budget)
            guard('display_success_stdout')
            print(json.dumps(dict(status=receipt['status'], elapsed_before_print=time.monotonic()-START)))
            budget.check(); guard('display_success_stdout_done')
    except BaseException as error:
        guard('display_failure')
        exclusive_text(args.output/'display_failure.json', json.dumps(dict(status='failed',
                       error=type(error).__name__+': '+str(error)), allow_nan=False), budget)
        raise


if __name__ == '__main__':
    main()
