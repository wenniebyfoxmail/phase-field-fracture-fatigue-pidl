#!/usr/bin/env python3
"""E019-D01: four fixed synthetic controls; no array-file input or numerical SVD.

Prepared for static review only. Execution and tests require separate approval.
"""
import time
PROCESS_START = time.monotonic()

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import warnings
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from unittest.mock import patch

import numpy as np
import aa2024_kinematic_capacity as original

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 'S03-E019-D01-R001'
OUTPUT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01')/RUN_ID/'analysis'
PLAN = 'docs/research/S03/S03-E019/subspace_localisation_plan.md'
THREADS = original.THREADS
RELATIVE_TOLERANCE = 1e-12
ATOL = dict(matrix=1e-12, vector=1e-15, square=1e-18)
ANCHORS = {
    PLAN: 'adbe5d5c9dafbdef0f9db99c231dda5e25840401fd98cac6021b24b320f11be4',
    'docs/research/S03/S03-E019/experiment.md': 'b956f21fa8c417d65d668ca876d91a35b04756c97318938eb95312e758b0cbde',
    'scripts/aa2024_kinematic_capacity.py': '4beb88d2a4b9aef20cc2c60face876f5469202c47b0f268bbc3efbd1cf3abaa7',
    'scripts/aa2024_geometry_prior.py': '0bb5c1c0689bca78021ba6cfbe0ed8979141bca665eabf68e7790f82da363fe5',
    'scripts/aa2024_boundary_basis.py': 'da7862fb55674e8fa83f44334e3e821b4cb7a087ab04a4e09bd9ac9c3dc60b66',
    'scripts/aa2024_triplet_structure.py': 'cf5e4b9dfc30e7c332af3900790694f0fe358225de525cca936c49c17df8b07c',
    'scripts/aa2024_patch_mechanics.py': '7b2299cb3baeb37b9bf7ef4879affbaa7088a0933779cbfca5552dc49bef7a39',
    'scripts/aa2024_rigid_observable.py': 'ebfab2714a7cee1ce03405c4dfd5741eedb6ba4f1de5e4e94ca1525bf4f2199d',
}
SOURCES = tuple(ANCHORS)+(
    'scripts/aa2024_qsubspace_diagnostic.py',
    'tests/test_aa2024_qsubspace_diagnostic.py',
    'docs/research/S03/S03-E019/subspace_test_design.md',
)


def within(start, clock=time.monotonic):
    if clock()-start >= 60.:
        raise TimeoutError('soft60s exceeded; stop without retry')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(commit):
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('full reviewed commit required')
    result = {}
    for name in SOURCES:
        path = ROOT/name
        data = path.read_bytes()  # Only the explicit source/protocol allowlist.
        expected = subprocess.check_output(['git', 'show', commit+':'+name], cwd=ROOT)
        digest = hashlib.sha256(data).hexdigest()
        if data != expected or (name in ANCHORS and digest != ANCHORS[name]):
            raise ValueError('reviewed source/plan changed: '+name)
        result[name] = digest
    return result


def forbidden(*args, **kwargs):
    raise RuntimeError('forbidden decomposition/array input/producer entry')


def guards(stack):
    """Keep prohibitions active throughout arithmetic, rendering and saving."""
    for module in (np.linalg, original.linalg):
        for name in ('svd', 'svdvals', 'eig', 'eigh', 'eigvals', 'eigvalsh',
                     'pinv', 'pinvh', 'lstsq', 'matrix_rank'):
            if hasattr(module, name):
                stack.enter_context(patch.object(module, name, side_effect=forbidden))
    stack.enter_context(patch.object(np, 'load', side_effect=forbidden))
    for module, names in (
        (original, ('run', 'analyze', 'project', 'checked_inputs', 'draw')),
        (original.prior, ('load', 'prepare', 'fit', 'validate', 'solve_patch', 'parse_nodemap')),
    ):
        for name in names:
            if hasattr(module, name):
                stack.enter_context(patch.object(module, name, side_effect=forbidden))


def array2(a):
    a = np.asarray(a, dtype=float)
    if a.ndim == 1:
        a = a[:, None]
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError('finite matrix/column required')
    return a


def dec(a):
    return [[Decimal.from_float(float(x)) for x in row] for row in array2(a)]


def transpose(a):
    return [list(row) for row in zip(*a)]


def dm(a, b):
    if not a or not b or len(a[0]) != len(b):
        raise ValueError('decimal product shape')
    out = [[Decimal(0) for _ in b[0]] for _ in a]
    for i, row in enumerate(a):
        for k, value in enumerate(row):
            if value:
                for j, other in enumerate(b[k]):
                    if other:
                        out[i][j] += value*other
    return out


