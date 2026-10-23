#!/usr/bin/env python3
"""Export the actually published main c1 prefix, without a completed window.

This is array/metadata I/O only. It reuses the existing native-vector reduction
and exact readback converters, with the real completion record as the step
publication boundary. It never creates or implies a completed window result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from export_window import (
    arr, checked_policy, convert_predecessor, convert_step, equal,
    export_as_predecessor, integer, key_from_mat, load_support, record,
    require, sha256, source_arrays, state_key, text,
)


BASE_SOURCES = {
    'driver_binding.mat', 'window/input_binding.mat',
    'predecessor/native_admission.mat', 'predecessor/admitted_predecessor.mat',
    'predecessor/admission_report.mat',
}
STEP_FILES = ('completion.mat', 'proposal.mat', 'step_checkpoint.mat', 'readback.mat')
REQUEST = dict(cycle=1, substeps=[1, 2, 3, 4, 5], role='main')


def read_request(h, prefix):
    return dict(cycle=integer(h, prefix + '/cycle'),
                substeps=arr(h, prefix + '/substeps').reshape(-1).tolist(),
                role=text(h, prefix + '/role'))


def append_scope(path, scope):
    """Annotate only this invocation's newly generated local conversion file."""
    receipt = json.loads(path.read_text())
    receipt['partial_scope'] = scope
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    return record(path)


