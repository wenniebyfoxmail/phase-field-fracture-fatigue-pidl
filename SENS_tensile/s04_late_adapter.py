"""Four-source read-only adapter; no fit, replay, field loader or real CLI.

Producer schemas come from Git. Verification paths/types were inspected under
a one-file schema-only approval; its late scalar is an RMSE increase percent.
Binding is NOT execution permission: real acquisition remains explicitly off.
"""
import json
import math
import os
from pathlib import Path
import stat

import s04_late_attribution as core

BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021')
CSV = str(BASE/'runs/S04-E021-R001/percycle.csv')
SUMMARY = str(BASE/'replay_runs/S04-E021-REPLAY-R001/summary.json')
VERIFICATION = str(BASE/'control/S04-E021-REPLAY-R001_verification.json')
INVENTORY = str(BASE/'control/S04-E021-R001_saved_output_verification.json')
SOURCES = (CSV, SUMMARY, VERIFICATION, INVENTORY)
FIT_COMMIT = '6aa21e3c469d53c92240c9689d07a3ffb316d67c'
REPLAY_COMMIT = '08242ea1c7a2cf09e4d211c51b946b8ed16cd1ab'
BUDGET = dict(seconds=60, rss_bytes=512*1024**2, output_bytes=5*1024**2)
MAX_BYTES = 1024**2
REAL_VERIFICATION_BINDING = {
    'run_id': ('run_id',),
    'runtime_commit': ('code_commit',),
    'rows': ('ordered_unique_rows',),
    'counts': ('exact_cycle_counts',),
    'late_ratio': ('u011_C41_plus_RMSE_increase_percent',),
}
# Schema-only permission does not authorize any four-source read or analysis.
# Enabling this requires a separately reviewed launcher and execution approval.
REAL_ACQUISITION_ENABLED = False
REAL_RUN = 'S04-E021-LATE-DIAG-R001'  # Proposed only; not an approved run.
REAL_OUTPUT = str(BASE/'late_attribution_runs'/REAL_RUN)
require = core.require


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def constant(value):
        raise ValueError('nonfinite JSON constant '+value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def token(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns)


def regular(t, path):
    require(len(t) == 5 and stat.S_ISREG(t[2]), 'regular file required: '+path)
    require(0 < t[3] <= MAX_BYTES, 'bounded scalar source required')


class ReadOnlyIO:
    """Exact allowlist, no directory scans, hashes or implicit filename probes.

    fstat binds each O_RDONLY|O_NOFOLLOW descriptor to the admitted path token;
    before/after path and descriptor checks detect replacement/metadata drift.
    These metadata checks are NOT content authentication or an OS sandbox.
    """
    def _path(self, path):
        require(path in SOURCES, 'source outside four-file allowlist')
        p = Path(path)
        require(str(p.resolve(strict=True)) == path, 'symlink/alias source forbidden')
        return p

    def metadata(self, path):
        t = token(self._path(path).lstat())
        regular(t, path)
        return t

    def read(self, path, before):
        self._path(path)
        require(self.metadata(path) == before, 'source changed before open')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            require(token(os.fstat(fd)) == before, 'descriptor/path mismatch')
            data = bytearray()
            while len(data) <= MAX_BYTES:
                block = os.read(fd, min(65536, MAX_BYTES+1-len(data)))
                if not block:
                    break
                data.extend(block)
            require(len(data) == before[3] and len(data) <= MAX_BYTES, 'size/read mismatch')
            require(token(os.fstat(fd)) == before, 'descriptor changed while reading')
        finally:
            os.close(fd)
        require(self.metadata(path) == before, 'path changed while reading')
        return bytes(data).decode('utf-8')


def binding_value(doc, keys):
    require(isinstance(keys, (list, tuple)) and keys, 'explicit verification selector required')
    value = doc
    for key in keys:
        require(isinstance(key, str) and isinstance(value, dict) and key in value,
                'verification selector missing; no recursive guessing')
        value = value[key]
    return value


def bound_verification_values(doc):
    """Pure schema adapter, NO IO. Percent -> ratio only on supplied values.

    This function was not applied to real values during the schema-only step.
    Identity/row counts and the frozen ratio tolerance are checked by snapshot.
    """
    values = {key: binding_value(doc, path) for key, path in REAL_VERIFICATION_BINDING.items()}
    require(type(values['run_id']) is str and type(values['runtime_commit']) is str and
            type(values['rows']) is int and type(values['counts']) is dict and
            all(type(v) is int for v in values['counts'].values()), 'verification binding types')
    require(type(values['late_ratio']) in (int, float), 'verification percent must be numeric, not bool/string')
    percent = core.finite(values['late_ratio'], 'saved RMSE increase percent')
    values['late_ratio'] = core.finite(1.0+percent/100.0, 'converted saved late ratio')
    return values


def check_grant(grant, *, code_commit, attempt, output, domain):
    """Machine interlock only: cannot prove that a human approved an action."""
    require(domain in ('MOCK_ONLY', 'REAL_SAVED_SCALARS'), 'grant domain')
    require(isinstance(code_commit, str) and len(code_commit) == 40 and
            all(c in '0123456789abcdef' for c in code_commit), 'full code commit')
    expected = dict(version=1, action='four_source_readonly_handoff', domain=domain,
                    code_commit=code_commit, plan_commit=core.PLAN_COMMIT,
                    attempt=attempt, output=output, sources=list(SOURCES), budget=BUDGET,
                    fit=False, confirmation=False)
    extra = {'engineering_only', 'user_approved_real_execution'} if domain == 'MOCK_ONLY' else {
        'user_approved_real_execution', 'independent_code_review'}
    require(isinstance(grant, dict) and set(grant) == set(expected) | extra and
            all(grant.get(k) == v for k, v in expected.items()),
            'authorization scope mismatch')
    if domain == 'MOCK_ONLY':
        require(grant.get('engineering_only') is True and
                grant.get('user_approved_real_execution') is False, 'mock cannot grant real access')
    else:
        require(attempt == REAL_RUN and output == REAL_OUTPUT and
                grant.get('user_approved_real_execution') is True and
                grant.get('independent_code_review') == 'APPROVED', 'separate real approval required')


def prepare_handoff(auth_path, output, *, parent_pid, attempt, code_commit):
    """Resolve once in parent cwd. No file reads or source metadata access."""
    require(type(parent_pid) is int and parent_pid > 0, 'parent PID')
    auth = str(Path(auth_path).resolve())
    out = str(Path(output).resolve())
    return dict(authorization=auth, output=out,
                env=dict(S04_LATE_AUTH=auth, S04_LATE_OUTPUT=out,
                         S04_LATE_PARENT=str(parent_pid), S04_LATE_ATTEMPT=attempt,
                         S04_LATE_CODE=code_commit))


def check_child_handoff(auth_path, output, env, *, actual_parent, attempt, code_commit):
    require(Path(auth_path).is_absolute() and Path(output).is_absolute(), 'absolute child paths required')
    expected = dict(S04_LATE_AUTH=str(auth_path), S04_LATE_OUTPUT=str(output),
                    S04_LATE_PARENT=str(actual_parent), S04_LATE_ATTEMPT=attempt,
                    S04_LATE_CODE=code_commit)
    require(all(env.get(k) == v for k, v in expected.items()), 'parent/child handoff mismatch')


def decode_child_grant(auth_path, output, env, *, actual_parent, attempt, code_commit, read_auth):
    """Read only the explicit authorization after verifying absolute handoff.
    read_auth is supplied by a future reviewed launcher, or a mock callback.
    It is not the four-source reader and never infers a filename from payloads.
    """
    check_child_handoff(auth_path, output, env, actual_parent=actual_parent,
                        attempt=attempt, code_commit=code_commit)
    text = read_auth(str(auth_path))
    require(isinstance(text, str) and len(text.encode('utf-8')) <= 65536, 'bounded authorization text')
    return strict_json(text)


def snapshot(io, *, grant, code_commit, attempt, output, domain, binding, expected_ratio):
    """Authorization and explicit schema binding MUST precede any source IO.

    This function never opens an auth path, writes a file, or calls describe().
    The caller supplies the already decoded grant and a separately supervised
    reader. Mock IO uses the SAME four logical names but no real files.
    """
    check_grant(grant, code_commit=code_commit, attempt=attempt, output=output, domain=domain)
    if domain == 'MOCK_ONLY':
        # The supplied native reader (including subclasses) must never be
        # admitted by a mock grant. This interlock is not an OS sandbox for
        # arbitrary caller-provided Python objects.
        require(not isinstance(io, ReadOnlyIO), 'MOCK_ONLY forbids native source reader')
    names = {'run_id', 'runtime_commit', 'rows', 'counts', 'late_ratio'}
    require(isinstance(binding, dict) and set(binding) == names, 'SCHEMA_BINDING_REQUIRED')
    if domain == 'REAL_SAVED_SCALARS':
        require(REAL_ACQUISITION_ENABLED, 'REAL_EXECUTION_DISABLED')
        require(REAL_VERIFICATION_BINDING is not None and binding == REAL_VERIFICATION_BINDING,
                'SCHEMA_BINDING_REQUIRED')
        require(expected_ratio == core.KNOWN_REAL_RATIO, 'frozen real ratio required')
    expected_ratio = core.finite(expected_ratio, 'expected ratio')
    require(expected_ratio >= 0, 'nonnegative ratio')
    before = {path: io.metadata(path) for path in SOURCES}
    for path, t in before.items():
        regular(t, path)
    require(before[CSV][2] & 0o222 == 0, 'original CSV must be read-only')
    audit = strict_json(io.read(INVENTORY, before[INVENTORY]))
    require(audit['status'] == 'VERIFIED_SAVED_OUTPUTS' and
            audit['run_id'] == 'S04-E021-R001' and audit['code_commit'] == FIT_COMMIT,
            'original saved-output audit identity')
    matches = [v for v in audit['frozen_files'] if v.get('path') == CSV]
    require(len(matches) == 1, 'unique original CSV inventory entry required')
    entry = matches[0]
    require(type(entry['bytes']) is int and type(entry['mtime_ns']) is int and
            entry['bytes'] == before[CSV][3] and entry['mtime_ns'] == before[CSV][4],
            'original CSV metadata mismatch')
    verification = strict_json(io.read(VERIFICATION, before[VERIFICATION]))
    values = (bound_verification_values(verification) if domain == 'REAL_SAVED_SCALARS' else
              {key: binding_value(verification, selector) for key, selector in binding.items()})
    require(values['run_id'] == 'S04-E021-REPLAY-R001' and
            values['runtime_commit'] == REPLAY_COMMIT and type(values['rows']) is int and
            values['rows'] == 357 and values['counts'] == core.COUNTS, 'replay verification identity')
    ratio = core.finite(values['late_ratio'], 'saved late ratio')
    require(abs(ratio-expected_ratio) <= 1e-12, 'saved late scalar disagreement')
    summary = strict_json(io.read(SUMMARY, before[SUMMARY]))
    require(summary['run_id'] == 'S04-E021-REPLAY-R001' and
            summary['code_commit'] == REPLAY_COMMIT and
            summary['status'] == 'REPLAY_ARITHMETIC_MATCH' and
            summary['original_verdict'] == 'DIRECTIONAL_DEVELOPMENT_GAIN' and
            summary['fitting_invoked'] is False, 'frozen summary identity')
    folds = summary['folds']
    require(len(folds) == 4 and len({f['holdout'] for f in folds}) == 4 and
            {f['holdout'] for f in folds} == set(core.COUNTS), 'summary fold coverage')
    background = []
    for fold in folds:
        means = fold['stratum_mse']
        require(len(means) == 3 and all(len(row) == 2 for row in means), 'summary three strata')
        require(all(math.isfinite(float(v)) and float(v) >= 0 for row in means for v in row),
                'summary MSE finite/nonnegative')
        if fold['holdout'] != 'u011':
            background.append(dict(holdout=fold['holdout'], V0_saved_late_mse=means[2][0],
                                   V1_saved_late_mse=means[2][1], role='saved background only'))
    rows = core.parse_csv(io.read(CSV, before[CSV]))
    core.validate(rows)  # Coverage only; NO new decomposition/R/G/Q/other-case means.
    after = {path: io.metadata(path) for path in SOURCES}
    require(before == after, 'source changed across snapshot')
    return dict(rows=rows, expected_ratio=expected_ratio, background=background,
                source_metadata={p: list(t) for p, t in before.items()}, domain=domain,
                metadata_only_not_content_hash=True, fitting_invoked=False,
                real_data_read=domain == 'REAL_SAVED_SCALARS')


def acquire_real(*, grant, code_commit, env, auth_path, output, actual_parent):
    # Schema binding alone must not enable even source stat().
    require(REAL_ACQUISITION_ENABLED, 'REAL_EXECUTION_DISABLED')
    require(REAL_VERIFICATION_BINDING is not None, 'SCHEMA_BINDING_REQUIRED')
    check_child_handoff(auth_path, output, env, actual_parent=actual_parent,
                        attempt=REAL_RUN, code_commit=code_commit)
    return snapshot(ReadOnlyIO(), grant=grant, code_commit=code_commit, attempt=REAL_RUN,
                    output=output, domain='REAL_SAVED_SCALARS',
                    binding=REAL_VERIFICATION_BINDING, expected_ratio=core.KNOWN_REAL_RATIO)


if __name__ == '__main__':
    raise SystemExit('No real CLI. Real execution disabled; launcher review and separate approval required.')