def combine(a, b, sign=1):
    if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
        raise ValueError('decimal addition shape')
    return [[x+sign*y for x, y in zip(row, other)] for row, other in zip(a, b)]


def magnitude(a):
    return max(abs(x) for row in a for x in row)


def floating(a):
    out = np.array([[float(x) for x in row] for row in a])
    if not np.isfinite(out).all():
        raise ValueError('nonfinite decimal conversion')
    return out


def check(a, b, label, kind='matrix'):
    a, b = array2(a), array2(b)
    if a.shape != b.shape or not np.allclose(a, b, rtol=RELATIVE_TOLERANCE, atol=ATOL[kind]):
        raise ValueError('unexpected identity: '+label)


def dcheck(a, b, label, kind='matrix'):
    if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
        raise ValueError('decimal identity shape: '+label)
    absolute, relative = Decimal.from_float(ATOL[kind]), Decimal.from_float(RELATIVE_TOLERANCE)
    for row, other in zip(a, b):
        for x, ref in zip(row, other):
            if not x.is_finite() or not ref.is_finite() or abs(x-ref) > absolute+relative*abs(ref):
                raise ValueError('unexpected decimal identity: '+label)


def scalar_product(a, b):
    a, b = array2(a), array2(b)
    if a.shape[1] != b.shape[0]:
        raise ValueError('scalar product shape')
    return np.array([[math.fsum(float(x)*float(y) for x, y in zip(row, col))
                      for col in b.T] for row in a])


def crosscheck(a, b, label, kind='matrix'):
    reference = dm(dec(a), dec(b))
    check(scalar_product(a, b), floating(reference), label, kind)
    return reference


def a_layer(H, C, A):
    hd, cd, ad = dec(H), dec(C), dec(A)
    ht = transpose(hd)
    gram = crosscheck(H.T, H, 'A/Gram')
    hc = crosscheck(H.T, C, 'A/HtC')
    aref = combine(cd, dm(hd, hc), -1)
    delta = combine(ad, aref, -1)
    gram_defect = combine(dec(np.eye(H.shape[1])), gram, -1)
    basis_term, evaluation_term = dm(gram_defect, hc), dm(ht, delta)
    total = crosscheck(H.T, A, 'A/HtA')
    dcheck(dm(ht, aref), basis_term, 'A/reference identity')
    dcheck(total, combine(basis_term, evaluation_term), 'A/two-term ledger')
    check(A, floating(aref), 'A/float versus reference')
    return dict(
        A_total_max=str(magnitude(total)),
        gram_defect_max=str(magnitude(gram_defect)),
        A_basis_term_max=str(magnitude(basis_term)),
        A_evaluation_term_max=str(magnitude(evaluation_term)),
        A_float_evaluation_error_max=str(magnitude(delta)),
        A_ledger_error_max=str(magnitude(combine(total, combine(basis_term, evaluation_term), -1))),
    )


def hadamard16():
    k = np.ones((1, 1))
    for _ in range(4):
        k = np.block([[k, k], [k, -k]])
    return k/4.


def analytic_case(name):
    if name not in ('C1', 'C2', 'C3'):
        raise ValueError('fixed case ID required')
    o = hadamard16()
    H, clean, V = o[:, :3].copy(), o[:, 3:8].copy(), o[:, 8:13].copy()
    s = np.array([1., 2.**-4, 2.**-12, 2.**-24, 2.**-32])
    y = (2.**-8*(clean[:, 0]+clean[:, 4])+2.**-12*o[:, 13])[:, None]
    L = clean.copy()
    t = 2.**-20
    c, a = (1-t*t)/(1+t*t), 2*t/(1+t*t)
    if name != 'C1':
        L[:, 4] = c*clean[:, 4]+a*H[:, 1]
    # No SVD: these are prescribed analytic factors, with floating Gram defect retained.
    input_factor = L if name == 'C2' else clean
    A = original.multiply(input_factor*s[None, :], V.T)
    tau = 1e-12*float(s[0])
    if not np.all(s > 10*tau):
        raise ValueError('fixed analytic modes violate frozen cutoff separation')
    return H, A, L, V, s, y, dict(t=t, c=c, a=a, known_retained_modes=5, tau=tau)


