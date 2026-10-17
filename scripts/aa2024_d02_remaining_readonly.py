#!/usr/bin/env python3
"""D02 saved-artifact acceptance only; prepared, not executed.

Standard library reference arithmetic, no producer import/decomposition/writes.
PNG viewing is a separate, conditional read-only tool step after exit0.
"""
import time
START = time.monotonic()

import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import io
import json
import logging
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import zlib

REPO = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013')
ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001')
TEST = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks/S03-E019-D02-T001')
SNAPSHOT = '0fb6bfeffbd96bb45eb7c9ac5c75f10172fe7c42'
SOURCES = (
    'scripts/aa2024_qconsistent_repair.py', 'scripts/aa2024_qconsistent_launch.py',
    'tests/test_aa2024_qconsistent_repair.py',
    'docs/research/S03/S03-E019/q_consistency_repair_plan.md',
    'docs/research/S03/S03-E019/q_consistency_plan_review.md',
    'docs/research/S03/S03-E019/q_consistency_pro_request.md',
    'docs/research/S03/S03-E019/q_consistency_pro_response.md',
    'docs/research/S03/S03-E019/q_consistency_test_design.md',
    'scripts/aa2024_kinematic_capacity.py', 'scripts/aa2024_qsubspace_diagnostic.py',
)
PINNED = {
    ROOT/'report.json': '76ab2a6bb7d2e909a39fc08797bfb93dd2d344ebf5b0e46963b90b1eba85ecaa',
    ROOT/'summary.csv': '1fc66beba44f2027cfe99eb508a64aafdd01e7f41979ee8522d5be3f6fe66ff9',
    ROOT/'q_identity_ratio.png': 'a2fc8b937df8ea1e72a683019172c89dc76a7f26c00690df8a27b4195724dbf9',
    ROOT/'q_identity_ratio.pdf': '3a119769edc5bb81e1189bafec596a4a2d9ae2bc3ef111a56655a2d9051bdd16',
    ROOT/'q_identity_ratio.md': '0788c0190a6906f633d01fbbc985ff60e765fdf0af7939a98e0a2cac101df0fc',
    ROOT/'execution_receipt.json': 'f5eb8bbf642ac99bc85461412ab52d4bc84c764b17f9d29bd89c962ad1ea98d1',
    ROOT/'q_identity_ratio.sidecar_v01.md': 'b4ad866d79174d72fbecefad051092ea6ebb8e1f964a7bd2c2a1532474fd9246',
    ROOT/'q_identity_ratio.sidecar_v01.receipt.json': '631afb1ca7c204fe85225853d1b252c5c1e931c66289f0eea48f7dad8e209c37',
    TEST/'test_receipt.json': '37c75fac8698df03075d2405517211942c60eb511ccb9f6187303bb9827c1f8c',
    TEST/'tests.log': '53d6928e2de7285ece1d0c903b9105d269168ae9b9670301677f432459dca9c9',
    REPO/'scripts/aa2024_d02_sidecar_v01.py': '2247849e9535414ef67762893e4a17194cd448606d062a4ccfcfa91b9805eab2',
    REPO/'source/validate_figure_sidecars.py': '56b8f45ce496f425b29676246042eff8d19c31cd005259820b94c7804c5b664a',
}
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')
COMPLETED = []
ALLOWED = set(PINNED) | {REPO/name for name in SOURCES} | {REPO/'scripts/aa2024_d02_remaining_readonly.py'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def within():
    need(time.monotonic()-START < 60, 'STOP_BUDGET_60_SECONDS')


def deadline(*_):
    raise TimeoutError('STOP_BUDGET_60_SECONDS')


class WarningStop(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            raise RuntimeError('STOP_LOG_WARNING: '+record.getMessage())


def raw(path):
    within()
    need(path in ALLOWED, 'STOP_READ_ALLOWLIST: '+str(path))
    need(path.resolve() == path and path.is_file() and not path.is_symlink(), 'STOP_PATH: '+str(path))
    return path.read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def process(command):
    within()
    result = subprocess.run(command, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=max(.001, 60-(time.monotonic()-START)), check=False)
    need(result.returncode == 0 and not result.stderr, 'STOP_SUBPROCESS: '+repr(command)+': '+result.stderr.decode(errors='replace'))
    within()
    return result.stdout


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'STOP_JSON_DUPLICATE: '+key)
        result[key] = value
    return result


def load(data):
    def invalid(value):
        raise ValueError('STOP_NONFINITE_JSON: '+value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def dec(value):
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, str):
        result = Decimal(value)
    else:
        need(type(value) in (float, int), 'STOP_NONNUMERIC')
        result = Decimal.from_float(float(value))
    need(result.is_finite(), 'STOP_NONFINITE')
    return result


def mat(value, rows, cols):
    need(isinstance(value, list) and len(value) == rows and all(isinstance(r, list) and len(r) == cols for r in value), 'STOP_MATRIX_SHAPE')
    return [[dec(x) for x in row] for row in value]


def tr(a):
    return list(map(list, zip(*a)))


def mul(a, b):
    need(len(a[0]) == len(b), 'STOP_PRODUCT_SHAPE')
    return [[sum((x*y for x, y in zip(row, col)), Decimal(0)) for col in zip(*b)] for row in a]


def sub(a, b):
    need(len(a) == len(b) and all(len(x) == len(y) for x, y in zip(a, b)), 'STOP_SUB_SHAPE')
    return [[x-y for x, y in zip(row, other)] for row, other in zip(a, b)]


def add(a, b):
    return sub(a, [[-v for v in row] for row in b])


def eye(n):
    return [[Decimal(int(i == j)) for j in range(n)] for i in range(n)]


def close(a, ref, kind, label):
    atol = dec({'matrix': 1e-12, 'vector': 1e-15, 'square': 1e-18}[kind])
    differences = sub(a, ref)
    ratio = max(abs(d)/(atol+dec(1e-12)*abs(r)) for row, rr in zip(differences, ref) for d, r in zip(row, rr))
    need(ratio <= 1, 'STOP_IDENTITY: '+label)
    return float(ratio)


def scalar(value, ref, kind, label):
    return close([[dec(value)]], [[dec(ref)]], kind, label)


def square(a):
    return sum((x*x for row in a for x in row), Decimal(0))


def q(H, z):
    return sub(z, mul(H, mul(tr(H), z)))


def rounded(a):
    return [[dec(float(x)) for x in row] for row in a]


def fmul(a, b):
    return [[float(math.fsum(float(x)*float(y) for x, y in zip(row, col))) for col in zip(*b)] for row in a]


def float_ratio(a, ref, kind):
    atol = {'matrix': 1e-12, 'vector': 1e-15, 'square': 1e-18}[kind]
    need(len(a) == len(ref) and all(len(x) == len(y) for x, y in zip(a, ref)), 'STOP_RATIO_SHAPE')
    return max(abs(float(x)-float(y))/(atol+1e-12*abs(float(y))) for row, rr in zip(a, ref) for x, y in zip(row, rr))


def qrecord(H, z, saved, kind, expected, label):
    rows, cols = len(z), len(z[0])
    reference = q(H, z)
    producer = mat(saved['Qz_float'], rows, cols)
    d_saved = mat(saved['Qz_Decimal80'], rows, cols)
    f_saved = mat(saved['Qz_fsum'], rows, cols)
    # Decimal80 from the actual saved binary64 operands, never fed back to output.
    close(d_saved, reference, kind, label+' Decimal ledger')
    try:
        close(producer, rounded(reference), kind, label+' producer/reference evaluation')
    except ValueError as exc:
        raise ValueError('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: '+label+' producer/Decimal80; '+str(exc)) from exc
    hf = fmul(tr(H), z)
    fq = [[dec(float(x)-float(y)) for x, y in zip(row, rr)] for row, rr in zip(z, fmul(H, hf))]
    close(f_saved, fq, kind, label+' saved fsum ledger')
    try:
        close(fq, rounded(reference), kind, label+' fsum/reference evaluation')
    except ValueError as exc:
        raise ValueError('STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: '+label+' fsum/Decimal80; '+str(exc)) from exc
    p_ratio = float_ratio(producer, z, kind)
    d_ratio = float_ratio(rounded(reference), z, kind)
    # Same operands/path definitions, not a cross-path ratio-equality criterion.
    need(saved['producer_einsum_ratio'] == p_ratio, 'STOP_SAVED_RATIO_DEFINITION: '+label)
    need(saved['Decimal80_ratio'] == d_ratio, 'STOP_DECIMAL_RATIO_DEFINITION: '+label)
    need(type(saved['producer_pass']) is bool and type(saved['Decimal80_pass']) is bool, 'STOP_Q_BOOL_SCHEMA')
    need(saved['producer_pass'] == (p_ratio <= 1) and saved['Decimal80_pass'] == (d_ratio <= 1), 'STOP_Q_SAVED_STATUS')
    need((p_ratio <= 1) == (d_ratio <= 1), 'STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED: '+label)
    need((d_ratio <= 1) == expected, 'STOP_Q_CLASSIFICATION: '+label)
    return {'saved_producer_ratio': p_ratio, 'independent_Decimal80_ratio': d_ratio,
            'cross_path_scalar_equality_required': False, 'expected_pass': expected}


def provenance(data):
    sources = {name: digest(raw(REPO/name)) for name in SOURCES}
    for name in SOURCES:
        need(raw(REPO/name) == process(['git', 'show', SNAPSHOT+':'+name]), 'STOP_SOURCE_SNAPSHOT: '+name)
    receipt = load(data[ROOT/'execution_receipt.json'])
    a = load(data[TEST/'test_receipt.json'])
    for r, status, operation in ((receipt, 'succeeded', 'fixed_C1_C3_synthetic_repair'), (a, 'passed', 'artificial_unit_tests_only')):
        need(r['status'] == status and r['operation'] == operation and r['source_commit'] == SNAPSHOT, 'STOP_RECEIPT_IDENTITY')
        need(r['budget_seconds'] == 60 and 0 <= r['elapsed_seconds'] < 60, 'STOP_ORIGINAL_BUDGET')
        need(r['sources_before_sha256'] == sources == r['sources_after_sha256'], 'STOP_ORIGINAL_SOURCES')
        need(r['thread_environment'] == {k: '1' for k in THREADS}, 'STOP_ORIGINAL_THREADS')
    need(a['actual_qr_calls'] == a['svd_calls'] == 0, 'STOP_A_COUNTERS')
    need(a['test_log_sha256'] == PINNED[TEST/'tests.log'], 'STOP_A_LOG')
    need(receipt['matching_A_receipt_sha256'] == PINNED[TEST/'test_receipt.json'], 'STOP_MATCHING_A')
    names = ('report.json', 'summary.csv', 'q_identity_ratio.png', 'q_identity_ratio.pdf', 'q_identity_ratio.md')
    need(receipt['artifacts_sha256'] == {n: PINNED[ROOT/n] for n in names}, 'STOP_ARTIFACT_MANIFEST')
    need(receipt['qr_calls'] == 3 and receipt['svd_calls'] == 0, 'STOP_B_COUNTERS')
    need(receipt['expected_initialization_logs'] == [dict(logger='matplotlib.font_manager', level='WARNING', message='Matplotlib is building the font cache; this may take a moment.')], 'STOP_HISTORICAL_FONT_LOG')
    return sources


def mapped_sidecar(data):
    original = data[ROOT/'q_identity_ratio.md']
    edits = (
        (b'## Visual grammar and panel guide\n', b'## How to read: visual grammar and panel guide\n'),
        (b'Full primary analytic-p/r ratios and all five image/Pythagoras probes are in report.json and summary.csv.\n',
         b'Full primary analytic-p/r ratios and all five image/Pythagoras probe details are in report.json. summary.csv contains case-level summary columns only; it does not contain the five-probe details.\n'),
    )
    expected = original
    for old, new in edits:
        need(original.count(old) == 1, 'STOP_SIDECAR_EDIT_CARDINALITY')
        expected = expected.replace(old, new, 1)
    companion = ROOT/'q_identity_ratio.sidecar_v01.md'
    need(data[companion] == expected, 'STOP_SIDECAR_DERIVATION')
    text = expected.decode().strip()
    need(len(text) >= 400 and all(p in text.lower() for p in ('how to read', 'data provenance', 'limitation')), 'STOP_MAPPED_SIDECAR_CONTENT')
    r = load(data[ROOT/'q_identity_ratio.sidecar_v01.receipt.json'])
    fixed = dict(status='sidecar_derivative_written_not_accepted', operation='E019-D02-sidecar-v01-two-text-edits-only',
                 script=str(REPO/'scripts/aa2024_d02_sidecar_v01.py'), script_sha256=PINNED[REPO/'scripts/aa2024_d02_sidecar_v01.py'],
                 source=str(ROOT/'q_identity_ratio.md'), source_sha256_before=PINNED[ROOT/'q_identity_ratio.md'],
                 source_sha256_after=PINNED[ROOT/'q_identity_ratio.md'], output=str(companion), output_sha256=PINNED[companion],
                 replacements=2, companion_for=[str(ROOT/'q_identity_ratio.png'), str(ROOT/'q_identity_ratio.pdf')],
                 official_same_stem_sidecar=str(ROOT/'q_identity_ratio.md'),
                 official_directory_validator_run=False, independent_acceptance_run=False, thread_env={k: '1' for k in THREADS})
    need(all(r.get(k) == v for k, v in fixed.items()), 'STOP_COMPANION_RECEIPT')
    need(0 <= r['elapsed_before_receipt_write_seconds'] < 60, 'STOP_COMPANION_BUDGET')
    return text


def audit_case(row):
    name = row['case']
    shapes = dict(H=(16, 3), Lr=(16, 5), A=(16, 16), V=(16, 5), y=(16, 1), clean=(16, 5), g=(16, 1),
                  B=(16, 5), U=(16, 5), T=(5, 5), p=(16, 1), r=(16, 1), p_old=(16, 1), r_old=(16, 1),
                  p_star=(16, 1), r_star=(16, 1), p_actual_U_Decimal80=(16, 1), r_actual_U_Decimal80=(16, 1))
    e = row['evidence']
    m = {k: mat(e[k], *shape) for k, shape in shapes.items()}
    H, L, y, U, T, p, r = (m[k] for k in ('H', 'Lr', 'y', 'U', 'T', 'p', 'r'))
    need(row['retained_modes'] == 5 and row['candidate_Q_applications'] == 1 and row['qr_calls'] == 1, 'STOP_MODE_COUNTER_METADATA')
    mechanisms = dict(C1='clean', C2='prescribed_A_leakage', C3='prescribed_factor_leakage')
    need(row['input_mechanism'] == mechanisms[name], 'STOP_MECHANISM_LABEL')
    need(row['old_Q_role'] == ('clean_baseline' if name == 'C1' else 'predeclared_negative_control'), 'STOP_NEGATIVE_ROLE')
    for key, columns in (('H', range(3)), ('clean', range(3, 8)), ('V', range(8, 13)), ('g', [13])):
        for i in range(16):
            for j, column in enumerate(columns):
                need(m[key][i][j] == Decimal(-1 if (i & column).bit_count() % 2 else 1)/4, 'STOP_SAVED_DYADIC_DEFINITION')
    need(e['s'] == [1., 2.**-4, 2.**-12, 2.**-24, 2.**-32], 'STOP_SAVED_MODES')
    c = e['constants']
    t = 2.**-20
    need(c == dict(t=t, c=(1-t*t)/(1+t*t), a=2*t/(1+t*t), tau=1e-12, retained_modes=5), 'STOP_CONSTANTS')
    expected_L = [[x for x in rr] for rr in m['clean']]
    if name != 'C1':
        for i in range(16):
            expected_L[i][4] = dec(c['c'])*m['clean'][i][4]+dec(c['a'])*H[i][1]
    close(L, expected_L, 'matrix', 'saved Lr definition')
    a_input = L if name == 'C2' else m['clean']
    close(m['A'], mul([[x*dec(e['s'][j]) for j, x in enumerate(rr)] for rr in a_input], tr(m['V'])), 'matrix', 'saved A definition')
    pstar = [[(rr[0]+rr[4])*dec(2.**-8)] for rr in m['clean']]
    rstar = [[-rr[0]*dec(2.**-12)] for rr in m['g']]
    close(y, sub(pstar, rstar), 'vector', 'fixed input y')
    close(m['p_star'], pstar, 'vector', 'saved analytic p')
    close(m['r_star'], rstar, 'vector', 'saved analytic r')
    close(mul(tr(H), H), eye(3), 'matrix', 'H Gram')
    close(m['B'], q(H, L), 'matrix', 'B=QLr')
    close(mul(U, T), m['B'], 'matrix', 'UT=B (no new QR)')
    close(mul(tr(U), U), eye(5), 'matrix', 'U Gram')
    need(all(T[i][i] > 0 for i in range(5)), 'STOP_POSITIVE_DIAGONAL')
    close([[T[i][j] if i > j else Decimal(0) for j in range(5)] for i in range(5)], [[Decimal(0)]*5 for _ in range(5)], 'matrix', 'T triangular')
    eta = max(sum((abs(Decimal(int(i == j))-T[i][j]) for j in range(5)), Decimal(0)) for i in range(5))
    need(eta <= Decimal('.5'), 'STOP_ETA_HARD_HALF')
    scalar(row['eta'], eta, 'matrix', 'saved eta')
    p_reference = mul(U, mul(tr(U), y))
    r_reference = sub(p_reference, y)
    close(p, rounded(p_reference), 'vector', 'saved p evaluation')
    close(r, rounded(r_reference), 'vector', 'saved r evaluation')
    close(m['p_actual_U_Decimal80'], p_reference, 'vector', 'actual U Decimal p ledger')
    close(m['r_actual_U_Decimal80'], r_reference, 'vector', 'actual U Decimal r ledger')
    close(sub(p, y), r, 'vector', 'residual definition')
    close(mul(tr(U), r), [[Decimal(0)] for _ in range(5)], 'vector', 'normal equation')
    primary = [close(p, pstar, 'vector', 'analytic p'), close(r, rstar, 'vector', 'analytic r')]
    close(m['p_old'], mul(L, mul(tr(L), y)), 'vector', 'old p from saved Lr')
    close(m['r_old'], sub(m['p_old'], y), 'vector', 'old r definition')
    checks = row['checks']
    for key in ('H_gram', 'qr_reconstruction', 'qr_orthogonality', 'normal_equation', 'residual_definition', 'primary_p', 'primary_r', 'B_reference', 'p_full_Decimal80', 'r_full_Decimal80'):
        need(0 <= dec(checks[key]) <= 1, 'STOP_SAVED_CHECK_STATUS: '+key)
    for key in ('UT_paths', 'UTy_paths', 'p_product_paths'):
        need(set(checks[key]) == {'float_vs_Decimal80_ratio', 'fsum_vs_Decimal80_ratio'} and all(0 <= dec(v) <= 1 for v in checks[key].values()), 'STOP_SAVED_PRODUCT_PATH_STATUS')
    for key, target, kind in (('input_y_Q', y, 'vector'), ('U_Q', U, 'matrix'), ('p_Q', p, 'vector'), ('r_Q', r, 'vector')):
        qrecord(H, target, checks[key], kind, True, key)
    old = qrecord(H, m['r_old'], row['old_r_Q'], 'vector', name == 'C1', 'old_r_Q')
    if name == 'C1':
        close(p, m['p_old'], 'vector', 'C1 old p preserved')
        close(r, m['r_old'], 'vector', 'C1 old r preserved')
        need(all(0 <= dec(checks[k]) <= 1 for k in ('C1_p_preserved', 'C1_r_preserved')), 'STOP_C1_SAVED_STATUS')
    probes = row['probes']
    need(isinstance(probes, list) and len(probes) == 5 and [a['mode'] for a in probes] == [1, 2, 3, 4, 5], 'STOP_PROBE_SCHEMA')
    for j, probe in enumerate(probes):
        b, image, d, total = (mat(probe[k], 16, 1) for k in ('b', 'image', 'd', 'residual'))
        expected_b = [[rr[j]*dec(2.**-8)] for rr in m['clean']]
        close(b, expected_b, 'vector', 'probe b')
        close(image, mul(U, mul(tr(U), b)), 'vector', 'probe image evaluation')
        close(image, b, 'vector', 'probe in span')
        close(d, sub(b, p), 'vector', 'probe d')
        close(total, sub(b, y), 'vector', 'probe residual')
        close(total, add(d, r), 'vector', 'probe residual addition')
        cross = 2*mul(tr(r), d)[0][0]
        scalar(cross, 0, 'square', 'probe orthogonal cross')
        scalar(probe['cross_mm2'], cross, 'square', 'saved cross')
        scalar(square(total), square(r)+square(d), 'square', 'probe Pythagoras')
        gap = dec((1 if j in (0, 4) else 3)*2.**-16)
        total_truth = gap+dec(2.**-24)
        for key, reference in (('gap_square_mm2', square(d)), ('total_square_mm2', square(total)),
                               ('analytic_gap_square_mm2', gap), ('analytic_total_square_mm2', total_truth)):
            scalar(probe[key], reference, 'square', 'saved '+key)
        scalar(square(d), gap, 'square', 'analytic gap')
        scalar(square(total), total_truth, 'square', 'analytic total')
        for key in ('image_ratio', 'addition_ratio', 'cross_ratio', 'Pythagoras_ratio'):
            need(0 <= dec(probe[key]) <= 1, 'STOP_SAVED_PROBE_STATUS')
    scalar(square(r), dec(2.**-24), 'square', 'analytic residual floor')
    return dict(case=name, old_Q=old, new_Q=checks['r_Q']['producer_einsum_ratio'],
                independent_primary_p_r_ratios=primary, independent_eta=str(eta), probes_checked=5)


def png_structure(data):
    need(data[:8] == b'\x89PNG\r\n\x1a\n', 'STOP_PNG_SIGNATURE')
    offset, types, size = 8, [], None
    while offset < len(data):
        need(offset+12 <= len(data), 'STOP_PNG_TRUNCATED')
        length = struct.unpack('>I', data[offset:offset+4])[0]
        end = offset+12+length
        need(end <= len(data), 'STOP_PNG_LENGTH')
        kind, payload = data[offset+4:offset+8], data[offset+8:offset+8+length]
        need(zlib.crc32(kind+payload) & 0xffffffff == struct.unpack('>I', data[end-4:end])[0], 'STOP_PNG_CRC')
        types.append(kind)
        if kind == b'IHDR':
            need(len(types) == 1 and length == 13, 'STOP_PNG_IHDR')
            size = struct.unpack('>II', payload[:8])
        offset = end
        if kind == b'IEND':
            need(length == 0 and offset == len(data), 'STOP_PNG_IEND')
            break
    need(types[0] == b'IHDR' and types[-1] == b'IEND' and b'IDAT' in types and size == (1836, 986), 'STOP_PNG_STRUCTURE')
    return size


def main():
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, max(.001, 60-(time.monotonic()-START)))
    logging.getLogger().addHandler(WarningStop(logging.WARNING))
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-script-sha256', required=True)
    args = parser.parse_args()
    need(Path.cwd() == REPO and REPO.resolve() == REPO, 'STOP_WORKTREE')
    need(all(os.environ.get(k) == '1' for k in THREADS) and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'STOP_ENVIRONMENT')
    need(sys.flags.isolated and sys.flags.dont_write_bytecode and sys.warnoptions == ['error'], 'STOP_PYTHON_FLAGS')
    script = REPO/'scripts/aa2024_d02_remaining_readonly.py'
    script_bytes = raw(script)
    need(digest(script_bytes) == args.expected_script_sha256, 'STOP_AUDIT_SCRIPT_IDENTITY')
    need(not process(['git', 'status', '--porcelain']), 'STOP_DIRTY_WORKTREE')
    head = process(['git', 'rev-parse', 'HEAD']).decode().strip()
    data = {}
    for path, expected in PINNED.items():
        data[path] = raw(path)
        need(digest(data[path]) == expected, 'STOP_PINNED_IDENTITY: '+str(path))
    sources = provenance(data)
    COMPLETED.append('fixed artifact/source/A/B provenance and historical font log')
    sidecar = mapped_sidecar(data)
    COMPLETED.append('explicit PNG/PDF to companion mapping and two-edit derivation')
    report = load(data[ROOT/'report.json'])
    need(report['protocol'] == 'E019-D02_v0.1' and report['domain'] == 'synthetic' and report['status'] == 'candidate_checks_passed', 'STOP_REPORT_IDENTITY')
    need(report['tolerances'] == dict(rtol=1e-12, matrix=1e-12, vector=1e-15, square=1e-18), 'STOP_TOLERANCES')
    need(report['qr_calls'] == 3 and report['svd_calls'] == report['forbidden_calls'] == 0, 'STOP_REPORTED_COUNTERS')
    rows = report['cases']
    need([r['case'] for r in rows] == ['C1', 'C2', 'C3'], 'STOP_CASE_ORDER')
    fields = ['case', 'old_Q_ratio', 'new_Q_ratio', 'p_star_ratio', 'r_star_ratio', 'eta', 'retained_modes']
    reader = csv.DictReader(io.StringIO(data[ROOT/'summary.csv'].decode()))
    need(reader.fieldnames == fields, 'STOP_CSV_COLUMNS')
    table = list(reader)
    need(len(table) == 3, 'STOP_CSV_ROWS')
    results = []
    with localcontext() as context:
        context.prec = 80
        for row, csv_row in zip(rows, table):
            name = row['case']
            expected = [row['old_r_Q']['producer_einsum_ratio'], row['checks']['r_Q']['producer_einsum_ratio'],
                        row['checks']['primary_p'], row['checks']['primary_r'], row['eta'], row['retained_modes']]
            need(csv_row['case'] == name and all(float(csv_row[k]) == value for k, value in zip(fields[1:], expected)), 'STOP_CSV_SERIALIZATION')
            # Same frozen display row, not a new numerical interpretation.
            line = f"- {name}: old={expected[0]!r}; new={expected[1]!r}; analytic p ratio={expected[2]!r}; eta={expected[4]!r}"
            need(line in sidecar, 'STOP_SIDECAR_DISPLAY_VALUES')
            results.append(audit_case(row))
            COMPLETED.append(name+' saved identities, analytic projection, Q paths and five probes')
            within()
    left, right = rows[1]['evidence'], rows[2]['evidence']
    need(left['A'] != right['A'] and all(left[k] == right[k] for k in ('Lr', 'y', 'p_old', 'r_old')), 'STOP_CROSS_CASE_IDENTITY')
    COMPLETED.append('C2/C3 source distinction and shared candidate inputs')
    png_size = png_structure(data[ROOT/'q_identity_ratio.png'])
    # Parse/metadata only, not rendering or proof of PDF visual equivalence.
    info = process(['/opt/homebrew/bin/pdfinfo', '-isodates', str(ROOT/'q_identity_ratio.pdf')]).decode()
    entries = dict(line.split(':', 1) for line in info.splitlines() if ':' in line)
    need(entries.get('Pages', '').strip() == '1' and entries.get('Encrypted', '').strip() == 'no', 'STOP_PDF_METADATA')
    size = entries.get('Page size', '').split()
    need(len(size) >= 4 and size[1] == 'x' and size[3] == 'pts', 'STOP_PDF_PAGE_SIZE_SCHEMA')
    need((float(size[0]), float(size[2])) == (777.6, 417.6), 'STOP_PDF_PAGE_SIZE')
    COMPLETED.append('PNG signature/chunk CRC/dimensions and PDF parse/page metadata (not visual QA)')
    for path, expected in PINNED.items():
        need(digest(raw(path)) == expected, 'STOP_FINAL_ARTIFACT_CHANGED')
    need(all(digest(raw(REPO/n)) == value for n, value in sources.items()), 'STOP_FINAL_SOURCE_CHANGED')
    need(raw(script) == script_bytes and not process(['git', 'status', '--porcelain']), 'STOP_FINAL_SCRIPT_OR_WORKTREE')
    need(process(['git', 'rev-parse', 'HEAD']).decode().strip() == head, 'STOP_FINAL_HEAD')
    within()
    print(json.dumps(dict(status='PASS_SAVED_SYNTHETIC_ARITHMETIC_AND_MAPPED_SIDECAR_PENDING_PNG',
                          completed=COMPLETED, cases=results, artifact_sha256={str(p): h for p, h in PINNED.items()},
                          source_sha256=sources, head=head, png_size=png_size, pdfinfo=info,
                          companion=str(ROOT/'q_identity_ratio.sidecar_v01.md'), original_directory_validator_run=False,
                          limitations=['PNG independent visual check still pending', 'PDF parse/metadata only, no PDF visual comparison',
                                       'reported producer counters are not independent historical process audit',
                                       'not bitwise certification of unsaved intermediate einsum products or all scalar ratios',
                                       'no D01/C0/original Qr or real E019 cause claim; no physical inversion/prediction validity',
                                       'original same-stem sidecar unchanged; no official directory-validator pass claimed'],
                          elapsed_before_stdout_seconds=time.monotonic()-START), indent=2), flush=True)
    within()
    signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps(dict(status='STOP_AT_FIRST_UNEXPECTED_NO_RETRY', error=str(exc), completed=COMPLETED)), flush=True)
        raise SystemExit(1)
