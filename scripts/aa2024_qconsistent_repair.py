"""E019-D02: fixed synthetic Q-consistent projection candidate. NOT YET RUN.

No project producer imports, real-data parameters or array-file reads.
Execution is available only through the separately approved launcher.
"""
from contextlib import ExitStack
from decimal import Decimal, localcontext
import math
from unittest.mock import patch

import numpy as np
from scipy import linalg

RTOL = 1e-12
ATOL = {'matrix': 1e-12, 'vector': 1e-15, 'square': 1e-18}
CASES = ('C1', 'C2', 'C3')
MODES = 5


class Stop(ValueError):
    """A classified stop, never a request to retry or change tolerance."""


def matrix(a):
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise Stop('STOP_INPUT: finite two-dimensional float64 required')
    return a


def multiply(a, b):
    # Same explicit contraction definition as frozen E019; no producer import.
    a, b = matrix(a), matrix(b)
    if a.shape[1] != b.shape[0]:
        raise Stop('STOP_INPUT: contraction shape')
    result = np.einsum('ik,kj->ij', a, b, optimize=False)
    return matrix(result)


def quotient(H, x):
    return matrix(x) - multiply(H, multiply(matrix(H).T, x))


def ratio(a, ref, kind):
    a, ref = matrix(a), matrix(ref)
    if a.shape != ref.shape:
        raise Stop('STOP_INPUT: comparison shape')
    return float(np.max(np.abs(a-ref)/(ATOL[kind]+RTOL*np.abs(ref))))


def check(a, ref, label, kind='matrix'):
    value = ratio(a, ref, kind)
    if value > 1:
        raise Stop('STOP_IDENTITY: '+label)
    return value


def decimals(a):
    return [[Decimal.from_float(float(x)) for x in row] for row in matrix(a)]


def dt(a):
    return list(map(list, zip(*a)))


def dm(a, b):
    if not a or not b or len(a[0]) != len(b):
        raise Stop('STOP_REFERENCE: Decimal product shape')
    return [[sum((x*y for x, y in zip(row, col)), Decimal(0))
             for col in zip(*b)] for row in a]


def ds(a, b):
    if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
        raise Stop('STOP_REFERENCE: Decimal subtraction shape')
    return [[x-y for x, y in zip(row, other)] for row, other in zip(a, b)]


def df(a):
    return matrix([[float(x) for x in row] for row in a])


def fsum_product(a, b):
    # Each Python float product rounds first; fsum only improves the summation.
    a, b = matrix(a), matrix(b)
    if a.shape[1] != b.shape[0]:
        raise Stop('STOP_REFERENCE: fsum shape')
    return matrix([[math.fsum(float(x)*float(y) for x, y in zip(row, col))
                    for col in b.T] for row in a])


def reference_product(a, b, value, label, kind='matrix'):
    """Check a float product, never feed a reference back into the candidate."""
    ref = df(dm(decimals(a), decimals(b)))
    try:
        d_ratio = check(value, ref, label+' / Decimal80', kind)
        f_ratio = check(fsum_product(a, b), ref, label+' / fsum', kind)
    except Stop as exc:
        raise Stop('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: '+label) from exc
    return {'float_vs_Decimal80_ratio': d_ratio, 'fsum_vs_Decimal80_ratio': f_ratio}


def q_check(H, z, kind='vector'):
    qz = quotient(H, z)  # Read-only check, never assigned back to z.
    hd, zd = decimals(H), decimals(z)
    qref = df(ds(zd, dm(hd, dm(dt(hd), zd))))
    qfsum = z-fsum_product(H, fsum_product(H.T, z))
    try:
        check(qz, qref, 'Q evaluation / Decimal80', kind)
        check(qfsum, qref, 'Q evaluation / fsum', kind)
    except Stop as exc:
        raise Stop('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: Q evaluation') from exc
    # Ratios have separate paths; no inferred scalar cross-path equality gate.
    producer, independent = ratio(qz, z, kind), ratio(qref, z, kind)
    return {'producer_einsum_ratio': producer, 'Decimal80_ratio': independent,
            'producer_pass': producer <= 1, 'Decimal80_pass': independent <= 1,
            'Qz_float': qz.tolist(), 'Qz_Decimal80': [[str(x) for x in row]
                for row in ds(zd, dm(hd, dm(dt(hd), zd)))],
            'Qz_fsum': qfsum.tolist()}


