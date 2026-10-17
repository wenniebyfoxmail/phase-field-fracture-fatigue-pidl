"""Targeted artificial binding/percent/tolerance/closed-entry checks ONLY.

No full snapshot, CSV parsing, real reader, field, figure or old suite run.
Tolerance probes stop at a deliberate sentinel immediately after the actual
snapshot comparison, before summary contents or CSV can be supplied.
"""
import sys

if sys.flags.optimize != 0:
    raise RuntimeError('optimized Python is forbidden for the binding mock worker')

import argparse
import copy
import json
import math
import os
from pathlib import Path
import stat
from unittest import mock

from s04_late_adapter_checks import protect, rejected


class ReachedAfterRatio(Exception):
    """Expected MOCK_ONLY probe boundary, NOT a completed snapshot."""


class ScalarProbe:
    def __init__(self, adapter, ratio):
        self.a = adapter
        self.calls = []
        self.tokens = {p: (1, i+1, stat.S_IFREG | 0o444, 1, 1000+i)
                       for i, p in enumerate(adapter.SOURCES)}
        self.text = {
            adapter.INVENTORY: json.dumps(dict(
                status='VERIFIED_SAVED_OUTPUTS', run_id='S04-E021-R001',
                code_commit=adapter.FIT_COMMIT, frozen_files=[dict(
                    path=adapter.CSV, bytes=1, mtime_ns=self.tokens[adapter.CSV][4])])),
            adapter.VERIFICATION: json.dumps(dict(
                run_id='S04-E021-REPLAY-R001', runtime_commit=adapter.REPLAY_COMMIT,
                rows=357, counts=adapter.core.COUNTS, late_ratio=ratio), allow_nan=False),
        }
        for path, text in self.text.items():
            t = list(self.tokens[path])
            t[3] = len(text.encode('utf-8'))
            self.tokens[path] = tuple(t)

    def metadata(self, path):
        assert path in self.tokens
        self.calls.append(('metadata', path))
        return self.tokens[path]

    def read(self, path, before):
        assert self.tokens[path] == before
        if path == self.a.SUMMARY:
            self.calls.append(('boundary', path))
            raise ReachedAfterRatio()
        assert path in self.text, 'CSV/other contents forbidden even in this mock'
        self.calls.append(('read', path))
        return self.text[path]


def adjacent_boundary(center, direction, tolerance):
    candidate = center+direction*tolerance
    if abs(candidate-center) <= tolerance:
        inside = candidate
        outside = math.nextafter(candidate, math.inf if direction > 0 else -math.inf)
    else:
        outside = candidate
        inside = math.nextafter(candidate, center)
    assert abs(inside-center) <= tolerance < abs(outside-center)
    assert math.nextafter(inside, math.inf if direction > 0 else -math.inf) == outside
    return inside, outside


