"""Independent no-fit replay of frozen S04-E021 physical-raw outer models."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from s04_d0 import LOCK_SHA, load_inputs


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json'
PARENT_RUN = 'S04-E021-R001'
PARENT_CODE = '6aa21e3c469d53c92240c9689d07a3ffb316d67c'
PARENT_RESULT = 'bcb58a68f4b5eea00c2796476ce7aa50688deeb7'
ALPHAS = (0.01, 1.0, 100.0)
EPS = 1e-10
MSE_ATOL = 1e-10
MSE_RTOL = 1e-10
AGG_ATOL = 1e-12
PARENT_FILES = {'receipt.json', 'models.json', 'selection.json', 'decision.json',
                'percycle.csv', 'folds.csv', 'u0115_C20.npz', 'V0_V1_holdouts.png',
                'u0115_C20_raw.png', 'README_analysis.md'}


class ReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def finite(*values: np.ndarray | float) -> None:
    require(all(np.isfinite(value).all() for value in values), 'nonfinite value')


def budget() -> None:
    if 'RAW_REPLAY_START_MONOTONIC' in os.environ:
        require(time.monotonic() - float(os.environ['RAW_REPLAY_START_MONOTONIC']) < 295,
                'internal wall reserve exhausted')


def cycle_weights(n: int) -> np.ndarray:
    strata = np.minimum(np.arange(n) // 20, 2)
    return np.array([1.0 / (3 * np.sum(strata == s)) for s in strata])


def source(case: dict, cycle: int, ids: np.ndarray, kind: str) -> np.ndarray:
    values = np.column_stack([
        case[kind][name][cycle - 1, ids]
        for name in ('damage', 'alpha_bar', 'psi_raw_direct')
    ]).astype(np.float64)
    finite(values)
    require(values.shape == (len(ids), 3), 'source shape mismatch')
    require(np.all(values[:, 1:] >= 0), 'negative source history/raw')
    if kind == 'fem':
        require(np.all((values[:, 0] >= 0) & (values[:, 0] <= 1)),
                'FEM damage outside bounds')
    return values


def admissible(pin: np.ndarray) -> np.ndarray:
    finite(pin)
    return np.column_stack((np.clip(pin[:, 0], 0.0, 1.0),
                            np.maximum(pin[:, 1:], 0.0)))


def scalar_prediction(features: np.ndarray, model: dict, alpha_index: int) -> np.ndarray:
    """Explicit float64 accumulation; intentionally not production evaluate()."""
    x = np.asarray(features, dtype=np.float64)
    xm = np.asarray(model['xm'], dtype=np.float64)
    xstd = np.asarray(model['xstd'], dtype=np.float64)
    ym = np.asarray(model['ym'], dtype=np.float64)
    ystd = np.asarray(model['ystd'], dtype=np.float64)
    coefficients = np.asarray(model['coefficients'], dtype=np.float64)
    scales = np.asarray(model['scales'], dtype=np.float64)
    finite(x, xm, xstd, ym, ystd, coefficients, scales)
    require(x.ndim == 2 and x.shape[1] == 32, 'feature shape mismatch')
    require(xm.shape == xstd.shape == (32,), 'feature normalizer shape mismatch')
    require(ym.shape == ystd.shape == (1,), 'target normalizer shape mismatch')
    require(coefficients.shape == (3, 33, 1), 'coefficient shape mismatch')
    require(scales.shape == (2,) and np.all(scales > 1e-12), 'scale mismatch')
    require(np.all(xstd > 0) and np.all(ystd > 0), 'nonpositive normalizer')
    require(alpha_index in range(3), 'alpha index mismatch')
    beta = coefficients[alpha_index, :, 0]
    normalized = np.full(len(x), beta[0], dtype=np.float64)
    for column in range(32):
        normalized += ((x[:, column] - xm[column]) / xstd[column]) * beta[column + 1]
    target = normalized * ystd[0] + ym[0]
    residual_physical = scales[1] * target
    finite(residual_physical)
    return residual_physical


def map_outputs(pin: np.ndarray, residual_physical: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply the frozen physical-raw map without changing damage or history."""
    raw = np.asarray(pin, dtype=np.float64)
    residual = np.asarray(residual_physical, dtype=np.float64)
    require(raw.ndim == 2 and raw.shape[1] == 3, 'mapped input shape mismatch')
    require(residual.shape == (len(raw),), 'mapped residual shape mismatch')
    finite(raw, residual)
    v0 = admissible(raw)
    v1 = v0.copy()
    v1[:, 2] = np.maximum(0.0, raw[:, 2] + residual)
    finite(v0, v1)
    require(np.array_equal(v0[:, :2], v1[:, :2]), 'damage/history changed')
    require(np.all((v1[:, 0] >= 0) & (v1[:, 0] <= 1)) and
            np.all(v1[:, 1:] >= 0), 'replayed output bounds')
    return v0, v1