def require_q(H, z, label, kind='vector'):
    result = q_check(H, z, kind)
    if result['producer_pass'] != result['Decimal80_pass']:
        raise Stop('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: '+label)
    if not result['producer_pass']:
        raise Stop('STOP_Q_CONSISTENCY: '+label)
    return result


def hadamard16():
    k = np.ones((1, 1), dtype=np.float64)
    for _ in range(4):
        k = np.block([[k, k], [k, -k]])
    return k/4.


def fixture(name):
    if name not in CASES:
        raise Stop('STOP_INPUT: fixed C1-C3 only')
    o = hadamard16()
    H, clean, V, g = o[:, :3].copy(), o[:, 3:8].copy(), o[:, 8:13].copy(), o[:, 13:14].copy()
    s = np.array([1., 2.**-4, 2.**-12, 2.**-24, 2.**-32])
    t = 2.**-20
    c, a = (1-t*t)/(1+t*t), 2*t/(1+t*t)
    Lr = clean.copy()
    if name != 'C1':
        Lr[:, 4] = c*clean[:, 4]+a*H[:, 1]
    input_factor = Lr if name == 'C2' else clean
    A = multiply(input_factor*s[None, :], V.T)
    y = 2.**-8*(clean[:, 0:1]+clean[:, 4:5])+2.**-12*g
    if not np.all(s > 10*(1e-12*s[0])):
        raise Stop('STOP_INPUT: frozen mode separation')
    return dict(H=H, Lr=Lr, A=A, V=V, s=s, y=y, clean=clean, g=g,
                constants={'t': t, 'c': c, 'a': a, 'tau': 1e-12*float(s[0]),
                           'retained_modes': MODES})


def signed_qr(U, T):
    U, T = matrix(U).copy(), matrix(T).copy()
    if U.shape != (16, MODES) or T.shape != (MODES, MODES):
        raise Stop('STOP_RANK_GUARD: five modes required')
    diagonal = np.diag(T)
    if np.any(diagonal == 0):
        raise Stop('STOP_RANK_GUARD: zero QR diagonal')
    signs = np.where(diagonal > 0, 1., -1.)
    return U*signs[None, :], T*signs[:, None]


def rank_guard(T):
    T = matrix(T)
    if T.shape != (MODES, MODES) or np.any(np.diag(T) <= 0):
        raise Stop('STOP_RANK_GUARD: positive five-mode triangular factor required')
    # Induced row-sum infinity norm, NOT maximum absolute element.
    eta = float(np.max(np.sum(np.abs(np.eye(MODES)-T), axis=1)))
    if eta > .5:  # Hard sufficient refusal, deliberately no isclose/tolerance.
        raise Stop('STOP_RANK_GUARD: eta exceeds fixed one-half')
    return eta


def repair(H, Lr, y):
    """Only H/Lr/y enter the candidate: no A/s/V/clean basis or oracle inputs."""
    H, Lr, y = matrix(H), matrix(Lr), matrix(y)
    if H.shape != (16, 3) or Lr.shape != (16, MODES) or y.shape != (16, 1):
        raise Stop('STOP_INPUT: fixed dimensions')
    check(multiply(H.T, H), np.eye(3), 'input H Gram')
    require_q(H, y, 'input y before repair')  # Admission only; y is not replaced.
    B = quotient(H, Lr)  # The candidate's sole Q operation.
    U, T = linalg.qr(B, mode='economic', pivoting=False, check_finite=True)
    U, T = signed_qr(U, T)
    eta = rank_guard(T)
    p = multiply(U, multiply(U.T, y))
    r = p-y
    return dict(B=B, U=U, T=T, p=p, r=r, eta=eta)


def square(z):
    z = matrix(z)
    return float(np.sum(z*z))


def image_probe(U, b, label):
    image = multiply(U, multiply(U.T, b))
    return image, check(image, b, label, 'vector')


