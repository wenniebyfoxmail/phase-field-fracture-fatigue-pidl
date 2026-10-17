"""2f0ff22 restricted real saved-scalar attribution worker, never a fit.

No scientific IO on import. A reviewed guard and separate human execution
approval are required; provenance references are not human authentication.
"""
import sys

if sys.flags.optimize != 0:
    raise RuntimeError('optimized Python is forbidden for real attribution')

import argparse
import csv
import json
import os
from pathlib import Path
import stat

import s04_late_adapter as a

SCOPE = 'FOUR_SOURCE_READONLY_LATE_ATTRIBUTION'
FILES = {'authorization.json', 'diagnostic.csv', 'summary.json', 'diagnostic.png',
         'README_analysis.md', 'analysis.log', 'guard_receipt.json'}
CACHE_ENV = {'MPLCONFIGDIR': 'cache/matplotlib', 'XDG_CACHE_HOME': 'cache/xdg',
             'TMPDIR': 'cache/tmp'}
# Exact constant messages in the unchanged core only. Never persist arbitrary
# exception text, values, parser excerpts or inferred causes.
DESCRIBE_FAILURE_CODES = {
    'unidentifiable late baseline': 'LATE_BASELINE_UNIDENTIFIABLE',
    'known late ratio disagreement': 'KNOWN_LATE_RATIO_DISAGREEMENT',
    'MSE decomposition closure': 'MSE_DECOMPOSITION_CLOSURE_FAILED',
    'nonfinite sum': 'NONFINITE_DECOMPOSITION_SUM',
    'count closure': 'CYCLE_COUNT_CLOSURE_FAILED',
    'nonfinite reference ratio': 'NONFINITE_REFERENCE_RATIO',
    'negative MSE': 'NEGATIVE_MSE',
    'nonfinite V0 MSE': 'NONFINITE_V0_MSE',
    'nonfinite V1 MSE': 'NONFINITE_V1_MSE',
}


def safe_error(exc, phase):
    record = dict(type=type(exc).__name__, stage=phase)
    if phase == 'DESCRIBE':
        code = (DESCRIBE_FAILURE_CODES.get(str(exc)) if type(exc) is ValueError else
                'NUMERIC_OVERFLOW' if type(exc) is OverflowError else None)
        if code is not None:
            record['reason_code'] = code
    return record


def full_commit(code):
    a.require(type(code) is str and len(code) == 40 and
              all(c in '0123456789abcdef' for c in code), 'full reviewed commit required')


def grant_for(code, refs):
    full_commit(code)
    a.check_execution_refs(refs, code)
    return dict(version=2, action='four_source_readonly_attribution',
                domain='REAL_SAVED_SCALARS', code_commit=code, plan_commit=a.core.PLAN_COMMIT,
                scope_commit=a.ATTR_SCOPE_COMMIT, attempt=a.ATTR_RUN, output=a.ATTR_OUTPUT,
                sources=list(a.SOURCES), budget=dict(a.BUDGET), fit=False, confirmation=False,
                user_approved_real_execution=True, independent_code_review='APPROVED',
                execution_references=dict(refs))


def read_authorization(path):
    """Only this new Run's bounded control file, never a science source."""
    p = Path(path)
    a.require(str(p) == str(Path(a.ATTR_OUTPUT)/'authorization.json') and
              str(p.resolve(strict=True)) == str(p), 'fixed canonical authorization path')
    st = p.lstat()
    before = a.token(st)
    a.require(stat.S_ISREG(st.st_mode) and 0 < st.st_size <= 65536 and
              st.st_mode & 0o222 == 0 and st.st_nlink == 1, 'bounded read-only authorization')
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        a.require(a.token(os.fstat(fd)) == before, 'authorization descriptor mismatch')
        data = bytearray()
        while len(data) <= 65536:
            block = os.read(fd, min(65536, 65537-len(data)))
            if not block:
                break
            data.extend(block)
        a.require(len(data) == before[3] and len(data) <= 65536 and
                  a.token(os.fstat(fd)) == before, 'authorization size/descriptor drift')
    finally:
        os.close(fd)
    a.require(a.token(p.lstat()) == before, 'authorization path drift')
    return bytes(data).decode('utf-8')