def run(out):
    protect(out)  # Reuse only the audit hook and rejection helper, NOT old run().
    import s04_late_adapter as a
    import s04_late_binding_guard as job
    assert out == a.BASE/'engineering'/job.OUTPUT_NAME and out.is_dir()
    assert os.environ.get('S04_BINDING_PARENT') == str(os.getppid()), 'use fixed guard parent'
    code = os.environ.get('S04_BINDING_CODE', '')
    assert len(code) == 40 and all(c in '0123456789abcdef' for c in code)
    assert a.REAL_ACQUISITION_ENABLED is False
    assert a.REAL_VERIFICATION_BINDING == {
        'run_id': ('run_id',), 'runtime_commit': ('code_commit',),
        'rows': ('ordered_unique_rows',), 'counts': ('exact_cycle_counts',),
        'late_ratio': ('u011_C41_plus_RMSE_increase_percent',),
    }
    grant = dict(version=1, action='four_source_readonly_handoff', domain='MOCK_ONLY',
                 code_commit=code, plan_commit=a.core.PLAN_COMMIT, attempt=job.ATTEMPT,
                 output=str(out), sources=list(a.SOURCES), budget=a.BUDGET,
                 fit=False, confirmation=False, engineering_only=True,
                 user_approved_real_execution=False)
    doc = dict(run_id='S04-E021-REPLAY-R001', code_commit=a.REPLAY_COMMIT,
               ordered_unique_rows=357, exact_cycle_counts=dict(a.core.COUNTS),
               u011_C41_plus_RMSE_increase_percent=25.)
    groups = []
    units = []
    for name, percent, expected in (
            ('ZERO_PERCENT', 0, 1.), ('NEGATIVE_PERCENT', -25., .75), ('POSITIVE_PERCENT', 25., 1.25)):
        supplied = dict(doc, u011_C41_plus_RMSE_increase_percent=percent)
        values = a.bound_verification_values(supplied)
        assert values == dict(run_id=doc['run_id'], runtime_commit=doc['code_commit'],
                              rows=357, counts=a.core.COUNTS, late_ratio=expected)
        units.append(dict(case=name, artificial_percent=percent, converted_ratio=values['late_ratio']))
    groups.append('explicit selectors and zero/negative/positive artificial percent conversion')

    type_cases = (('RUN_TYPE', 'run_id', 123), ('COMMIT_TYPE', 'code_commit', None),
                  ('ROWS_BOOL', 'ordered_unique_rows', True),
                  ('COUNT_FLOAT', 'exact_cycle_counts', {'u011': 121.}),
                  ('PERCENT_BOOL', 'u011_C41_plus_RMSE_increase_percent', True),
                  ('PERCENT_STRING', 'u011_C41_plus_RMSE_increase_percent', '25'))
    rejected_types = []
    for name, key, value in type_cases:
        supplied = copy.deepcopy(doc)
        supplied[key] = value
        rejected(lambda: a.bound_verification_values(supplied),
                 'verification percent' if key.endswith('_percent') else 'verification binding types')
        rejected_types.append(name)
    supplied = dict(doc)
    supplied.pop('ordered_unique_rows')
    rejected(lambda: a.bound_verification_values(supplied), 'verification selector missing')
    rejected_types.append('MISSING_ROWS')
    groups.append('six wrong types plus missing explicit row selector reject')

    nonfinite = []
    for name, value in (('NAN', float('nan')), ('NEGATIVE_INFINITY', -float('inf')),
                        ('POSITIVE_INFINITY', float('inf'))):
        supplied = dict(doc, u011_C41_plus_RMSE_increase_percent=value)
        rejected(lambda: a.bound_verification_values(supplied), 'nonfinite saved RMSE increase percent')
        nonfinite.append(name)  # Do not serialize nonfinite numeric values.
    groups.append('NaN and both infinities reject before any snapshot/IO')

    probe_records = []
    def compare(name, ratio, expected, accept):
        probe = ScalarProbe(a, ratio)
        mock_binding = {k: (k,) for k in ('run_id', 'runtime_commit', 'rows', 'counts', 'late_ratio')}
        try:
            a.snapshot(probe, grant=grant, code_commit=code, attempt=job.ATTEMPT,
                       output=str(out), domain='MOCK_ONLY', binding=mock_binding, expected_ratio=expected)
        except ReachedAfterRatio:
            assert accept, name
            observed = 'REACHED_POST_RATIO_BOUNDARY'
        except ValueError as exc:
            assert not accept and str(exc) == 'saved late scalar disagreement', (name, str(exc))
            observed = 'REJECTED_AT_RATIO'
        else:
            raise AssertionError('probe must never complete a snapshot')
        expected_calls = [('metadata', p) for p in a.SOURCES]
        expected_calls += [('read', a.INVENTORY), ('read', a.VERIFICATION)]
        if accept:
            expected_calls.append(('boundary', a.SUMMARY))
        assert probe.calls == expected_calls, name
        probe_records.append(dict(case=name, artificial_ratio=ratio, artificial_reference=expected,
                                  absolute_delta=abs(ratio-expected), tolerance=1e-12,
                                  expected_accept=accept, observed=observed,
                                  csv_contents_read=False, full_snapshot_completed=False))

    tolerance = 1e-12
    for name, ratio, accept in (
            ('TAU_NEXT_BELOW', math.nextafter(tolerance, 0.), True),
            ('TAU_EXACT', tolerance, True),
            ('TAU_NEXT_ABOVE', math.nextafter(tolerance, math.inf), False)):
        compare(name, ratio, 0., accept)
    # This is a Git constant, NOT a value read from a real file. Do not claim
    # center+1e-12 has an exactly 1e-12 floating-point difference at this center.
    center = a.core.KNOWN_REAL_RATIO
    for direction, side in ((-1, 'LOWER'), (1, 'UPPER')):
        inside, outside = adjacent_boundary(center, direction, tolerance)
        compare(side+'_ADJACENT_INSIDE', inside, center, True)
        compare(side+'_ADJACENT_OUTSIDE', outside, center, False)
    converted = a.bound_verification_values(doc)['late_ratio']
    compare('CONVERTED_PERCENT_TO_COMPARATOR', converted, 1.25, True)
    groups.append('actual MOCK snapshot ratio predicate: exact tau, adjacent-float sides and conversion bridge; sentinel stop')

    class NoSourceIO:
        def metadata(self, path):
            raise AssertionError('closed REAL snapshot reached source metadata')
        def read(self, path, before):
            raise AssertionError('closed REAL snapshot reached source read')
    real_grant = dict(grant)
    real_grant.pop('engineering_only')
    real_grant.update(domain='REAL_SAVED_SCALARS', attempt=a.REAL_RUN, output=a.REAL_OUTPUT,
                      user_approved_real_execution=True, independent_code_review='APPROVED')
    rejected(lambda: a.snapshot(NoSourceIO(), grant=real_grant, code_commit=code, attempt=a.REAL_RUN,
                                output=a.REAL_OUTPUT, domain='REAL_SAVED_SCALARS',
                                binding=a.REAL_VERIFICATION_BINDING,
                                expected_ratio=a.core.KNOWN_REAL_RATIO), 'REAL_EXECUTION_DISABLED')
    with mock.patch.object(a, 'ReadOnlyIO', side_effect=AssertionError('native reader constructed')):
        rejected(lambda: a.acquire_real(grant=real_grant, code_commit=code, env={}, auth_path='UNUSED',
                                        output=a.REAL_OUTPUT, actual_parent=os.getppid()),
                 'REAL_EXECUTION_DISABLED')
    assert a.REAL_ACQUISITION_ENABLED is False
    groups.append('both REAL entries reject before metadata/read or native reader construction; switch never enabled')

    assert len(groups) == 5 and len(probe_records) == 8
    record = dict(status='GENERATED_CHECKS_COMPLETED', scope='GENERATED_ENGINEERING_ONLY',
                  attempt_id=job.ATTEMPT, code_commit=code, targeted_check_groups=groups,
                  python_optimize=sys.flags.optimize, python_debug=__debug__,
                  artificial_unit_cases=units, rejected_type_cases=rejected_types,
                  rejected_nonfinite_cases=nonfinite, tolerance_probes=probe_records,
                  real_data_read=False, fitting_invoked=False, real_ready=False,
                  real_acquisition_enabled=False, csv_contents_read=False,
                  full_snapshot_completed=False, old_suite_run=False,
                  limits='pure artificial components and sentinel comparator probes; no full REAL-domain integration or OS stress test')
    with (out/'checks.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
    print(json.dumps(record, indent=2, allow_nan=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve())