def audit_case(name, f, candidate):
    H, Lr, y, clean = (f[k] for k in ('H', 'Lr', 'y', 'clean'))
    B, U, T, p, r = (candidate[k] for k in ('B', 'U', 'T', 'p', 'r'))
    checks = {}
    checks['H_gram'] = check(multiply(H.T, H), np.eye(3), 'H Gram')
    checks['input_y_Q'] = require_q(H, y, 'unchanged input y')
    checks['qr_reconstruction'] = check(multiply(U, T), B, 'UT=B')
    checks['qr_orthogonality'] = check(multiply(U.T, U), np.eye(MODES), 'U Gram')
    checks['U_Q'] = require_q(H, U, 'U', 'matrix')
    checks['p_Q'] = require_q(H, p, 'p')
    checks['r_Q'] = require_q(H, r, 'r')
    checks['normal_equation'] = check(multiply(U.T, r), np.zeros((MODES, 1)), 'UTr=0', 'vector')
    checks['residual_definition'] = check(p-y, r, 'p-y=r', 'vector')
    pstar = 2.**-8*(clean[:, 0:1]+clean[:, 4:5])
    rstar = -2.**-12*f['g']
    try:
        checks['primary_p'] = check(p, pstar, 'analytic p*', 'vector')
        checks['primary_r'] = check(r, rstar, 'analytic r*', 'vector')
    except Stop as exc:
        raise Stop('STOP_ANALYTIC_PROJECTION: '+name) from exc
    old_p = multiply(Lr, multiply(Lr.T, y))
    old_r = old_p-y
    old_q = q_check(H, old_r)
    expected = name == 'C1'
    if old_q['producer_pass'] != old_q['Decimal80_pass']:
        raise Stop('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: old negative control')
    if old_q['producer_pass'] is not expected:
        raise Stop('STOP_OLD_CONTROL: unexpected original Q result')
    if expected:
        checks['C1_p_preserved'] = check(p, old_p, 'C1 old p preserved', 'vector')
        checks['C1_r_preserved'] = check(r, old_r, 'C1 old r preserved', 'vector')
    # Actual float inputs -> Decimal80, never a second decomposition/repair.
    try:
        checks['B_reference'] = check(B, df(ds(decimals(Lr), dm(decimals(H), dm(dt(decimals(H)), decimals(Lr))))),
                                      'B actual-input reference')
    except Stop as exc:
        raise Stop('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: B') from exc
    checks['UT_paths'] = reference_product(U, T, multiply(U, T), 'UT')
    coefficients = multiply(U.T, y)
    checks['UTy_paths'] = reference_product(U.T, y, coefficients, 'UTy', 'vector')
    checks['p_product_paths'] = reference_product(U, coefficients, p, 'p product', 'vector')
    p_ref = dm(decimals(U), dm(dt(decimals(U)), decimals(y)))
    r_ref = ds(p_ref, decimals(y))
    try:
        checks['p_full_Decimal80'] = check(p, df(p_ref), 'p full Decimal80', 'vector')
        checks['r_full_Decimal80'] = check(r, df(r_ref), 'r full Decimal80', 'vector')
    except Stop as exc:
        raise Stop('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: p/r') from exc
    probes = []
    for j in range(MODES):
        b = 2.**-8*clean[:, j:j+1]
        image, image_ratio = image_probe(U, b, 'probe image '+str(j+1))
        residual, d = b-y, b-p
        addition = check(residual, d+r, 'probe residual addition', 'vector')
        cross = 2*float(multiply(r.T, d)[0, 0])
        cross_ratio = check([[cross]], [[0.]], 'probe cross term', 'square')
        decomposition = check([[square(residual)]], [[square(r)+square(d)]], 'Pythagoras', 'square')
        n = 1 if j in (0, 4) else 3
        oracle_d2 = n*2.**-16
        oracle_total = oracle_d2+2.**-24
        check([[square(d)]], [[oracle_d2]], 'probe analytic gap', 'square')
        check([[square(residual)]], [[oracle_total]], 'probe analytic total', 'square')
        probes.append(dict(mode=j+1, b=b.tolist(), image=image.tolist(), d=d.tolist(),
                           residual=residual.tolist(), image_ratio=image_ratio, addition_ratio=addition,
                           cross_mm2=cross, cross_ratio=cross_ratio, Pythagoras_ratio=decomposition,
                           gap_square_mm2=square(d), total_square_mm2=square(residual),
                           analytic_gap_square_mm2=oracle_d2, analytic_total_square_mm2=oracle_total))
    check([[square(r)]], [[2.**-24]], 'analytic floor square', 'square')
    return dict(case=name, input_mechanism={'C1': 'clean', 'C2': 'prescribed_A_leakage',
                'C3': 'prescribed_factor_leakage'}[name], retained_modes=MODES,
                candidate_Q_applications=1, qr_calls=1, eta=candidate['eta'],
                old_Q_role='clean_baseline' if expected else 'predeclared_negative_control',
                old_r_Q=old_q, checks=checks, probes=probes,
                evidence={**{k: v.tolist() for k, v in f.items() if isinstance(v, np.ndarray)},
                    'constants': f['constants'],
                    **{k: candidate[k].tolist() for k in ('B', 'U', 'T', 'p', 'r')},
                    'p_old': old_p.tolist(), 'r_old': old_r.tolist(),
                    'p_star': pstar.tolist(), 'r_star': rstar.tolist(),
                    'p_actual_U_Decimal80': [[str(x) for x in row] for row in p_ref],
                    'r_actual_U_Decimal80': [[str(x) for x in row] for row in r_ref]})


