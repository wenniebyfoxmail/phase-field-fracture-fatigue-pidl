"""E025 fixed input/grant contract. Import performs no file IO.

Real reads occur only from the explicit, reviewed worker after separate human
execution approval. The permit/ref checks are interlocks, not authentication
of a person or an OS sandbox. Never follow legacy event/audit/model pointers.
"""
import sys

if sys.flags.optimize:
    raise RuntimeError('non-optimised Python required')

import hashlib
import json
import os
from pathlib import Path
import stat

EXPERIMENT = 'S04-E025'
RUN = EXPERIMENT+'-R001'
ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
# Only legacy relative scientific paths use the documented E016 source root.
# Keep the parent project/output root and three absolute PIN paths unchanged.
RELATIVE_SOURCE_ROOT = DATA_ROOT/'.codex/worktrees/s04-e016-request31-storage-block-20261009'
OUT = DATA_ROOT/'local_archive/experiments'/EXPERIMENT/'runs'/RUN
MANIFEST = 'docs/research/S04/S04-E025/input_manifest.json'
PROPOSAL = '82cd09258bb09604a3f89809dd7005ac77631b8c'
LOCK_SHA = 'cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c'
COUNTS = dict(u011=121, u0115=99, u012=82, u013=55)
TRAIN = ('u0115', 'u012', 'u013')
BUDGET = dict(seconds=300, rss_bytes=2*1024**3, output_bytes=100*1024**2)
CACHE = {'MPLCONFIGDIR': 'cache/matplotlib', 'XDG_CACHE_HOME': 'cache/xdg', 'TMPDIR': 'cache/tmp'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def strict_json(text):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    def constant(_):
        raise ValueError('nonfinite JSON constant')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def manifest():
    """Git controls only, no scientific metadata or array reads."""
    m = strict_json((ROOT/MANIFEST).read_text())
    require(m['experiment_id'] == EXPERIMENT and m['revision'] == 'v2' and
            m['proposal_commit'] == PROPOSAL and m['data_root'] == str(DATA_ROOT) and
            m['relative_source_root'] == str(RELATIVE_SOURCE_ROOT) and
            m['legacy_lock_sha256'] == LOCK_SHA and m['counts'] == COUNTS and
            m['train'] == list(TRAIN) and m['evaluation'] == 'u011' and
            m['horizon'] == 0 and m['origin'] == 'cN_s4_post_history_commit', 'manifest identity')
    require(m['legacy_lock'] == 'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json',
            'fixed legacy lock')
    data = (ROOT/m['legacy_lock']).read_bytes()
    require(hashlib.sha256(data).hexdigest() == LOCK_SHA, 'legacy lock changed')
    lock = strict_json(data.decode('utf-8'))
    require(lock['feature_module'] == 'SENS_tensile/s04_g5_features.py' and
            hashlib.sha256((ROOT/lock['feature_module']).read_bytes()).hexdigest() == lock['feature_sha256'],
            'unchanged legacy feature recipe required')
    absolute = lambda path: str(Path(path) if Path(path).is_absolute() else RELATIVE_SOURCE_ROOT/path)
    expected = {(None, 'geometry'): (absolute(lock['geometry']['path']), lock['geometry']['sha256'])}
    for item in lock['trajectories']:
        require(item['id'] in COUNTS and item['common_pre_cycle_end_candidate'] == COUNTS[item['id']], 'fixed prefix')
        for kind in ('pin', 'fem'):
            expected[item['id'], kind] = (absolute(item[kind+'_path']), item[kind+'_sha256'])
    files = m['scientific_files']
    require(len(files) == 9 and len({f['path'] for f in files}) == 9 and
            len({(f['case'], f['kind']) for f in files}) == 9, 'nine unique scientific files')
    require({(f['case'], f['kind']): (f['path'], f['sha256']) for f in files} == expected,
            'manifest differs from frozen scientific allowlist')
    for f in files:
        role = 'public_geometry' if f['kind'] == 'geometry' else (
            'evaluation_after_fit' if f['case'] == 'u011' else 'training')
        require(f['role'] == role, 'input role')
    require(m['pin_fields'] == ['damage', 'alpha_bar', 'fatigue_f', 'psi_raw_direct'] and
            m['fem_fields'] == ['damage', 'alpha_bar', 'psi_raw_direct'], 'declared channel set')
    return m


def refs_ok(code, refs):
    require(type(code) is str and len(code) == 40 and all(c in '0123456789abcdef' for c in code), 'full code commit')
    require(type(refs) is dict and set(refs) == {'approval_ref', 'review_ref', 'reviewed_commit'} and
            refs['reviewed_commit'] == code, 'exact execution references')
    require(all(type(refs[k]) is str and 0 < len(refs[k]) <= 512 and
                not any(c in refs[k] for c in ('\r', '\n', '\x00')) for k in ('approval_ref', 'review_ref')),
            'bounded references')


def grant_for(code, refs, m):
    refs_ok(code, refs)
    return dict(version=1, action='two_arm_phase_representation_fit', experiment_id=EXPERIMENT,
                run_id=RUN, code_commit=code, proposal_commit=PROPOSAL, output=str(OUT),
                input_manifest=MANIFEST, scientific_files=m['scientific_files'], lock_sha256=LOCK_SHA,
                train=list(TRAIN), evaluation='u011', budget=dict(BUDGET),
                user_approved_real_execution=True, independent_code_review='APPROVED',
                fit=True, confirmation=False, execution_references=dict(refs))


def token(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns)


def read_control(path, limit):
    """Only an explicit Run-owned control; not a general scientific reader."""
    require(path in (OUT/'authorization.json', OUT/'receipt.json'), 'fixed own control')
    st = path.lstat()
    before = token(st)
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and 0 < st.st_size <= limit, 'bounded control')
    if path.name == 'authorization.json':
        require(st.st_mode & 0o222 == 0, 'authorization read-only')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(token(os.fstat(fd)) == before, 'control descriptor mismatch')
        data = bytearray()
        while len(data) <= limit:
            block = os.read(fd, min(65536, limit+1-len(data)))
            if not block:
                break
            data.extend(block)
        require(len(data) == st.st_size and token(os.fstat(fd)) == before, 'control drift')
    finally:
        os.close(fd)
    require(token(path.lstat()) == before, 'control path drift')
    return strict_json(bytes(data).decode('utf-8'))