def export(args):
    import h5py

    steps = args.substeps
    require(steps in ([1], [1, 2], [1, 2, 3]),
            'only the contiguous published c1 prefix through s3 is supported; no failed s4 target')
    required_sources = BASE_SOURCES | {
        f'window/c0001_s{step:02d}/{name}' for step in steps for name in STEP_FILES}
    require(not args.output.exists(), 'never replace an existing partial export')
    require(sha256(args.source_manifest) == args.source_manifest_sha256,
            'download source manifest hash differs')
    manifest_ref = dict(path=str(args.source_manifest.resolve()), sha256=args.source_manifest_sha256)
    manifest = json.loads(args.source_manifest.read_text())
    require(manifest['schema'] == 'e036-fem-published-step-sources-v1'
            and manifest['label'] == 'main_c1_01', 'wrong published-step source scope')
    sources = manifest['files']
    require(len(sources) == len(required_sources)
            and {f['relative_path'] for f in sources} == required_sources,
            'require exactly the actual binding/admission files and four artifacts per published step')
    refs = {}
    for entry in sources:
        require(re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None,
                'invalid source SHA256')
        path = args.run / entry['relative_path']
        require(sha256(path) == entry['sha256'], 'downloaded native source differs')
        refs[entry['relative_path']] = record(path)

    require(sha256(args.config) == args.config_sha256, 'executed config hash differs')
    config_ref = dict(path=str(args.config.resolve()), sha256=args.config_sha256)
    config = json.loads(args.config.read_text())
    spec = config['predecessor']
    require(config['request'] == REQUEST and config['watchdog_id'] == manifest['label']
            and config['run_root'] == manifest['producer_root']
            and config['output_dir'] == config['run_root'] + '/output/main_c1_01',
            'source manifest is not the executed main c1 window')
    old_key = state_key(spec['state_key']['trajectory'], 1, 0)
    require(spec['kind'] == 'stored_u0' and spec['state_key'] == old_key
            and spec['sha256'] == config['common_sha256']
            and sha256(args.predecessor) == spec['sha256'], 'wrong immutable c1 U0')

    with h5py.File(args.run / 'driver_binding.mat', 'r') as h:
        require(text(h, 'config_sha256') == args.config_sha256,
                'native driver did not bind the declared config')
        for name in ('run_root', 'output_dir', 'watchdog_id', 'manifest_sha256',
                     'authority_sha256', 'stage_a_evidence_sha256', 'source_commit'):
            require(text(h, 'c/' + name) == config[name], 'native driver binding differs: ' + name)
        require(read_request(h, 'c/request') == REQUEST
                and text(h, 'c/predecessor/sha256') == spec['sha256'],
                'native driver request or immutable source differs')
        approval_id = text(h, 'approval/authority_id')

    binding_path = args.run / 'window/input_binding.mat'
    with h5py.File(binding_path, 'r') as h:
        require(read_request(h, 'request') == read_request(h, 'authority/request') == REQUEST,
                'persisted window request differs')
        for name, expected in dict(run_id=manifest['label'], approval_id=approval_id,
                manifest_sha256=config['manifest_sha256'], source_commit=config['source_commit'],
                predecessor_sha256=spec['sha256']).items():
            require(text(h, 'authority/' + name) == expected, 'window input authority differs: ' + name)
        require(all(integer(h, 'authority/' + name) == 1 for name in
                    ('execution_approved', 'native_bindings_verified', 'thread_controls_verified')),
                'window input authority is incomplete')
        checked_policy(h, 'main', prefix='authority')
        require(key_from_mat(h, 'predecessor/state_key') == old_key
                and integer(h, 'predecessor/version') == 0, 'persisted incoming state key differs')
        su, sd, sh = source_arrays(args.predecessor, spec['kind'])
        for name, expected in (('u', su), ('d', sd), ('lower', sd), ('history', sh)):
            actual = arr(h, 'predecessor/' + name)
            equal(actual.reshape(-1) if expected.ndim == 1 else actual, expected,
                  'window immutable predecessor ' + name)

    publications = {}
    for step in steps:
        prefix = f'window/c0001_s{step:02d}/'
        key = state_key(old_key['trajectory'], 1, step)
        with h5py.File(args.run / (prefix + 'completion.mat'), 'r') as h:
            require(key_from_mat(h, 'completion/state_key') == key,
                    'actual completion key differs from the declared contiguous prefix')
            # Read each binding from the original published completion. Never
            # synthesize a window row or claim a complete window result.
            published = dict(state_key=key)
            for name, filename in dict(proposal='proposal.mat', checkpoint='step_checkpoint.mat',
                                       readback='readback.mat').items():
                require(text(h, 'completion/' + name) == filename, 'unexpected publication filename')
                published[name + '_sha256'] = text(h, 'completion/' + name + '_sha256')
                require(published[name + '_sha256'] == refs[prefix + filename]['sha256'],
                        'actual completion does not bind downloaded step bytes')
            publications[step] = published

    support = load_support(binding_path)
    args.output.mkdir(parents=True)
    scope = dict(kind='published_main_prefix_only', published_states=[f'c1/s{s}' for s in steps],
                 parent_request=REQUEST, full_window_completion_asserted=False,
                 parent_window_status='not_checked_by_this_partial_export',
                 completion_evidence={f'c1/s{s}': refs[f'window/c0001_s{s:02d}/completion.mat'] for s in steps},
                 source_manifest=manifest_ref, executed_config=config_ref,
                 native_solves=0, new_history_commits=0)
    old_admission_path = args.output / 'predecessor_admission.json'
    convert_predecessor(args.run / 'predecessor', args.predecessor, spec['kind'],
                        args.predecessor_npz, support, old_admission_path)
    old_admission = append_scope(old_admission_path, scope)
    targets, as_predecessors = {}, {}
    previous, previous_kind = args.predecessor, spec['kind']
    for step in steps:
        folder = args.run / f'window/c0001_s{step:02d}'
        output = args.output / f'c1_s{step}'
        target = convert_step(folder, previous, previous_kind, support, 'main', output, publications[step])
        target['admission'] = append_scope(Path(target['admission']['path']), scope)
        predecessor = export_as_predecessor(target, output / 'as_predecessor')
        predecessor['admission'] = append_scope(Path(predecessor['admission']['path']), scope)
        targets[f'c1/s{step}'], as_predecessors[f'c1/s{step}'] = target, predecessor
        # convert_step compares this exact checkpoint's full fields/history
        # against the next proposal's immutable old arrays and state key.
        previous, previous_kind = folder / 'step_checkpoint.mat', 'verified_window_step'
    for ref in (*refs.values(), config_ref, manifest_ref):
        require(sha256(ref['path']) == ref['sha256'], 'bound input changed during partial conversion')
    # Publish this index last. No window_result or completed-window schema is
    # written, and no later state is inferred from the available prefix.
    result = dict(schema='s04_e036_fem_partial_targets_v1', partial_scope=scope,
                  targets=targets, as_predecessors=as_predecessors,
                  predecessor=dict(predecessor=record(args.predecessor_npz), admission=old_admission),
                  predecessor_admission=old_admission, input_binding=record(binding_path),
                  source_artifacts=refs, converter_source=record(Path(__file__)),
                  reused_converter_source=record(Path(__file__).with_name('export_window.py')))
    result_path = args.output / 'partial_targets.json'
    with result_path.open('x') as f:
        f.write(json.dumps(result, indent=2) + '\n')
    return record(result_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'source-manifest', 'config', 'predecessor', 'predecessor-npz', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    for name in ('source-manifest-sha256', 'config-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--substeps', nargs='+', type=int, default=[1],
                        help='contiguous published prefix only: 1, 1 2, or 1 2 3')
    print(json.dumps(export(parser.parse_args()), indent=2))


if __name__ == '__main__':
    main()
