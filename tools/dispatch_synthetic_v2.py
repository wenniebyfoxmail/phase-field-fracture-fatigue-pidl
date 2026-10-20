"""One-shot Linux v2 admission + dispatch; no retry and no preflight solve.

The transport creates a fresh owned staging directory and exact reviewed Git
checkout. This script validates the original producer/runtime and all357 saved
states, then dispatches the one authorized R003 supervisor. A failed preflight
never invokes it. All artifacts are written outside the immutable code tree.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
from importlib.metadata import version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--transport-start', type=float, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    owner = Path('/mnt/data2/drtao/wennie')
    code = Path(__file__).resolve().parents[1]
    if (stage.parent != owner or not stage.name.startswith('pf_synmem_v2_')
            or code != stage/'code' or platform.node() != 'GPUServer8'
            or platform.system() != 'Linux'):
        raise RuntimeError('wrong v2 producer or staging root')
    from run_synthetic_history import json_read, verify_authority, storage_size
    from synthetic_history_recovery import verify_recovery, recover_prefixes, SOURCE_CODE
    import synthetic_history_experiment as experiment
    spec_path = code/'docs/research/S04/S04-E027-SYNMEM/spec.json'
    authority_path = spec_path.with_name('authority.json')
    review_path = spec_path.with_name('review.json')
    spec, authority, review = map(json_read, (spec_path, authority_path, review_path))
    experiment.validate_spec(spec)
    head = verify_authority(spec, authority, review, code)
    output = Path(authority['run_root'])
    if output.exists() or (stage/'dispatch_intent.json').exists():
        raise RuntimeError('run or dispatch claim already exists; no duplicate worker')
    continuation = authority['continuation']
    verify_recovery(spec, continuation, output)
    original = json_read(Path(continuation['source_root'])/'runtime.json')
    numerical = {n: version(n) for n in ('numpy', 'scipy', 'osqp', 'matplotlib')}
    if numerical != {n: original[n] for n in numerical} or sys.version != original['python']:
        raise RuntimeError('original numerical runtime required')
    if any(os.environ.get(n) != '4' for n in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')):
        raise RuntimeError('four-thread environment required')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('GPU devices must be hidden')
    cpus = sorted(os.sched_getaffinity(0))
    if len(cpus) < 4: raise RuntimeError('CPU affinity unavailable')
    os.sched_setaffinity(0, cpus[:4])
    resource.setrlimit(resource.RLIMIT_AS, (spec['budget']['ram_bytes'],)*2)

    def forbidden_solve(*args, **kwargs):
        raise AssertionError('no scientific solve during admission')
    experiment.solve_step = forbidden_solve
    scratch = stage/'zero_solve_recovery'
    scratch.mkdir()
    old_spec = json_read(Path(continuation['source_root'])/'spec.json')
    pairs = [[experiment.Trajectory(spec, variant, arm, scratch, SOURCE_CODE,
                                   forbidden_solve, state_contract_spec=old_spec)
              for arm in ('low','high')] for variant in spec['variants']]
    recover_prefixes(pairs, continuation, scratch)
    recovery = json_read(scratch/'recovery_receipt.json')
    if recovery['reused_accepted_states'] != 357 or recovery['new_solves_for_recovery'] != 0:
        raise RuntimeError('unexpected prefix accounting')
    # Include all old run/stage payloads plus new staging in the conservative
    # prior debit. R003's supervisor adds every newly generated output byte.
    prior_roots = [owner/'S04-E027-SYNMEM-R001', owner/'S04-E027-SYNMEM-R002',
                   owner/'pf_synmem_stage_e8ac73f6_20261020',
                   owner/'pf_synmem_recovery_bc334c0c_20261020', stage]
    footprint = sum(storage_size(p) for p in prior_roots)
    if footprint > continuation['prior_output_bytes']:
        raise RuntimeError('prior task footprint exceeds conservative debit')
    elapsed = time.time() - args.transport_start
    if elapsed >= authority['mechanical_budget']['cumulative_seconds']:
        raise RuntimeError('mechanical cumulative60-second budget reached')
    if time.time() >= continuation['deadline_epoch'] - spec['budget']['cleanup_seconds']:
        raise RuntimeError('cumulative task deadline reached')
    preflight = dict(status='strict v2 original-producer zero-solver recovery passed',
                     hostname=platform.node(), code_commit=head, reviewed_code=review['code_commit'],
                     numerical_versions=numerical, recovery=recovery, new_scientific_steps=0,
                     prior_footprint_bytes=footprint, prior_reserved_bytes=continuation['prior_output_bytes'],
                     mechanical_seconds=elapsed, epoch=time.time(), source_modified=False)
    with (stage/'preflight.json').open('x') as handle: json.dump(preflight, handle, indent=2)
    command = ['nohup', sys.executable, '-u', str(code/'tools/run_synthetic_history.py'),
               '--execute', '--spec', str(spec_path), '--authority', str(authority_path),
               '--review', str(review_path), '--output', str(output)]
    record = dict(command=command, cwd=str(code), run_id=output.name,
                  code_commit=head, epoch=time.time(), one_dispatch=True)
    with (stage/'dispatch_intent.json').open('x') as handle: json.dump(record, handle, indent=2)
    with (stage/'dispatch.log').open('xb') as log:
        proc = subprocess.Popen(command, cwd=code, env=os.environ.copy(), stdin=subprocess.DEVNULL,
                                stdout=log, stderr=log, start_new_session=True)
    record['pid'] = proc.pid
    with (stage/'dispatch.json').open('x') as handle: json.dump(record, handle, indent=2)
    print(json.dumps(dict(preflight=preflight, dispatch=record)))


if __name__ == '__main__':
    main()
