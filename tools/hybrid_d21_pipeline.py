"""D21 adapter for the original complete supervisor, not another solver."""
import json
import os
from pathlib import Path
from time import perf_counter, sleep, time

from hybrid_inputs import read_manifest, sha256
from hybrid_producer_common import write_json, append_event

OWNER = Path('docs/research/S04/hybrid_constrained_design_20261019')
TASK = OWNER / 'd21_complete_20261025'
REVISION = 'd21-active-face-complete-v1'


def is_d21(card):
    return card.get('numerical_solver_revision') == REVISION


def bound_json(code, binding):
    rel = Path(binding['source'])
    if rel.is_absolute() or '..' in rel.parts:
        raise RuntimeError('nonlocal D21 evidence')
    path = Path(code) / rel
    if sha256(path) != binding['sha256']:
        raise RuntimeError('D21 evidence hash differs')
    return read_manifest(path)


def validate(card, code):
    from hybrid_state_contract import CONTRACT_ID
    old = read_manifest(Path(code) / OWNER / 'complete_execution_20261020/execution_card.json')
    d21 = read_manifest(Path(code) / OWNER / 'solver_repair_v12/execution_card.json')
    if card.get('schema') != old['schema'] or card.get('state_contract_id') != CONTRACT_ID:
        raise ValueError('D21 accepted-state contract differs')
    for key in ('solver', 'coupling', 'snapshot_storage'):
        if card.get(key) != d21[key]:
            raise ValueError('D21 physical policy differs: ' + key)
    for key in ('training', 'criteria', 'producer', 'base_load_cycle', 'inputs_sha256',
                'state0_id', 'displacement_scale', 'runtime_expected', 'plotting_admission'):
        if card.get(key) != old[key]:
            raise ValueError('complete comparison policy differs: ' + key)
    expected = json.loads(json.dumps(old['phases']))
    for phase in expected:
        phase['cpu_cores'] = 4 if phase['kind'] == 'trajectory' and not phase['gpu'] else 16
        phase['ram_gib'] = 32 if phase['kind'] == 'trajectory' and not phase['gpu'] else 64
    if card['phases'] != expected:
        raise ValueError('D21 labels/fit/frozen-test phase order or limits differ')
    for key, value in old['budget'].items():
        if key not in ('remaining_host_hours_after_all_known_prior_runs', 'producer_retries') and card['budget'].get(key) != value:
            raise ValueError('original resource budget differs: ' + key)
    if card.get('retry_policy') != dict(admission_attempts=4, wait_seconds=30,
                                        technical_code_change='stop', repeat_started_fit=False):
        raise ValueError('bounded mechanical retry policy differs')


def require_authority(card, code):
    if card.get('execution_enabled') is not True:
        raise RuntimeError('D21 execution disabled')
    authority = bound_json(code, card['authority_binding'])
    if authority.get('kind') != 'direct_user_approval' or authority.get('date') != '2026-10-25':
        raise RuntimeError('current complete-task authority absent')
    prior = bound_json(code, card['prior_budget_binding'])
    if prior['budget']['GPU_hours_unused'] != 12:
        raise RuntimeError('prior GPU budget differs')
    if card['prior_charged_host_seconds'] < prior['budget']['conservative_total_deduction_seconds']:
        raise RuntimeError('prior work was reset')
    if not 0 < card['remaining_host_seconds'] <= 136 * 3600 - card['prior_charged_host_seconds']:
        raise RuntimeError('remaining host budget differs')
    if card['run_id'] in prior.get('settled_runs', []):
        raise RuntimeError('consumed run identity')


def require_benchmark(card, package, receipt, card_path):
    if (receipt.get('verdict') != 'FIXED_BENCHMARK_PASS'
            or receipt.get('card_sha256') != sha256(card_path)
            or receipt.get('artifact_id') != package['artifact_id']
            or receipt.get('independent_review_performed') is not False):
        raise RuntimeError('actual fixed benchmark does not bind exact source/card')


def initial_totals(card, started):
    prior = card['prior_charged_host_seconds']
    return dict(wall_seconds=prior, cpu_seconds=0., gpu_seconds=0., numerical_seconds=0.,
                phases={}, start_monotonic=started-prior, shared_analysis_seconds=0.,
                historical_cpu_seconds=None, historical_numerical_seconds=None,
                cpu_accounting_scope='observed new child CPU only; historical CPU unknown',
                pre_execution_cost=dict(wall_seconds=prior, cpu_seconds=None, gpu_seconds=0.,
                                        cost_only_not_admission=True))


def admission_retry(operation, card, runroot, totals):
    """Only resource/OS admission before any child; never repeats scientific work."""
    policy = card['retry_policy']
    for attempt in range(1, policy['admission_attempts']+1):
        try:
            return operation()
        except (OSError, RuntimeError) as exc:
            # A changed identity, version or policy cannot be fixed by waiting.
            transient = isinstance(exc, OSError) or any(s in str(exc) for s in
                ('GPU is occupied', 'RAM capacity below', 'free storage below'))
            append_event(Path(runroot)/'admission_retries.jsonl',
                         dict(attempt=attempt, reason=str(exc), transient=transient, epoch=time()))
            if (not transient or attempt == policy['admission_attempts']
                    or perf_counter()+policy['wait_seconds'] >= totals['start_monotonic']+136*3600-45):
                raise
            sleep(policy['wait_seconds'])


def require_frozen(archive):
    phase = Path(archive)/'training'
    receipt = read_manifest(phase/'receipt.json')
    record = read_manifest(phase/'training_record.json')
    labels = read_manifest(phase/'qualified_labels.json')
    if (receipt.get('completed') is not True or record.get('test_opened') is not False
            or (record.get('train_transitions'), record.get('validation_transitions')) != (1200, 600)
            or labels.get('qualified_transitions') != 1800
            or sha256(phase/'best.pt') != receipt['checkpoint_sha256']
            or sha256(phase/'training_record.json') != receipt['model_manifest']['training_receipt_sha256']):
        raise RuntimeError('test requires a sealed single fit of exactly1800 qualified labels')


def admit_phase(spec, archive, runroot):
    if spec['id'] == 'training':
        # Durable exclusivity survives an unknown/disconnected launch result.
        path = Path(runroot)/'fit_invocation.json'
        with path.open('x') as f:
            json.dump(dict(epoch=time(), maximum_fits=1, phase='training'), f)
            f.flush(); os.fsync(f.fileno())
    elif spec['id'].startswith('test_'):
        require_frozen(archive)