def forbidden(*args, **kwargs):
    raise Stop('STOP_FORBIDDEN: decomposition or array-file input')


def guards(stack):
    sentinels = []
    for module in (np.linalg, linalg):
        for name in ('svd', 'svdvals', 'eig', 'eigh', 'eigvals', 'eigvalsh', 'pinv',
                     'pinvh', 'lstsq', 'matrix_rank', 'cond'):
            if hasattr(module, name):
                sentinel = stack.enter_context(patch.object(module, name, side_effect=forbidden))
                sentinels.append(sentinel)
    for name in ('load', 'loadtxt', 'genfromtxt', 'fromfile', 'memmap'):
        sentinels.append(stack.enter_context(patch.object(np, name, side_effect=forbidden)))
    sentinels.append(stack.enter_context(patch.object(np.linalg, 'qr', side_effect=forbidden)))
    return sentinels


def diagnose(check_time):
    rows = []
    with ExitStack() as stack, localcontext() as ctx, np.errstate(all='raise'):
        ctx.prec = 80
        sentinels = guards(stack)
        actual_qr = linalg.qr
        qr_spy = stack.enter_context(patch.object(linalg, 'qr', wraps=actual_qr))
        for name in CASES:
            check_time()
            f = fixture(name)
            candidate = repair(f['H'], f['Lr'], f['y'])
            rows.append(audit_case(name, f, candidate))
            check_time()
        if qr_spy.call_count != 3 or any(s.call_count for s in sentinels):
            raise Stop('STOP_CALL_COUNTS: exactly three QR and zero forbidden calls')
    left, right = rows[1]['evidence'], rows[2]['evidence']
    if (left['A'] == right['A'] or left['Lr'] != right['Lr'] or left['y'] != right['y'] or
            left['p_old'] != right['p_old'] or left['r_old'] != right['r_old']):
        raise Stop('STOP_CONTROL_IDENTITY: same old p/r but different A lost')
    return dict(protocol='E019-D02_v0.1', domain='synthetic', status='candidate_checks_passed',
                cases=rows, tolerances={'rtol': RTOL, **ATOL}, qr_calls=3, svd_calls=0,
                forbidden_calls=0, numerical_scope='fixed synthetic construction only',
                reference_scope='analytic dyadic truth; Decimal80 exact-from-float; fsum rounded products',
                limitations=['not measured SVD errors', 'C2/C3 share candidate inputs, not independent stress tests',
                             'not real E019 cause or acceptance repair', 'not DIC inversion or prediction validity'])


