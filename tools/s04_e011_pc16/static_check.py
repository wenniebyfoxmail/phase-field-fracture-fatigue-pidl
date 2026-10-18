"""Text/AST/JSON preparation check only. Never import worker or numeric modules."""
import ast
import json
from pathlib import Path


def main():
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    for name in ('worker.py', 'guard.py', 'static_check.py'):
        tree = ast.parse((here / name).read_text(), filename=name)
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
                assert not any(n.split('.')[0] in ('numpy', 'torch', 'scipy', 'matplotlib') for n in names)
        assert not any(isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) for node in tree.body)
    text = (here / 'worker.py').read_text()
    tree = ast.parse(text)
    loads = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
             isinstance(node.func, ast.Attribute) and node.func.attr == 'load']
    assert len(loads) == 3  # state NPZ + frozen transform NPZ + weights-only original PT.
    for node in loads:
        keywords = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg in ('allow_pickle', 'weights_only')}
        assert keywords.get('allow_pickle') is False or keywords.get('weights_only') is True
    assert 'svd' not in text.lower() or 'svd(' not in text.lower()
    assert "payload['transform']" in text and "payload['z']" not in text
    contract = json.loads((root / 'docs/research/S04/S04-E011/uv_head_c1_pc16_20261018/inputs.json').read_text())
    assert contract['protocol'] == 'S04-E011-UVH-C1-PC16-v1'
    assert contract['run_id'] == 'pf_s04e011_uvh_c1_pc16_r1_20261018'
    assert contract['cycle'] == 1 and contract['substep'] == 4 and contract['FEM_outer'] == 9
    assert [r['role'] for r in contract['files']] == ['state', 'model', 'frozen_transform', 'frozen_summary', 'frozen_basis']
    assert len({r['path'] for r in contract['files']}) == 5
    assert all(len(r['sha256']) == 64 and r['bytes'] > 0 for r in contract['files'])
    assert contract['files'][2]['decode_fields'] == ['transform']
    assert sum(r['bytes'] for r in contract['files']) == 20911589
    assert contract['work_ledger'] == dict(total=400, hvp=68, controls=16, optimization=308, final=8,
         hvp_calls=34, hvp_cost=2, energy_or_energy_and_gradient_cost=1, standalone_gradient_cost=1, no_reallocation=True)
    assert contract['budget'] == dict(wall_seconds=900, opt_no_new_eval_seconds=600, work_seconds=840,
         work_units=400, rss_bytes=8589934592, gpu_reserved_bytes=8589934592,
         output_bytes=104857600, gpu_process_bytes=8589934592)
    pc = contract['pc16']
    assert (pc['rank'], pc['z_dimension'], pc['sketch_columns'], pc['seed']) == (388, 776, 16, 1)
    assert pc['z_gradient_inf_threshold'] == 1e-8 and pc['library_y_gtol'] == 0.0
    assert pc['ftol'] == 1e-14 and pc['maxls'] == 20 and pc['maxcor'] == 10
    assert contract['relative_gain_screen'] == 1e-4 and contract['rcond'] == 1e-10
    policy = contract['resource_policy']
    assert policy['physical_GPU'] == 3 and policy['minimum_initial_free_MiB'] == 12288
    assert policy['minimum_runtime_free_MiB'] == 4096 and policy['service']['pid'] == 3295884
    guard = (here / 'guard.py').read_text()
    assert "os.environ.get('CUDA_VISIBLE_DEVICES') != '"+policy['gpu_uuid']+"'" in guard
    assert 's04_e011_uv_head' in guard and 's04_e011_pc16' in guard
    assert "open('x')" in guard and 'os.killpg(child.pid' in guard
    print('Static AST/JSON contract checks passed. No numeric imports, fixtures, payload reads/hashes or execution.')


if __name__ == '__main__':
    main()