def factor_layer(H, A, L, V, s):
    hd, ad, ld, vd = dec(H), dec(A), dec(L), dec(V)
    ht = transpose(hd)
    sd = [Decimal.from_float(float(x)) for x in s]
    ls = [[x*sd[j] for j, x in enumerate(row)] for row in ld]
    E = combine(dm(ad, vd), ls, -1)
    input_term = dm(dm(ht, ad), vd)
    error_term = dm(ht, E)
    reconstructed = [[(x-y)/sd[j] for j, (x, y) in enumerate(zip(row, other))]
                     for row, other in zip(input_term, error_term)]
    hl = crosscheck(H.T, L, 'factor/HtL')
    crosscheck(A, V, 'factor/AV')
    dcheck(hl, reconstructed, 'factor/input-residual amplification')
    reconstruction = original.multiply(L*s[None, :], V.T)
    check(reconstruction, A, 'factor/frozen reconstruction tolerance')
    check(original.multiply(L.T, L), np.eye(5), 'factor/L Gram')
    check(original.multiply(V.T, V), np.eye(5), 'factor/V Gram')
    return dict(
        A_total_max=str(magnitude(dm(ht, ad))),
        factor_gram_defect_max=str(magnitude(combine(dm(transpose(ld), ld), dec(np.eye(5)), -1))),
        factor_HtL_max=str(magnitude(hl)),
        factor_E_max=str(magnitude(E)),
        factor_input_term_max=str(magnitude(input_term)),
        factor_residual_term_max=str(magnitude(error_term)),
        factor_input_amplified_max=str(magnitude([[x/sd[j] for j, x in enumerate(row)] for row in input_term])),
        factor_residual_amplified_max=str(magnitude([[x/sd[j] for j, x in enumerate(row)] for row in error_term])),
        factor_ledger_error_max=str(magnitude(combine(hl, reconstructed, -1))),
        factor_reconstruction_max=float(np.abs(reconstruction-A).max()),
        factor_reconstruction_pass=True,
    )


def projection_layer(name, H, L, y):
    coefficient = original.multiply(L.T, y)
    p = original.multiply(L, coefficient)
    r = p-y
    qr = original.quotient(H, r)
    hd, ld, yd, pd, rd = dec(H), dec(L), dec(y), dec(p), dec(r)
    ht = transpose(hd)
    coefficient_ref = crosscheck(L.T, y, 'projection/coefficient', 'vector')
    pref = dm(ld, coefficient_ref)
    delta_p = combine(pd, pref, -1)
    delta_r = combine(rd, combine(pd, yd, -1), -1)
    existing = dm(dm(ht, ld), coefficient_ref)
    evaluation, subtraction = dm(ht, delta_p), dm(ht, delta_r)
    hp, hy, hr = dm(ht, pd), dm(ht, yd), dm(ht, rd)
    dcheck(hp, combine(existing, evaluation), 'projection/two terms', 'vector')
    dcheck(hr, combine(combine(hp, hy, -1), subtraction), 'residual/three terms', 'vector')
    check(p, floating(pref), 'projection/evaluation', 'vector')
    scalar_qr = r-scalar_product(H, scalar_product(H.T, r))
    check(qr, scalar_qr, 'projection/scalar Q evaluation', 'vector')
    check(scalar_product(H.T, r), floating(hr), 'residual/scalar Htr', 'vector')
    bound = ATOL['vector']+RELATIVE_TOLERANCE*np.abs(r)
    ratio = float(np.max(np.abs(qr-r)/bound))
    passed = bool(np.all(np.abs(qr-r) <= bound))
    expected_pass = name == 'C1'
    if passed != expected_pass:
        raise ValueError('unexpected frozen Q identity outcome: '+name)
    if name == 'C1':
        check(floating(hp), np.zeros((3, 1)), 'clean baseline Htp', 'vector')
        check(floating(hr), np.zeros((3, 1)), 'clean baseline Htr', 'vector')
    metrics = dict(
        p_existing_subspace_max_mm=str(magnitude(existing)),
        p_new_evaluation_max_mm=str(magnitude(evaluation)),
        r_new_subtraction_max_mm=str(magnitude(subtraction)),
        p_float_error_max_mm=str(magnitude(delta_p)),
        r_float_error_max_mm=str(magnitude(delta_r)),
        Htp_max_mm=str(magnitude(hp)), Hty_max_mm=str(magnitude(hy)), Htr_max_mm=str(magnitude(hr)),
        Q_identity_max_mm=float(np.abs(qr-r).max()), Q_identity_ratio=ratio,
        Q_identity_pass=passed,
        Q_identity_role='clean_baseline' if expected_pass else 'predeclared_negative_control',
        Q_identity_outcome='passed' if passed else 'expected_not_passed_at_original_tolerance',
    )
    return metrics, dict(H=H.tolist(), L=L.tolist(), y=y.tolist(), p=p.tolist(), r=r.tolist())