def close(replayed: float | np.ndarray, saved: float | np.ndarray,
          atol: float = MSE_ATOL, rtol: float = MSE_RTOL) -> tuple[float, float]:
    a = np.asarray(replayed, dtype=np.float64)
    b = np.asarray(saved, dtype=np.float64)
    require(a.shape == b.shape, 'comparison shape mismatch')
    finite(a, b)
    difference = np.abs(a - b)
    allowed = atol + rtol * np.abs(b)
    require(np.all(difference <= allowed),
            f'replay mismatch max={float(difference.max())} allowed={float(allowed.max())}')
    return float(difference.max(initial=0.0)), float((difference / np.maximum(allowed, 1e-300)).max(initial=0.0))


def file_hashes(source_run: Path) -> dict[str, str]:
    require(source_run.is_dir(), 'parent run directory missing')
    require({path.name for path in source_run.iterdir()} == PARENT_FILES,
            'parent run file set mismatch')
    result = {}
    for name in sorted(PARENT_FILES):
        digest = hashlib.sha256()
        with (source_run / name).open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        result[name] = digest.hexdigest()
    return result


def verify_hashes(source_run: Path, expected: dict[str, str] | None) -> dict[str, str]:
    actual = file_hashes(source_run)
    if expected is not None:
        require(set(expected) == PARENT_FILES, 'parent hash coverage mismatch')
        require(all(isinstance(value, str) and len(value) == 64 for value in expected.values()),
                'parent hash format mismatch')
        require(actual == expected, 'parent SHA-256 mismatch')
    return actual