def report(late, summary, cumulative, out, *, on_plot):
    """Real report consumes this invocation's original describe result only.

    No reader, recomputation, directory creation or engineering-label override.
    Called only after authorised four-source acquisition and describe().
    """
    with (out/'diagnostic.csv').open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(late[0]))
        writer.writeheader()
        writer.writerows(late)
    # Font discovery, rendering and all temporary caches stay in the budgeted
    # worker; parent supplies fixed run-owned paths before process startup.
    on_plot()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
    try:
        left, right = axes
        left.bar([r['cycle'] for r in late], [r['D'] for r in late], width=.85,
                 color=['#b35806' if r['D'] > 0 else '#2166ac' for r in late])
        left.axhline(0, color='black', lw=1)
        left.set(xlabel='Physical cycle (all 81)',
                 ylabel='V1 MSE - V0 MSE\n(raw archive units squared)',
                 title='A | Signed difference; zero = V1 equals V0')
        if cumulative:
            right.step(range(1, 82), cumulative, where='post', color='#336d8b', lw=1.4)
            right.axhline(.5, color='gray', ls='--', lw=1)
            right.axvline(summary['k50'], color='#b35806', ls=':', lw=1)
            right.text(.98, .08, 'k50 = '+str(summary['k50'])+'/81',
                       transform=right.transAxes, ha='right')
        else:
            right.text(.5, .5, 'Positive excess unidentifiable\nNo normalised curve; stop',
                       transform=right.transAxes, ha='center')
        right.set(xlabel='Rank (positive excess descending; ties: cycle ascending)',
                  ylabel='Cumulative share of S_plus', ylim=(0, 1.03),
                  title='B | 50% definition, not a success threshold')
        fig.suptitle(a.ATTR_RUN+' | U0.11 C41-121 | s4 / horizon 0\n'
                     'Viewed synthetic development; descriptive error localisation, NOT physical cause',
                     fontsize=10)
        with (out/'diagnostic.png').open('xb') as file:
            fig.savefig(file, format='png', dpi=120)
    finally:
        plt.close(fig)
    with (out/'README_analysis.md').open('x') as file:
        file.write('# Analysis: S04-E021 late saved-scalar attribution\n\n'
                   'Question: which of the 81 U0.11 C41-121 cycles contribute positive excess '
                   'physical-raw MSE, which improvements offset it, and how concentrated/frequent is harm?\n\n'
                   'Evidence: '+a.ATTR_RUN+'; four fixed saved files listed in summary.json, '
                   'original fit 6aa21e3 and replay 08242ea, plan 9984226 / scope 2f0ff22. '
                   'Synthetic, already-viewed development archive, nominal-peak s4 post-history, horizon 0. '
                   'V1 versus V0; no new model prediction, fitting, replay or confirmation access.\n\n'
                   'Reading order: diagnostic.csv, summary.json analysis, panel A, then B. '
                   'A shows every signed D=m1-m0 with zero as equality; B ranks positive excess '
                   'descending (exact ties by cycle ascending), showing half S_plus and k50. '
                   'Unidentifiable excess has no normalised curve. No smoothing, truncation or cycle removal.\n\n'
                   'S_plus=sum(max(D,0)); S_minus=sum(max(-D,0)); S_net=S_plus-S_minus; '
                   'late mean=S_net/81, not the original overall weight 1/(3*81). '
                   'tau=1e-10+1e-10*abs(m0); harm D>tau, improve D<-tau, otherwise tie. '
                   'k50 reaches half S_plus; S_plus<=sum(tau) is unidentifiable. '
                   'Baseline mean must exceed 1e-24; frozen RMSE ratio agreement is within 1e-12. '
                   'Units are raw archive units squared. RMSE percentages cannot be additively attributed.\n\n'
                   'Interpretation: read S_plus, S_minus and S_net together with all 81 counts/fractions '
                   'and the fixed branch in summary.json. Other three cases are saved late background only, '
                   'not recomputed. No physical success threshold is introduced; tables are authoritative. '
                   'A missing figure is incomplete reporting, not a negative scientific verdict.\n\n'
                   'Allowed: descriptive cycle-level error contribution and a next-evidence proposal. '
                   'Blocked: physical causality, gradient conflict, spatial support, independent-cycle '
                   'inference, NN necessity, new weights, teacher qualification or confirmation generalisation. '
                   'C121 inclusion only proposes provenance checking, not a continuation cause.\n\n'
                   'Storyline: original E021 verdict unchanged. Next action is the predeclared proposal '
                   'only, not automatic source expansion, fitting, a new experiment or confirmation access.\n')


