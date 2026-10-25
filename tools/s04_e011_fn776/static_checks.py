"""FN776-r8 static contract and canonical-head repair audit.

This is AST/text/Git only: it never imports numeric code, opens scientific
payloads, starts SSH, or performs numerical evaluation.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASELINE = '5f6349a1f67ad4a38089304f6ed26b73211c94c4'
RUN = 'pf_s04e011_uvh_c1_fn776_r8_20261025'
CARD = 'S04-E011-UVH-C1-FN776-CARD-r8'
INDEX = 'S04-E011-FN776-r8-A1'
RESOURCE_REVISION = 'GPU7-FN776-shared-r2-uvicorn28011'
EXPECTED_CONTRACT_SHA256 = 'a79de9464c4057caa9ea6096785a17ab4601a43f5061a868d093be571f5aee17'
# These immutable review hashes cover the entire changed worker/run and solver,
# rather than trusting a concurrently editable AST snapshot alone.
EXPECTED_WORKER_SOURCE_SHA256 = '7f8c6304c6231199d8da22f820bbfd9456e0f11d18dc3c7f5f9cd0a624c18bad'
EXPECTED_RUN_AST_SHA256 = 'ad4eed791cdf4a3f3ffae7fa49391d847e3cc381e0dc645760b4f793b65d4680'
EXPECTED_SQUARE_ROOT_SOURCE_SHA256 = '613da597b86db7ab8c608d2015155c232d441942b79c5fea39ee8c50feca4184'
THIRD_SERVICE = {
    'pid': 651952,
    'start_ticks': 541746716,
    'uids': [0, 0, 0, 0],
    'cmdline_sha256': 'be18325d0086a499e503b772c5a74d63a708299a314533ef5711f5cf5b853808',
    'cgroup_sha256': 'a1e3fcdf826b0ef154308aec0ff2d84eabf72cd221b321f5f1db06e001ee468e',
    'baseline_MiB': 5638,
    'maximum_MiB': 6144,
    'description': 'root Docker-scoped python -m uvicorn app.main:app --host 0.0.0.0 --port 28011 --workers 1',
    'utc': '2026-10-25T17:10:13+00:00',
}
EXPECTED_REMAINING = {
    'total': 17637, 'curvature': 17072, 'controls': 45, 'trials': 507, 'final': 13,
    'curvature_slot_units': 1552, 'hvp_cost': 2, 'energy_or_energy_and_gradient_cost': 1,
    'standalone_gradient_cost': 1, 'no_reallocation': True,
}
EXPECTED_PRIOR = {
    'total': 7787, 'curvature': 7760, 'controls': 19, 'trials': 5, 'final': 3,
    'source_run': 'pf_s04e011_uvh_c1_fn776_r7_20261025',
    'terminal': 'final actual-head/basis-gradient equivalence assertion; not a stationarity result',
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def contract_digest(contract):
    return sha256(json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii'))


def function_nodes(tree):
    return {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def functions(tree):
    return {name: ast.dump(node, include_attributes=False) for name, node in function_nodes(tree).items()}


def contract_checks(folder):
    original = json.loads((folder/'inputs_fn776.json').read_text())
    r7 = json.loads((folder/'inputs_fn776_r7.json').read_text())
    current = json.loads((folder/'inputs_fn776_r8.json').read_text())
    protected = ('protocol', 'files', 'read_semantics', 'rcond', 'relative_gain_screen',
                 'cycle', 'substep', 'load', 'FEM_outer', 'source_base')
    for key in protected:
        assert current[key] == original[key], key
    assert current['run_id'] == RUN
    expected_fn = dict(original['fn776'], max_outer_steps=11)
    assert current['fn776'] == expected_fn
    assert current['resource_policy'] == r7['resource_policy']
    assert current['resource_policy']['services'][-1] == THIRD_SERVICE
    assert current['resource_revision'] == RESOURCE_REVISION
    assert current['task_work_ledger'] == original['work_ledger']
    assert current['prior_work_ledger'] == EXPECTED_PRIOR
    assert current['work_ledger'] == EXPECTED_REMAINING
    for key in ('curvature', 'controls', 'trials', 'final'):
        assert (current['task_work_ledger'][key] - current['prior_work_ledger'][key]
                == current['work_ledger'][key]), key
    assert current['task_work_ledger']['total'] - current['prior_work_ledger']['total'] == current['work_ledger']['total']
    assert sum(current['prior_work_ledger'][key] for key in ('curvature', 'controls', 'trials', 'final')) == current['prior_work_ledger']['total']
    assert sum(current['work_ledger'][key] for key in ('curvature', 'controls', 'trials', 'final')) == current['work_ledger']['total']
    assert current['fn776']['max_outer_steps'] * current['work_ledger']['curvature_slot_units'] == current['work_ledger']['curvature']
    assert 'budget' not in current
    repair = current['repair']
    assert repair['kind'] == 'canonical_actual_head_vjp_finite_precision_repair'
    assert repair['new_diagnostics'] == [
        'zero_actual_head_diagnostic.json', 'probe_actual_head_diagnostic.json', 'final_actual_head_diagnostic.json']
    assert repair['rhs_binding'] == ('canonical actual-head AD gradient; augmented-basis projection is retained only as a floating-point diagnostic')
    assert repair['unchanged'] == ['five input identities', 'continuous model', 'rank 388', 'z_dimension 776', 'seed',
                                    'thresholds', 'Armijo', 'full-rank TSQR tangent factorization', 'mechanics']
    control = current['control_plane']
    assert control['card_id'] == CARD and control['approval_index'] == INDEX
    assert control['resource_policy_changed'] is False
    assert control['repair_baseline_dev'] == BASELINE
    assert 'one r8 guard/numerical solve only' in control['technical_retry_policy']
    execution = current['execution_resource_policy']
    assert execution['self_resource_ceiling'] == execution['self_resource_enforcement'] == 'none'
    assert execution['algorithmic_scope_is_not_a_resource_ceiling'] is True
    assert '17637' in execution['fixed_algorithmic_scope'] and '11 outer steps' in execution['fixed_algorithmic_scope']
    policy = current['resource_policy']
    assert policy['minimum_host_available_kB'] == 16 * 1024 * 1024
    assert policy['minimum_data2_free_bytes'] == 5 * 1024**3
    assert contract_digest(current) == EXPECTED_CONTRACT_SHA256
    return current


def assigned_constant(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            if isinstance(node.value, ast.Constant):
                return node.value.value
    raise AssertionError('missing literal '+name)


def remote_contract(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'CONTRACT' for target in node.targets):
            assert isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
            assert node.value.func.attr == 'loads' and len(node.value.args) == 1
            assert isinstance(node.value.args[0], ast.Constant)
            return json.loads(node.value.args[0].value)
    raise AssertionError('missing literal remote CONTRACT')


def check(root):
    assert not sys.flags.optimize
    folder = root/'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019'
    current = contract_checks(folder)
    worker_path = root/'tools/s04_e011_fn776/worker.py'
    worker_raw = worker_path.read_bytes()
    worker = worker_raw.decode()
    assert sha256(worker_raw) == EXPECTED_WORKER_SOURCE_SHA256, 'worker source differs from reviewed repair'
    tree = ast.parse(worker, filename=str(worker_path))
    worker_functions = functions(tree)
    run_node = function_nodes(tree)['run']
    assert sha256(ast.dump(run_node, include_attributes=False).encode()) == EXPECTED_RUN_AST_SHA256, 'run body differs from reviewed repair'
    baseline_worker = subprocess.check_output(
        ['git', 'show', BASELINE+':tools/s04_e011_fn776/worker.py'], cwd=root, text=True)
    assert blob(baseline_worker.encode()) == '9e02f72ef309304ad86018cf78c7a7fb43568daa'
    baseline_tree = ast.parse(baseline_worker, filename='baseline_worker.py')
    baseline_functions = functions(baseline_tree)
    unchanged = ('check_work', 'charge', 'tensor', 'selected_json', 'elastic', 'hvp', 'raw_field',
                 'assert_frozen', 'opt_check', 'log_control', 'make_figure')
    for name in unchanged:
        assert worker_functions[name] == baseline_functions[name], 'unreviewed worker change: '+name
    assert 'physical' in baseline_functions and 'gradient_close' in baseline_functions
    assert 'actual_head_uv' not in baseline_functions and 'actual_head_force_vjp' not in baseline_functions
    expected_names = {'actual_head_uv', 'tensor', 'selected_json', 'elastic', 'branch_signature', 'measure',
                      'physical', 'objective_z', 'gradient_comparison', 'field_pair_diagnostic',
                      'actual_head_force_vjp', 'raw_field', 'assert_frozen', 'capture_factor'}
    mechanics_record = json.loads((folder/'mechanics_ast.json').read_text())
    assert mechanics_record['purpose'].startswith('AST snapshot of the reviewed canonical actual-head/VJP')
    assert set(mechanics_record['functions']) == expected_names
    for name in expected_names:
        assert worker_functions[name] == mechanics_record['functions'][name], name
    assert mechanics_record['worker_source_sha256'] == EXPECTED_WORKER_SOURCE_SHA256
    assert mechanics_record['run_ast_sha256'] == EXPECTED_RUN_AST_SHA256
    for required in ('torch.nn.functional.linear', 'weight0[2:]', 'def actual_head_force_vjp',
                     "save('zero_actual_head_diagnostic.json'", "save('probe_actual_head_diagnostic.json'",
                     "save('final_actual_head_diagnostic.json'", 'force_comparison=gradient_comparison',
                     'last_value, last_gradient = checked_value, checked_g',
                     'return actual_head_uv(torch, field, original, features, x, transform, rank, z)'):
        assert required in worker, required
    for forbidden in ('del features', 'def gradient_close', 'increment = basis @ z.reshape(rank, 2)',
                      'actual_gz = (basis.T @', "contract['budget']", 'work_seconds',
                      'opt_no_new_eval_seconds', 'set_per_process_memory_fraction'):
        assert forbidden not in worker, forbidden
    for artifact, gate in (
            ("zero_actual_head_diagnostic.json", "assert zero_diagnostic['field_maxabs']"),
            ("probe_actual_head_diagnostic.json", "assert probe_diagnostic['field_maxabs']"),
            ("final_actual_head_diagnostic.json", "assert final_diagnostic['field_maxabs']")):
        assert worker.index("save('"+artifact+"'") < worker.index(gate)
    assert "probe_diagnostic['force_comparison']['passed']" in worker
    assert "final_diagnostic['force_comparison']['passed']" in worker
    assert "analytic_basis_gradient = (basis.T @" in worker
    assert "final_diagnostic['vjp_vs_direct']['passed']" in worker

    square = root/'tools/s04_e011_fn776/square_root.py'
    square_raw = square.read_bytes()
    assert sha256(square_raw) == EXPECTED_SQUARE_ROOT_SOURCE_SHA256, 'square-root source differs from reviewed canonical-RHS repair'
    square_text = square_raw.decode()
    assert 'canonical_rhs_binding=\'actual_head_AD_gradient\'' in square_text
    assert 'canonical_rhs = torch.linalg.solve_triangular(R.T, gradient[:, None], upper=False)' in square_text
    assert "assert canonical_transport_relative <= config['linear_relative_residual'], 'canonical square-root RHS residual'" in square_text
    assert "assert canonical_transport_backward <= config['linear_backward_tolerance'], 'canonical square-root RHS backward error'" in square_text
    assert 'step = triangular(W, -canonical_rhs, True) / col_norm' in square_text
    assert 'augmented_basis_gradient_maxabs_error=augmented_gradient_error' in square_text
    assert "augmented_rhs='root[:776,776]; transformed jointly with A; diagnostic only'" in square_text
    assert "assert gradient_error <= gradient_tolerance, 'square-root gradient mismatch'" not in square_text

    mechanics = {}
    for path in ('SENS_tensile/run_native_q4_one_step_matrix.py', 'SENS_tensile/field_computation.py'):
        raw = (root/path).read_bytes()
        prior = subprocess.check_output(['git', 'show', '3dfef418828e53632b3a5c90521ab8989dbf9673:'+path], cwd=root)
        assert raw == prior, path
        mechanics[path] = blob(raw)
    assert mechanics_record['frozen_mechanics_blobs'] == mechanics
    assert mechanics_record['reviewed_solver_blob'] == blob(square_raw)
    assert mechanics_record['square_root_source_sha256'] == EXPECTED_SQUARE_ROOT_SOURCE_SHA256

    parsed = {}
    for path in (root/'tools/s04_e011_fn776').glob('*.py'):
        raw = path.read_text()
        parsed[path.name] = ast.parse(raw, filename=str(path))
        for node in parsed[path.name].body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
                assert all(m and m.split('.')[0] not in ('numpy', 'torch', 'scipy', 'matplotlib') for m in modules)
    remote = parsed['remote_control_r2.py']
    assert remote_contract(remote) == current
    assert contract_digest(remote_contract(remote)) == EXPECTED_CONTRACT_SHA256
    assert assigned_constant(parsed['guard.py'], 'CONTRACT_SHA256') == EXPECTED_CONTRACT_SHA256
    for name in ('digest', 'contract_digest', 'service_identity', 'gpu_snapshot'):
        a = next(node for node in parsed['guard.py'].body if isinstance(node, ast.FunctionDef) and node.name == name)
        b = next(node for node in remote.body if isinstance(node, ast.FunctionDef) and node.name == name)
        assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False), name
    remote_text = (root/'tools/s04_e011_fn776/remote_control_r2.py').read_text()
    guard_text = (root/'tools/s04_e011_fn776/guard.py').read_text()
    assert 'bundled contract differs from reviewed SSH literal' in remote_text
    assert '--expected-contract-sha256' in remote_text and '--expected-contract-sha256' in guard_text
    assert "contract_digest(contract) != CONTRACT_SHA256" in guard_text
    assert "contract_sha256=CONTRACT_SHA256" in remote_text and "contract_sha256=CONTRACT_SHA256" in guard_text
    for artifact in current['repair']['new_diagnostics']:
        assert artifact in remote_text, artifact
    identity_files = ('guard.py', 'control_r2.py', 'verify_retrieval_r2.py', 'build_code_package.py')
    for name in identity_files:
        raw = (root/'tools/s04_e011_fn776'/name).read_text()
        assert 'pf_s04e011_uvh_c1_fn776_r8_20261025' in raw or name == 'build_code_package.py', name
        assert 'inputs_fn776_r8.json' in raw or name in ('control_r2.py', 'verify_retrieval_r2.py'), name
        for forbidden in ("contract['budget']", 'gpu_process_bytes', '100MiB', '10*1024**2'):
            assert forbidden not in raw, (name, forbidden)
    package_text = (root/'tools/s04_e011_fn776/build_code_package.py').read_text()
    verifier_text = (root/'tools/s04_e011_fn776/verify_code_package.py').read_text()
    assert 'inputs_fn776_r8.json' in package_text and 'deployment_fn776_r8.md' in package_text
    assert 'worker_repair_audit' in package_text and 'worker_repair_audit' in verifier_text
    assert 'static_audit' in package_text and 'static_audit' in verifier_text
    control_text = (root/'tools/s04_e011_fn776/control_r2.py').read_text()
    retrieval_text = (root/'tools/s04_e011_fn776/verify_retrieval_r2.py').read_text()
    assert 'contract_binding' in package_text and 'contract_binding' in verifier_text
    assert "plan['contract_binding'] == source['contract_binding']" in control_text
    assert "contract_sha256=CONTRACT_SHA256" in guard_text
    assert "output_claimed=OUT.exists()" in guard_text
    assert "root_terminal_before_output" in retrieval_text
    assert "partial output receipt chain" in retrieval_text
    assert "worker_output_evidence_available" in retrieval_text
    assert "git', 'rev-parse', 'HEAD'" in package_text and "git', 'status', '--porcelain', '--untracked-files=all'" in package_text
    assert BASELINE in package_text and '9e02f72ef309304ad86018cf78c7a7fb43568daa' in verifier_text
    return dict(status='DIFF_STATIC_PASS', worker_blob=blob(worker_raw),
                worker_source_sha256=sha256(worker_raw), run_ast_sha256=EXPECTED_RUN_AST_SHA256,
                baseline_worker_blob=blob(baseline_worker.encode()), unchanged_worker_functions=list(unchanged),
                square_root_blob=blob(square_raw), square_root_source_sha256=sha256(square_raw),
                frozen_mechanics_blobs=mechanics, contract_sha256=EXPECTED_CONTRACT_SHA256,
                parsed_modules=len(parsed), repair='canonical actual-head/VJP with canonical TSQR RHS binding; materialized head remains independent check',
                cumulative_ledger=dict(prior=current['prior_work_ledger'], remaining=current['work_ledger'],
                                       task=current['task_work_ledger']), resource_policy='exact GPU7 three services unchanged',
                checks='AST/text/Git only; no SSH, scientific payload access, numeric import or runtime validation',
                SSH=False, scientific_payload_access=False, numerical_calls=False)


if __name__ == '__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[2]), indent=2))