def diagnostic(start, clock=time.monotonic):
    """Fixed synthetic constants only. No data paths or case/precision overrides."""
    rows, evidence = [], {}
    with localcontext() as ctx:
        ctx.prec = 80
        xy = np.array([[-13.05, -4.95], [-8.55, -2.25], [-4.05, 2.25], [-.45, 4.95],
                       [.45, -4.95], [4.05, -2.25], [8.55, 2.25], [13.05, 4.95]])
        w = np.arange(1., 9.)
        S, nodes, coeff = original.sampling(xy)
        bd = original.prior.rectangular_mesh()[2]
        free = np.flatnonzero(~np.repeat(bd, 2))
        if S[:, np.flatnonzero(np.repeat(bd, 2))].nnz:
            raise ValueError('synthetic C0 direct boundary sampling')
        scale, H = original.rigid_basis(xy, w)  # Exactly one synthetic thin QR.
        C = scale[:, None]*S[:, free].toarray()
        A = original.quotient(H, C)
        if C.shape != (16, 1482):
            raise ValueError('synthetic C0 shape')
        rows.append(dict(case='C0', scope='synthetic_A_construction', **a_layer(H, C, A),
                         Q_identity_ratio=None, Q_identity_pass=None, Q_identity_role='not_applicable',
                         Q_identity_outcome='no_y_p_r_in_C0'))
        evidence['C0'] = dict(xy=xy.tolist(), weights=w.tolist(), H=H.tolist(), scale=scale.tolist(),
                              stencil_nodes=nodes.tolist(), stencil_coeff=coeff.tolist(), free_dofs=free.tolist())
        within(start, clock)
        for name in ('C1', 'C2', 'C3'):
            H, A, L, V, s, y, constants = analytic_case(name)
            f = factor_layer(H, A, L, V, s)
            p, data = projection_layer(name, H, L, y)
            if name == 'C1':
                check(floating(dm(dec(H.T), dec(A))), np.zeros((3, 16)), 'clean baseline HtA')
                check(floating(dm(dec(H.T), dec(L))), np.zeros((3, 5)), 'clean baseline HtL')
            rows.append(dict(case=name, scope='synthetic_analytic_factors', **f, **p))
            evidence[name] = dict(**data, A=A.tolist(), V=V.tolist(), s=s.tolist(), constants=constants)
            within(start, clock)
        if evidence['C2']['p'] != evidence['C3']['p'] or evidence['C2']['r'] != evidence['C3']['r']:
            raise ValueError('fixed C2/C3 shared factors must produce identical p/r')
    return dict(domain='synthetic', protocol_revision='E019-D01_v1.1', cases=rows,
                evidence=evidence, precision_digits=80, reference_conversion='Decimal.from_float',
                tolerances=dict(rtol=RELATIVE_TOLERANCE, **ATOL),
                svd_calls=0, eig_calls=0, fem_solves=0, array_file_inputs=0,
                conclusion_scope='synthetic mechanism only; actual E019 root cause unresolved; original failed check retained')


def write_json(path, obj):
    with path.open('w') as handle:
        json.dump(obj, handle, indent=2, allow_nan=False)
        handle.write('\n')