def load_saved(source_run: Path) -> tuple[dict, list[dict], dict, dict[tuple[str, int], dict]]:
    require(source_run.name == PARENT_RUN, 'parent run identity mismatch')
    receipt = json.loads((source_run / 'receipt.json').read_text())
    require(receipt.get('status') == 'COMPLETED' and
            receipt.get('run_id') == PARENT_RUN and
            receipt.get('code_commit') == PARENT_CODE and
            receipt.get('lock_sha256') == LOCK_SHA,
            'parent receipt identity mismatch')
    models = json.loads((source_run / 'models.json').read_text())
    selections = json.loads((source_run / 'selection.json').read_text())
    decision = json.loads((source_run / 'decision.json').read_text())
    with (source_run / 'percycle.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 357, 'parent row count mismatch')
    indexed: dict[tuple[str, int], dict] = {}
    for row in rows:
        key = (row['holdout'], int(row['cycle']))
        require(key not in indexed, 'duplicate parent row')
        indexed[key] = row
    return models, selections, decision, indexed


def replay(cases: dict, pipeline, source_run: Path, output: Path,
           expected_hashes: dict[str, str] | None = None) -> dict:
    source_hashes = verify_hashes(source_run, expected_hashes)
    models, selections, saved_decision, saved_rows = load_saved(source_run)
    keys = sorted(cases)
    require(keys == ['u011', 'u0115', 'u012', 'u013'], 'development case identity mismatch')
    require(len(selections) == 4, 'selection count mismatch')
    selection_by_key = {row['holdout']: row for row in selections}
    saved_fold_by_key = {row['holdout']: row for row in saved_decision['folds']}
    require(set(selection_by_key) == set(saved_fold_by_key) == set(keys), 'fold identity mismatch')
    area = np.asarray(pipeline.areas, dtype=np.float64)
    area = area / area.sum()
    finite(area)
    require(len(area) == len(pipeline.ids) and np.all(area > 0), 'area weights mismatch')
    comparisons: list[dict] = []
    aggregate: list[dict] = []
    c20_maxima = None
    for key in keys:
        case = cases[key]
        model = models.get('outer_' + key)
        selection = selection_by_key[key]
        require(model is not None and selection.get('reason') == 'LEARNED_SELECTED',
                'frozen outer model missing')
        alpha = float(selection['selected_alpha'])
        require(alpha in ALPHAS, 'selected alpha mismatch')
        alpha_index = ALPHAS.index(alpha)
        require(model.get('train') == selection.get('train'), 'training identity mismatch')
        base = np.zeros(3, dtype=np.float64)
        corrected = np.zeros(3, dtype=np.float64)
        saved_base = np.zeros(3, dtype=np.float64)
        saved_corrected = np.zeros(3, dtype=np.float64)
        weights = cycle_weights(case['n'])
        for cycle, weight in enumerate(weights, 1):
            budget()
            saved = saved_rows.get((key, cycle))
            require(saved is not None, 'missing parent cycle row')
            require(float(saved['selected_alpha']) == alpha and saved['fallback'] == 'False',
                    'saved selection mismatch')
            pin = source(case, cycle, pipeline.ids, 'pin')
            fem = source(case, cycle, pipeline.ids, 'fem')
            x = pipeline.trajectory_cycle(case['pin'], cycle, case['umax'],
                                          np.asarray(model['scales'], dtype=np.float64))
            residual = scalar_prediction(x, model, alpha_index)
            v0, v1 = map_outputs(pin, residual)
            mse0 = float(np.sum(area * (v0[:, 2] - fem[:, 2]) ** 2))
            mse1 = float(np.sum(area * (v1[:, 2] - fem[:, 2]) ** 2))
            finite(mse0, mse1)
            d0, n0 = close(mse0, float(saved['V0_physical_mse']))
            d1, n1 = close(mse1, float(saved['V1_physical_mse']))
            stratum = min((cycle - 1) // 20, 2)
            require(stratum == int(saved['stratum']), 'saved stratum mismatch')
            close(weight, float(saved['cycle_weight']), atol=1e-16, rtol=0.0)
            base[stratum] += 3.0 * weight * mse0
            corrected[stratum] += 3.0 * weight * mse1
            saved_base[stratum] += 3.0 * weight * float(saved['V0_physical_mse'])
            saved_corrected[stratum] += 3.0 * weight * float(saved['V1_physical_mse'])
            comparisons.append(dict(holdout=key, cycle=cycle, stratum=stratum,
                selected_alpha=alpha, replay_V0_physical_mse=mse0,
                saved_V0_physical_mse=float(saved['V0_physical_mse']),
                V0_abs_difference=d0, V0_tolerance_fraction=n0,
                replay_V1_physical_mse=mse1,
                saved_V1_physical_mse=float(saved['V1_physical_mse']),
                V1_abs_difference=d1, V1_tolerance_fraction=n1,
                V0_raw_min=float(v0[:, 2].min()), V0_raw_max=float(v0[:, 2].max()),
                V1_raw_min=float(v1[:, 2].min()), V1_raw_max=float(v1[:, 2].max())))
            if key == 'u0115' and cycle == 20:
                with np.load(source_run / 'u0115_C20.npz', allow_pickle=False) as saved_snapshot:
                    require(np.array_equal(saved_snapshot['ids'], pipeline.ids),
                            'C20 support identity mismatch')
                    maxima = {}
                    for name, value in (('fem', fem), ('V0', v0), ('V1', v1)):
                        maximum, fraction = close(value, saved_snapshot[name])
                        maxima[name + '_max_abs'] = maximum
                        maxima[name + '_max_tolerance_fraction'] = fraction
                    c20_maxima = maxima
        require(np.all(base > 1e-24), 'unidentified replay denominator')
        r = float(np.sqrt(corrected.mean() / base.mean()))
        g = float(np.sqrt(corrected[0] / base[0]))
        frozen = saved_fold_by_key[key]
        close(r, float(frozen['R']), atol=AGG_ATOL, rtol=0.0)
        close(g, float(frozen['G']), atol=AGG_ATOL, rtol=0.0)
        late = float(np.sqrt(corrected[2] / base[2]))
        saved_late = float(np.sqrt(saved_corrected[2] / saved_base[2]))
        close(late, saved_late, atol=AGG_ATOL, rtol=0.0)
        aggregate.append(dict(holdout=key, selected_alpha=alpha, replay_R=r,
            saved_R=float(frozen['R']), replay_G=g, saved_G=float(frozen['G']),
            late_C41plus_ratio=late, saved_late_C41plus_ratio=saved_late))
    require(len(comparisons) == 357 and c20_maxima is not None, 'replay coverage mismatch')
    q = max(row['replay_R'] for row in aggregate)
    status = ('EARLY_REGRESSION' if any(row['replay_G'] > 1 + EPS for row in aggregate)
              else 'RAW_REGRESSION' if q > 1 + EPS
              else 'DIRECTIONAL_DEVELOPMENT_GAIN' if q < 1 - EPS
              else 'NUMERICAL_TIE')
    close(q, float(saved_decision['Q']), atol=AGG_ATOL, rtol=0.0)
    require(status == saved_decision['status'], 'decision classification changed')
    require(verify_hashes(source_run, expected_hashes) == source_hashes,
            'parent package changed during replay')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'percycle_comparison.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
        writer.writeheader(); writer.writerows(comparisons)
    with (output / 'aggregate_comparison.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate[0]))
        writer.writeheader(); writer.writerows(aggregate)
    result = dict(status='REPLAY_REPRODUCED', parent_outcome=status, Q=q,
                  parent_Q=float(saved_decision['Q']), rows=len(comparisons),
                  folds=aggregate, fixed_C20=c20_maxima, fit_performed=False,
                  selection_performed=False, confirmation_accessed=False,
                  source_file_sha256=source_hashes)
    (output / 'decision.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    return result


def authorization(path: Path | None, output: Path, source_run: Path) -> dict:
    require(path is not None, 'separate replay authorization required')
    record = json.loads(Path(path).read_text())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    tracked_dirty = subprocess.check_output(
        ['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True)
    require(not tracked_dirty, 'tracked worktree must be clean')
    expected = dict(user_approved_real_replay=True, independent_code_review='APPROVED',
                    experiment_id='S04-E022', run_id='S04-E022-R001',
                    code_commit=commit, parent_result_commit=PARENT_RESULT,
                    parent_run_id=PARENT_RUN, lock_sha256=LOCK_SHA,
                    source_run=str(source_run.resolve()), output=str(output.resolve()))
    require(all(record.get(key) == value for key, value in expected.items()),
            'authorization/code/source/output mismatch')
    require(output.name == record['run_id'], 'run/output identity mismatch')
    hashes = record.get('source_file_sha256')
    require(isinstance(hashes, dict) and set(hashes) == PARENT_FILES,
            'authorization parent hash coverage mismatch')
    require(all(isinstance(value, str) and len(value) == 64 for value in hashes.values()),
            'authorization parent hash format mismatch')
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    args = parser.parse_args()
    source_run = args.source_run.resolve(); output = args.out.resolve()
    approved = authorization(args.authorization.resolve(), output, source_run)
    require(not output.exists(), 'fresh output required')
    cases, pipeline = load_inputs(ROOT, LOCK)
    result = replay(cases, pipeline, source_run, output,
                    expected_hashes=approved['source_file_sha256'])
    receipt = dict(run_id=output.name,
        code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        lock_sha256=LOCK_SHA, source_run=str(source_run), output=str(output), **result)
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