def run(out):
    """Explicit child entry. Definitions/imports never invoke it."""
    a.require(str(out) == a.ATTR_OUTPUT, 'fixed attribution output required')
    code = os.environ.get('S04_LATE_CODE', '')
    full_commit(code)
    refs = dict(approval_ref=os.environ.get('S04_LATE_APPROVAL_REF'),
                review_ref=os.environ.get('S04_LATE_REVIEW_REF'), reviewed_commit=code)
    a.check_execution_refs(refs, code)
    auth = str(out/'authorization.json')
    a.check_child_handoff(auth, str(out), os.environ, actual_parent=os.getppid(),
                          attempt=a.ATTR_RUN, code_commit=code)
    a.require(all(os.environ.get(key) == str(out/value) for key, value in CACHE_ENV.items()),
              'fixed run-owned cache paths required')
    activity = dict(metadata_attempts=0, read_attempts=0, content_bytes=0,
                    content_by_source={path: 0 for path in a.SOURCES})
    snapshot = analysis = None
    error = None
    phase = 'AUTHORIZATION'
    attribution_invoked = plotting_invoked = False

    def event(kind, path, count):
        a.require(path in a.SOURCES, 'activity outside science allowlist')
        if kind == 'METADATA_ATTEMPT':
            activity['metadata_attempts'] += 1
        elif kind == 'READ_ATTEMPT':
            activity['read_attempts'] += 1
        elif kind == 'CONTENT_BYTES':
            activity['content_bytes'] += count
            activity['content_by_source'][path] += count
        else:
            raise ValueError('unknown access event')
        print(json.dumps(dict(event=kind, path=path, bytes=count)), flush=True)

    def on_plot():
        nonlocal plotting_invoked
        plotting_invoked = True
        print(json.dumps(dict(event='PLOTTING_ENTERED')), flush=True)

    try:
        grant = a.decode_child_grant(auth, str(out), os.environ, actual_parent=os.getppid(),
                                     attempt=a.ATTR_RUN, code_commit=code,
                                     read_auth=read_authorization)
        phase = 'FOUR_SOURCE_SNAPSHOT'
        snapshot = a.acquire_attribution(grant=grant, code_commit=code, env=os.environ,
                                         auth_path=auth, output=str(out), actual_parent=os.getppid(),
                                         execution_refs=refs, access_event=event)
        phase = 'DESCRIBE'
        attribution_invoked = True
        print(json.dumps(dict(event='ATTRIBUTION_ENTERED')), flush=True)
        late, analysis, cumulative = a.core.describe(snapshot['rows'], snapshot['expected_ratio'])
        # Do not duplicate the 357 rows or pretend that the engine authenticates them.
        analysis = dict(analysis, source_identity='FOUR_SOURCE_METADATA_CHECKED_NOT_CONTENT_HASHED')
        del snapshot['rows']
        phase = 'REPORT'
        print(json.dumps(dict(event='REPORT_ENTERED')), flush=True)
        report(late, analysis, cumulative, out, on_plot=on_plot)
    except BaseException as exc:
        # Parser exceptions can expose values. Record stage/type only.
        # Only known constant core checks get an additional safe reason code.
        error = safe_error(exc, phase)
    record = dict(status='READONLY_ATTRIBUTION_REPORTED' if error is None else 'ATTRIBUTION_FAILED',
                  scope=SCOPE, domain='REAL_SAVED_SCALARS', evidence_domain='SYNTHETIC_VIEWED_DEVELOPMENT',
                  attempt_id=a.ATTR_RUN, code_commit=code, plan_commit=a.core.PLAN_COMMIT,
                  scope_commit=a.ATTR_SCOPE_COMMIT, execution_references=refs, sources=list(a.SOURCES),
                  activity=activity, error=error, source_metadata=None, saved_background=None,
                  coverage_verified=snapshot is not None, rows_verified=357 if snapshot is not None else None,
                  counts_verified=dict(a.core.COUNTS) if snapshot is not None else None,
                  analysis=analysis, python_optimize=sys.flags.optimize, python_debug=__debug__,
                  source_metadata_accessed=activity['metadata_attempts'] > 0,
                  real_data_read=activity['content_bytes'] > 0,
                  attribution_invoked=attribution_invoked, plotting_invoked=plotting_invoked,
                  fitting_invoked=False, confirmation_accessed=False,
                  original_scientific_verdict_unchanged=True,
                  limits='metadata drift checks, not content authentication or physical causality')
    if snapshot is not None:
        record.update(source_metadata=snapshot['source_metadata'], saved_background=snapshot['background'])
    with (out/'summary.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
    print(json.dumps(dict(worker_status=record['status'], activity=activity,
                          attribution_invoked=attribution_invoked, plotting_invoked=plotting_invoked)), flush=True)
    return int(error is not None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.out))