def render(report, out):
    # Fresh figure only; never invokes the old producer/rendering pipeline.
    plt = original.plt
    fig, ax = plt.subplots(figsize=(7.4, 4.2), constrained_layout=True)
    try:
        for i, row in enumerate(report['cases'][1:]):
            value = row['Q_identity_ratio']
            ax.scatter(i, value, s=48, marker='o' if i == 0 else 'x', color='#0072B2' if i == 0 else '#D55E00')
            ax.annotate('0 (exact)' if value == 0 else '%.5g' % value, (i, value),
                        xytext=(0, 8), textcoords='offset points', ha='center')
        ax.axhline(1., color='black', ls='--', lw=1.2, label='Original vector tolerance boundary = 1')
        ax.set_yscale('symlog', linthresh=1.)
        ax.set_xticks(range(3), ['C1 clean', 'C2 input perturbation', 'C3 factor perturbation'])
        ax.set_ylabel('max componentwise error / original allowed error [dimensionless]')
        ax.set_title('SYNTHETIC | E019-D01-R001 | zero SVD\nC2/C3 are prescribed negative controls, not actual solver errors', fontsize=10)
        ax.legend(loc='upper left', fontsize=8)
        for suffix in ('png', 'pdf'):
            fig.savefig(out/('q_identity_ratio.'+suffix), dpi=170)
    finally:
        plt.close(fig)
    note = (
        '# q_identity_ratio\n\n## Figure question\n\n'
        'Can different synthetic input/factor mechanisms yield the same Q-space discrepancy?\n\n'
        '## How to read / panels\n\nOne panel; all three prescribed analytic cases. '
        'C0 has no y/p/r and is not applicable, not a zero error case. '
        'Vertical value is max_i[abs((Qr-r)_i)/(1e-15+1e-12*abs(r_i))], dimensionless; '
        'line 1 is the original vector tolerance boundary. Symlog keeps exact zeros at zero; '
        'no plotting floor or clipping. Blue circle: clean control; orange crosses: injected negative controls.\n\n'
        '## Data provenance\n\n'+RUN_ID+'; this folder report.json and summary.csv; '
        'fixed Hadamard16 analytic factors, t=2^-20, five fixed modes; no data-array input and no SVD. '
        'Code/protocol hashes in execution_receipt.json.\n\n'
        '## Key numerical takeaway\n\n'+json.dumps([{k: r[k] for k in ('case', 'Q_identity_ratio', 'Q_identity_outcome')}
                                                    for r in report['cases'][1:]], allow_nan=False)+'\n\n'
        '## Limitations and claim boundary\n\nSynthetic arithmetic controls only, not independent specimens, '
        'DIC observations, noise calibration, actual gesvd error measurements, material/phase-field inversion or prediction. '
        'C2/C3 share factors and y, hence share p/r despite different input/factor provenance. '
        'Float factor Gram defects are reported, not renormalized away. Existing E019 outputs, '
        'failed identity and acceptance pause are unchanged; no real root-cause certification.\n\n'
        '## Related assets\n\nreport.json; summary.csv; README_analysis.md; execution_receipt.json; same-stem PNG/PDF.\n'
    )
    with (out/'q_identity_ratio.md').open('w') as handle:
        handle.write(note)
    with (out/'README_analysis.md').open('w') as handle:
        handle.write(note+'\nMatrix ledger columns are dimensionless; vector ledger columns use mm. '
                     'A max magnitude is not an additive causal allocation. Decimal reference uses precision 80, '
                     'not infinite precision. This report cannot identify actual E019 A/Lr history.\n')


def run(out, commit):
    start = PROCESS_START
    if out.resolve() != OUTPUT.resolve() or out.exists():
        raise ValueError('fresh canonical synthetic output required; no retry/overwrite')
    before = source_hashes(commit)
    within(start)
    out.mkdir(parents=False, exist_ok=False)
    receipt = dict(run_id=RUN_ID, execution_status='running', hostname=socket.gethostname(), pid=os.getpid(),
                   start_utc=datetime.now(timezone.utc).isoformat(), budget_seconds=60., command=sys.argv,
                   source_commit_declared=commit, sources_before_sha256=before,
                   git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   git_status=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True),
                   thread_environment={k: os.environ.get(k) for k in THREADS}, numpy_version=np.__version__,
                   python_version=sys.version, budget_scope='process import start through final receipt write',
                   scientific_role='synthetic numerical diagnostic only; no E019 acceptance change')
    try:
        with ExitStack() as stack, warnings.catch_warnings(), np.errstate(all='warn'):
            warnings.simplefilter('error')
            guards(stack)
            report = diagnostic(start)
            within(start)
            write_json(out/'report.json', report)
            fields = list(dict.fromkeys(key for row in report['cases'] for key in row))
            with (out/'summary.csv').open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(report['cases'])
            within(start)
            render(report, out)
            within(start)
            after = source_hashes(commit)
            if before != after:
                raise ValueError('source changed during diagnostic')
            names = {'report.json', 'summary.csv', 'q_identity_ratio.png', 'q_identity_ratio.pdf',
                     'q_identity_ratio.md', 'README_analysis.md'}
            if {p.name for p in out.iterdir()} != names:
                raise ValueError('unexpected synthetic artifact set')
            receipt.update(sources_after_sha256=after, artifacts_sha256={n: sha(out/n) for n in sorted(names)},
                           execution_status='succeeded', elapsed_seconds=time.monotonic()-start,
                           end_utc=datetime.now(timezone.utc).isoformat())
            within(start)
            write_json(out/'execution_receipt.json', receipt)
            within(start)
    except Exception as exc:
        receipt.update(execution_status='failed', error=repr(exc), outputs_role='forensic_only',
                       elapsed_seconds=time.monotonic()-start, end_utc=datetime.now(timezone.utc).isoformat())
        write_json(out/'execution_receipt.json', receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    if any(os.environ.get(k) != '1' for k in THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('single-thread CPU and disabled CUDA required')
    if os.environ.get('PYTHONWARNINGS') != 'error':
        raise ValueError('PYTHONWARNINGS=error required')
    run(args.output, args.source_commit)


if __name__ == '__main__':
    main()
