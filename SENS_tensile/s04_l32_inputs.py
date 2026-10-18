"""E026 fixed 9+5 source contract; import is inert, not an execution permit."""
import sys
if sys.flags.optimize:
    raise RuntimeError('non-optimised Python required')
import os
from pathlib import Path
import stat
import s04_phase_inputs as legacy

require, strict_json, token, Reader = legacy.require, legacy.strict_json, legacy.token, legacy.Reader
refs_ok = legacy.refs_ok
EXPERIMENT, RUN = 'S04-E026', 'S04-E026-R001'
ROOT, DATA_ROOT = Path(__file__).resolve().parents[1], legacy.DATA_ROOT
OUT = DATA_ROOT/'local_archive/experiments'/EXPERIMENT/'runs'/RUN
MANIFEST = 'docs/research/S04/S04-E026/input_manifest.json'
PROPOSAL = '69457e1405efe00f2b242a7934445d11f1730f86'
BASE_RUN, BASE_CODE = 'S04-E025-R002', 'ba4518d1bd9c27b4b8bf154486456d59d17a57ee'
BASE_OUT = DATA_ROOT/'local_archive/experiments/S04-E025/runs'/BASE_RUN
LOCK_SHA, COUNTS, TRAIN, BUDGET, CACHE = legacy.LOCK_SHA, legacy.COUNTS, legacy.TRAIN, legacy.BUDGET, legacy.CACHE
FROZEN = [('receipt.json', 6061, 'identity'), ('guard_receipt.json', 7548, 'identity'),
          ('models.json', 30209, 'train_only_baseline'), ('percycle.csv', 13230, 'evaluation_after_fit'),
          ('summary.json', 2214, 'evaluation_after_fit')]


def manifest():
    old = legacy.manifest()  # Git controls only; nine original identities unchanged.
    m = strict_json((ROOT/MANIFEST).read_text())
    require(m['experiment_id'] == EXPERIMENT and m['revision'] == 'v1' and m['proposal_commit'] == PROPOSAL,
            'new experiment/proposal')
    for key in ('scientific_files', 'data_root', 'relative_source_root', 'legacy_lock', 'legacy_lock_sha256',
                'admission_record', 'train', 'evaluation', 'counts', 'pin_fields', 'fem_fields', 'origin', 'horizon'):
        require(m[key] == old[key], 'unchanged scientific contract: '+key)
    expected = [dict(name=n, path=str(BASE_OUT/n), bytes=b, role=r) for n, b, r in FROZEN]
    require(m['frozen_files'] == expected and m['baseline_run'] == BASE_RUN and
            m['baseline_code'] == BASE_CODE and m['expected_fit_count'] == 1 and
            m['fit_cycles'] == {'u0115': [41, 99], 'u012': [41, 82], 'u013': [41, 55]}, 'fixed baseline/one-fit scope')
    return m


def grant_for(code, refs, m):
    refs_ok(code, refs)
    return dict(version=1, action='one_late_weight_fit_reuse_frozen_B32', experiment_id=EXPERIMENT,
                run_id=RUN, code_commit=code, proposal_commit=PROPOSAL, output=str(OUT),
                input_manifest=MANIFEST, scientific_files=m['scientific_files'], frozen_files=m['frozen_files'],
                lock_sha256=LOCK_SHA, train=list(TRAIN), evaluation='u011', budget=dict(BUDGET),
                user_approved_real_execution=True, independent_code_review='APPROVED', fit=True,
                expected_fit_count=1, baseline_refit=False, baseline_reevaluation=False,
                confirmation=False, execution_references=dict(refs))


def bounded_read(path, limit, decoder, *, readonly=False, size=None):
    """Caller binds an exact allowlist path; same no-follow descriptor and drift checks."""
    require(path.resolve(strict=True) == path, 'canonical fixed control')
    st = path.lstat(); before = token(st)
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and 0 < st.st_size <= limit and
            (size is None or st.st_size == size) and (not readonly or st.st_mode & 0o222 == 0), 'bounded control identity')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        with os.fdopen(fd, 'rb', closefd=False) as file:
            require(token(os.fstat(fd)) == before, 'control fd identity')
            data = file.read(limit+1)
            require(len(data) == st.st_size and len(data) <= limit, 'bounded control bytes')
            result = decoder(data)
            require(token(os.fstat(fd)) == before, 'control changed during decode')
    finally:
        os.close(fd)
    require(token(path.lstat()) == before, 'control path drift')
    return result, list(before)


def read_control(path, limit):
    require(path in (OUT/'authorization.json', OUT/'receipt.json'), 'fixed own controls')
    return bounded_read(path, limit, lambda b: strict_json(b.decode('utf-8')),
                        readonly=path.name == 'authorization.json')[0]


def child_authorization(out):
    require(str(out) == str(OUT), 'fixed output')
    code = os.environ.get('S04_L32_CODE', '')
    refs = dict(approval_ref=os.environ.get('S04_L32_APPROVAL_REF'),
                review_ref=os.environ.get('S04_L32_REVIEW_REF'), reviewed_commit=code)
    refs_ok(code, refs)
    expected = dict(S04_L32_OUTPUT=str(OUT), S04_L32_PARENT=str(os.getppid()), S04_L32_RUN=RUN,
                    S04_L32_CODE=code, S04_L32_AUTH=str(OUT/'authorization.json'))
    require(all(os.environ.get(k) == v for k, v in expected.items()) and 'RAW_START_MONOTONIC' in os.environ,
            'fixed parent/child handoff')
    require(all(os.environ.get(k) == str(OUT/v) for k, v in CACHE.items()), 'own caches')
    m = manifest()
    require(read_control(OUT/'authorization.json', 65536) == grant_for(code, refs, m), 'exact grant')
    return m, code, refs


def read_frozen(m, name, activity, decoder=None):
    files = m['frozen_files']; index = len(activity['verified_frozen'])
    require(index < len(files) and files[index]['name'] == name, 'fixed ordered frozen read')
    entry = files[index]
    if entry['role'] == 'evaluation_after_fit':
        require(activity['fits_completed'] == 1 and activity['training_released'] is True,
                'saved evaluation only after candidate fit/release')
    require(BASE_OUT.resolve(strict=True) == BASE_OUT and BASE_OUT.stat().st_mode & 0o222 == 0,
            'frozen baseline root')
    activity['frozen_read_attempts'] += 1
    result, metadata = bounded_read(Path(entry['path']), entry['bytes'],
        decoder or (lambda b: strict_json(b.decode('utf-8'))), readonly=True, size=entry['bytes'])
    activity['verified_frozen'].append(dict(entry, metadata=metadata))
    return result
