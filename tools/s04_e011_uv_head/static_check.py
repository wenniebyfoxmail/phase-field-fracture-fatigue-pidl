"""Preparation-only AST/JSON checks. No numpy/torch imports or payload access."""
import ast
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    here = Path(__file__).resolve().parent
    for name in ('guard.py', 'worker.py', 'static_check.py'):
        tree = ast.parse((here / name).read_text(), filename=name)
        for node in tree.body:
            assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.FunctionDef,
                                     ast.ClassDef, ast.Assign, ast.If)), (name, type(node))
        if name == 'worker.py':
            assert not any(isinstance(n, ast.Import) and any(a.name in ('torch', 'numpy') for a in n.names)
                           for n in tree.body)
            loads = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                     isinstance(n.func, ast.Attribute) and n.func.attr == 'load' and
                     isinstance(n.func.value, ast.Name)]
            assert len(loads) == 3  # Two allow_pickle=False NPZ, one weights_only PT.
    c = json.loads((root / 'docs/research/S04/S04-E011/uv_head_c1_20261018_r2/inputs.json').read_text())
    assert c['cycle'] == 1 and c['substep'] == 4 and c['FEM_outer'] == 9
    assert len(c['files']) == 4
    assert [r['role'] for r in c['files']] == ['state', 'model', 'baseline_fields', 'baseline_result']
    assert len({r['path'] for r in c['files']}) == 4
    assert all(len(r['sha256']) == 64 and r['bytes'] > 0 for r in c['files'])
    assert c['files'][0]['decode_fields'] == ['nodes', 'cells', 'freeu', 'u_fem', 'v_fem', 'd_fem', 'ru_fem']
    assert c['budget'] == dict(wall_seconds=900, opt_no_new_eval_seconds=600,
                               work_seconds=840, evaluations=400, rss_bytes=8589934592,
                               gpu_reserved_bytes=8589934592, gpu_process_bytes=8589934592,
                               output_bytes=104857600)
    assert c['resource_policy']['physical_GPU'] == 3
    assert c['resource_policy']['minimum_initial_free_MiB'] == 12288
    assert c['resource_policy']['minimum_runtime_free_MiB'] == 4096
    assert c['resource_policy']['service']['pid'] == 3295884
    assert c['rcond'] == 1e-10 and c['relative_gain_screen'] == 1e-4
    print('AST and four-file contract checks passed; no payload opened, imported or evaluated')


if __name__ == '__main__':
    main()