def child_authorization(out):
    """All machine interlocks precede any scientific stat/open."""
    require(str(out) == str(OUT), 'fixed output')
    code = os.environ.get('S04_PHASE_CODE', '')
    refs = dict(approval_ref=os.environ.get('S04_PHASE_APPROVAL_REF'),
                review_ref=os.environ.get('S04_PHASE_REVIEW_REF'), reviewed_commit=code)
    refs_ok(code, refs)
    expected = dict(S04_PHASE_OUTPUT=str(OUT), S04_PHASE_PARENT=str(os.getppid()),
                    S04_PHASE_RUN=RUN, S04_PHASE_CODE=code,
                    S04_PHASE_AUTH=str(OUT/'authorization.json'))
    require(all(os.environ.get(k) == v for k, v in expected.items()) and
            'RAW_START_MONOTONIC' in os.environ, 'fixed parent/child handoff')
    require(all(os.environ.get(k) == str(OUT/v) for k, v in CACHE.items()), 'run-owned caches')
    m = manifest()
    grant = read_control(OUT/'authorization.json', 65536)
    require(grant == grant_for(code, refs, m), 'grant identity/scope mismatch')
    return m, code, refs


class Reader:
    """Exact nine-file SHA-locked read/decode on the SAME no-follow descriptor.

    Hashes reuse the already frozen external-input identities; no new hash
    forest. Decoders receive a file object, never an inferred path. Full-file
    hashing and selected variable decompression may read beyond used prefixes;
    computation uses only the frozen prefixes, never confirmation amplitudes.
    """
    def __init__(self, m, activity):
        self.files = {(f['case'], f['kind']): f for f in m['scientific_files']}
        self.activity = activity

    def read(self, case, kind, decoder):
        entry = self.files[case, kind]
        path = Path(entry['path'])
        a = self.activity
        a['metadata_attempts'] += 1
        print(json.dumps(dict(event='INPUT_METADATA_ATTEMPT', path=str(path))), flush=True)
        require(path.resolve(strict=True) == path, 'canonical scientific path')
        before = token(path.lstat())
        require(stat.S_ISREG(before[2]) and before[3] > 0, 'nonempty regular input')
        a['read_attempts'] += 1
        print(json.dumps(dict(event='INPUT_READ_ATTEMPT', path=str(path))), flush=True)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            with os.fdopen(fd, 'rb', closefd=False) as file:
                require(token(os.fstat(fd)) == before, 'input descriptor mismatch')
                digest = hashlib.sha256()
                while True:
                    block = file.read(1024**2)
                    if not block:
                        break
                    digest.update(block)
                    a['hash_bytes_read'] += len(block)
                require(digest.hexdigest() == entry['sha256'], 'frozen input digest mismatch')
                file.seek(0)
                a['decode_attempts'] += 1
                result = decoder(file)
                require(token(os.fstat(fd)) == before, 'input changed during hash/decode')
        finally:
            os.close(fd)
        require(token(path.lstat()) == before, 'input path drift')
        a['verified_inputs'].append(dict(entry, metadata=list(before)))
        print(json.dumps(dict(event='INPUT_VERIFIED', path=str(path))), flush=True)
        return result
