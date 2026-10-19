"""Standard-library static contract/dependency tests; never execute solver code."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from verify_code_package import check_local_imports


def check(root):
    if sys.flags.optimize:
        raise RuntimeError('static checks require Python optimization disabled')
    folder = root/'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019'
    c = json.loads((folder/'inputs_fn776.json').read_text())
    reference = json.loads((folder/'mechanics_ast.json').read_text())
    worker = ast.parse((root/'tools/s04_e011_fn776/worker.py').read_text())
    run = next(n for n in worker.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    nested = {n.name: n for n in run.body if isinstance(n, ast.FunctionDef)}
    for name, expected in reference['functions'].items():
        assert ast.dump(nested[name], include_attributes=False) == expected, name
    pc, budget, caps = c['fn776'], c['budget'], c['work_ledger']
    assert pc['rank'] == 388 and pc['z_dimension'] == 776
    assert pc['max_outer_steps'] == 16 and pc['max_backtracking_trials'] == 32
    assert pc['curvature_slot_units'] == 776*2 == 1552
    assert pc['max_outer_steps']*1552 == caps['curvature'] == 24832
    assert 16*32 == caps['trials'] == 512
    # Four initial E/G controls + one E/G and one HVP per complete direction.
    assert 4 + 16*(1+2) == 52 <= caps['controls'] == 64
    assert 3 <= caps['final'] == 16
    assert sum(caps[k] for k in ('curvature','controls','trials','final')) == caps['total'] == budget['work_units'] == 25424
    assert budget['wall_seconds'] == 900 and budget['opt_no_new_eval_seconds'] == 600 and budget['work_seconds'] == 840
    assert budget['rss_bytes'] == budget['gpu_reserved_bytes'] == budget['gpu_process_bytes'] == 8*1024**3
    assert budget['output_bytes'] == 100*1024**2
    assert c['resource_policy']['minimum_runtime_free_MiB'] == 4096
    assert c['resource_policy']['gpu_uuid'] == 'GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81'
    assert len(c['files']) == 5 and sum(r['bytes'] for r in c['files']) == 20911589
    assert next(r for r in c['files'] if r['role'] == 'frozen_transform')['decode_fields'] == ['transform']
    assert pc['z_gradient_inf_threshold'] == 1e-8
    selected = [p.relative_to(root).as_posix() for p in (root/'source').rglob('*.py')]
    selected += ['SENS_tensile/run_native_q4_one_step_matrix.py','SENS_tensile/field_computation.py']
    selected += [p.relative_to(root).as_posix() for p in (root/'tools/s04_e011_fn776').glob('*.py')]
    catalog = {}
    for directory in ('source','SENS_tensile','tools/s04_e011_fn776'):
        for path in (root/directory).glob('*.py'):
            catalog.setdefault(path.stem, []).append(path.relative_to(root).as_posix())
    manifest = dict(files=[dict(path=p) for p in selected], local_module_catalog=catalog,
                    import_entrypoints=[p for p in selected if p.startswith('tools/')])
    closure = check_local_imports(root, manifest)
    broken = copy.deepcopy(manifest)
    broken['files'] = [r for r in manifest['files'] if r['path'] != 'SENS_tensile/field_computation.py']
    try:
        check_local_imports(root, broken)
    except AssertionError as error:
        assert 'missing local module: SENS_tensile/field_computation.py' in str(error)
    else:
        raise AssertionError('missing-local-module negative test did not fail')
    # Test the actual promisor regex constant, not an independently copied regex.
    tree = ast.parse((root/'tools/s04_e011_fn776/verify_code_package.py').read_text())
    pattern = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and
                   isinstance(n.value, str) and 'promisor' in n.value)
    with tempfile.TemporaryDirectory(prefix='fn776-code-git-') as temp:
        subprocess.run(['git','init','-q',temp],check=True,capture_output=True)
        subprocess.run(['git','-C',temp,'config','remote.origin.promisor','true'],check=True)
        found = subprocess.check_output(['git','-C',temp,'config','--get-regexp',pattern],text=True).strip()
        assert found == 'remote.origin.promisor true'
    for path in (root/'tools/s04_e011_fn776').glob('*.py'):
        tree = ast.parse(path.read_text(), filename=str(path))
        for n in tree.body:
            if isinstance(n, (ast.Import,ast.ImportFrom)):
                modules = [a.name for a in n.names] if isinstance(n,ast.Import) else [n.module]
                assert all(m.split('.')[0] not in ('torch','numpy','scipy','matplotlib') for m in modules)
    return dict(status='standard_library_static_checks_passed', mechanics_AST_functions=list(reference['functions']),
                planned_controls_upper_bound=52, planned_final_readouts=3, cap=25424,
                local_import_closure=closure, missing_module_negative=True, promisor_negative=True,
                scientific_arrays_accessed=0, numerical_imports_or_calls=0,
                boundary='No numerical fixture, gradient, QR, matrix assembly or runtime feasibility tested')


if __name__ == '__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[2]),indent=2))