def render(report, out):
    """One fixed-layout figure, only values from this new scored report."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.text import Text
    fig, ax = plt.subplots(figsize=(10.8, 5.8), dpi=170)
    try:
        fig.subplots_adjust(left=.15, right=.97, bottom=.23, top=.79)
        fig.text(.5, .97, 'E019-D02 | R001 | synthetic controls | zero SVD', ha='center', va='top', fontsize=12)
        fig.text(.5, .90, 'Old negative controls retained; new path: one Q + thin QR', ha='center', va='top', fontsize=10)
        ax.set_yscale('symlog', linthresh=1)
        ax.set_ylim(0, 1e8)
        ax.set_xlim(-.5, 2.5)
        ax.set_xticks(range(3), ['C1\nclean', 'C2\nA-input perturbation', 'C3\nfactor perturbation'])
        ax.set_ylabel('Q(r) identity error ratio\n(dimensionless)')
        ax.axhline(1, color='black', linestyle='--', linewidth=1)
        ax.text(.98, 1, 'Original tolerance = 1', transform=ax.get_yaxis_transform(), ha='right', va='bottom', fontsize=9)
        for i, row in enumerate(report['cases']):
            old = row['old_r_Q']['producer_einsum_ratio']
            new = row['checks']['r_Q']['producer_einsum_ratio']
            ax.scatter([i-.10], [old], marker='x', color='#D55E00', s=45, clip_on=False,
                       label='Original path' if i == 0 else None)
            ax.scatter([i+.10], [new], marker='o', color='#0072B2', s=38, clip_on=False,
                       label='Q-consistent candidate' if i == 0 else None)
            ax.annotate(f'old {old:.4g}', (i-.10, old), xytext=(-6, -18 if old > 1 else 28),
                        textcoords='offset points', ha='center', va='top', fontsize=9)
            ax.annotate(f'new {new:.4g}', (i+.10, new), xytext=(6, 10),
                        textcoords='offset points', ha='center', va='bottom', fontsize=9)
        ax.legend(loc='upper left', fontsize=9)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        # Fail rather than adjusting layout if any visible text leaves the canvas.
        for text in fig.findobj(Text):
            if text.get_visible() and text.get_text():
                box = text.get_window_extent(renderer)
                if box.x0 < 2 or box.y0 < 2 or box.x1 > fig.bbox.x1-2 or box.y1 > fig.bbox.y1-2:
                    raise Stop('STOP_LAYOUT: text outside fixed canvas')
        for suffix in ('png', 'pdf'):
            with (out/('q_identity_ratio.'+suffix)).open('xb') as handle:
                fig.savefig(handle, format=suffix, dpi=170)
    finally:
        plt.close(fig)


def sidecar(report):
    rows = '\n'.join(f"- {r['case']}: old={r['old_r_Q']['producer_einsum_ratio']!r}; "
                     f"new={r['checks']['r_Q']['producer_einsum_ratio']!r}; "
                     f"analytic p ratio={r['checks']['primary_p']!r}; eta={r['eta']!r}"
                     for r in report['cases'])
    return f'''# Q-consistent projection: fixed synthetic controls

## Figure question
Does the one-Q plus thin-QR candidate preserve Q-consistent residuals on the three fixed controls?

## Data provenance
S03-E019-D02-R001, report.json, generated from only the reviewed artificial constants.
Script: scripts/aa2024_qconsistent_repair.py; code identity and report SHA in execution_receipt.json.
No original archived arrays, real DIC, stage15, new holdout or numerical SVD.

## Visual grammar and panel guide
One panel; x: all C1-C3 controls in fixed order. Orange x: original path; blue circle: candidate.
y: max_i |(Qr)_i-r_i|/(1e-15 mm+1e-12 |r_i|), producer einsum evaluation path.
Symlog has linear range below 1 and fixed [0,1e8] extent; zeros remain zero, not epsilon.
Dashed line 1 is the original componentwise tolerance. Markers at zero may cross the axis, not canvas.
Decimal80 and fsum reference paths are separately saved, not silently substituted in this plot.

## Key numerical takeaway
{rows}
Full primary analytic-p/r ratios and all five image/Pythagoras probes are in report.json and summary.csv.
Q consistency alone cannot establish the primary claim.

## Limitations and claim boundary
C2/C3 share candidate Lr/y and differ in artificial A provenance; they are not independent stress inputs.
Old C2/C3 negative controls are retained. No actual SVD error measurement, true E019 cause,
old-result rescue, real DIC inversion, physical identification or future-prediction claim.
This figure explains the newly scored outputs, never changes thresholds or old verdicts.

## Related assets
q_identity_ratio.png, q_identity_ratio.pdf, report.json, summary.csv, execution_receipt.json.
'''


if __name__ == '__main__':
    raise SystemExit('Use the separately reviewed launcher; direct diagnostic execution is disabled.')
