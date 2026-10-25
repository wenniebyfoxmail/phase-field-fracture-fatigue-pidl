"""SCB normalized-input CPU kernel. No raw-image parser or implicit data acquisition.

Source: STATE_INTERFACE_AMENDMENT_20261020. Fixed alpha10, LOCO, common E0.
Import is inert. Real CLI denies unbound/unauthorized input before payload opens.
The only local execution authorized at development is benchmark_scb_state_kernel.
"""
from dataclasses import dataclass
from collections import Counter, defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import platform
import time
from scb_metadata_interface import audit_metadata

ARMS = ('G', 'C', 'H', 'D', 'P', 'S')
ALPHA = 10.0


class NotQualified(ValueError):
    pass


def number(v, name):
    if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v):
        raise NotQualified('finite number required: ' + name)
    return float(v)


def array(v):
    import numpy as np
    a = np.asarray(v, dtype=np.float64)
    if not np.isfinite(a).all():
        raise NotQualified('nonfinite feature, fit or prediction')
    return a


def config_check(cfg):
    if cfg.get('alpha') != ALPHA or cfg.get('threads') != 1:
        raise NotQualified('only single alpha10, one CPU thread')
    hs = cfg.get('horizons_cycles')
    if not hs or len(set(hs)) != len(hs) or any(number(h, 'H') <= 0 for h in hs):
        raise NotQualified('physical horizons not bound')
    if cfg.get('primary_horizon_cycles') not in hs or cfg.get('frozen_before_outer_targets') is not True:
        raise NotQualified('primary H and source-side choices must be fixed before outer outcomes')
    for k in ('sigma_floor_mm', 'reference_effect_delta_mm', 'donor_max_standardized_distance'):
        if number(cfg.get(k), k) <= 0:
            raise NotQualified('positive source-supported parameter required: ' + k)
    for k in ('sigma_floor_basis', 'effect_delta_basis', 'donor_support_basis'):
        if not cfg.get(k):
            raise NotQualified('source/development basis not bound: ' + k)
    p = number(cfg.get('phase_tolerance_fraction'), 'phase tolerance')
    if not 0 <= p < .5:
        raise NotQualified('phase tolerance [0,.5)')
    schema = cfg['feature_schema']
    g, c, local = (schema.get(k) for k in ('geometry_load_plan_columns', 'current_response_columns', 'local_response_columns'))
    if not all(isinstance(v, list) and v and len(set(v)) == len(v) for v in (g, c, local)):
        raise NotQualified('feature names not bound to source adapter')
    if not set(local) <= set(c) or set(g) & set(c):
        raise NotQualified('local response must be a declared current-response subset; distinct G/C names')
    names = g + c
    forbidden = ('n_over_nf', 'n/nf', 'final_life', 'final_crack', 'remaining_life', 'future_target', 'y_ref')
    if any(any(z in n.lower() for z in forbidden) for n in names):
        raise NotQualified('terminal/target information in feature schema')
    if not isinstance(schema.get('units'), dict) or set(schema['units']) != set(names) or not all(schema['units'].values()):
        raise NotQualified('source units for every feature required')


def whole_core_splits(entities):
    """Adapter helper: all halves/tests/views with one mother core follow the core."""
    return [dict(fold_id='core_holdout:' + core, test_id=e['test_id'],
                 role='evaluation' if e['core_id'] == core else 'development')
            for core in sorted({e['core_id'] for e in entities}) for e in entities]


@dataclass(frozen=True)
class Sample:
    key: str
    core: str
    test: str
    origin: float
    horizon: float
    roi: str
    current_length: float
    growth: float
    g: object
    current: object
    history: object
    phase: float
    stratum: tuple
    reference_id: str
    resolution_mm: float


class References:
    """Labels have a separate access path; fitting callers declare their allowed cores."""
    def __init__(self, rows):
        self.rows = rows
        self.access_log = []

    def get(self, samples, allowed_cores, purpose):
        if any(s.core not in allowed_cores for s in samples):
            raise NotQualified('future reference requested outside this fit/evaluation partition')
        values = []
        for s in samples:
            row = self.rows.get(s.reference_id)
            if row is None or set(row) != {'reference_id', 'length_mm', 'reference_source_asset_id'}:
                raise NotQualified('missing independent future value; do not drop/replace origin')
            values.append(number(row['length_mm'], 'independent future length'))
        self.access_log.append({'purpose': purpose, 'cores': sorted({s.core for s in samples}),
                                'allowed_cores': sorted(allowed_cores), 'sample_keys': [s.key for s in samples]})
        return array(values)


def _unique(rows, key):
    d = {}
    for row in rows:
        k = key(row)
        if k in d:
            raise NotQualified('duplicate normalized payload identity')
        d[k] = row
    return d


def adapt_normalized(metadata, payload, cfg):
    """Our normalized contract, not invented author CSV headers. No field interpolation."""
    config_check(cfg)
    audit = audit_metadata(metadata, cfg['horizons_cycles'], cfg['phase_tolerance_fraction'])
    if audit['status'] != 'METADATA_CONSISTENT_NOT_EXECUTION_AUTHORITY':
        raise NotQualified('received metadata missing')
    if not audit['reference_effect_tolerance_ready']:
        raise NotQualified('reference resolution needed to interpret effect size; no R/Q prerequisite')
    if set(payload) != {'response_rows', 'origin_covariates', 'reference_values'}:
        raise NotQualified('normalized numerical payload schema')
    entity = {r['test_id']: r for r in metadata['entities']}
    cores = sorted({e['core_id'] for e in entity.values()})
    if len(cores) < 3:
        raise NotQualified('outer development-side different-core donor cannot be formed')
    # Check exactly one held-out core per fold and complete, once-only LOCO coverage.
    roles = defaultdict(lambda: defaultdict(set))
    for s in metadata['splits']:
        roles[s['fold_id']][s['role']].add(entity[s['test_id']]['core_id'])
    held = []
    for role in roles.values():
        if len(role['evaluation']) != 1 or role['development'] != set(cores) - role['evaluation']:
            raise NotQualified('one mother-core holdout per fold required')
        held.extend(role['evaluation'])
    if sorted(held) != cores:
        raise NotQualified('each core must be held exactly once')
    k = lambda r: (r['test_id'], r['cycle'], r['roi_id'])
    response = _unique(payload['response_rows'], k)
    catalog = {k(r): r for r in metadata['response_catalog']}
    cov = _unique(payload['origin_covariates'], lambda r: (r['test_id'], r['origin_cycle'], r['roi_id']))
    refs = _unique(payload['reference_values'], lambda r: r['reference_id'])
    refcat = {k(r): r for r in metadata['reference_catalog']}
    gnames = cfg['feature_schema']['geometry_load_plan_columns']
    cnames = cfg['feature_schema']['current_response_columns']
    lnames = cfg['feature_schema']['local_response_columns']
    samples = []
    for o in metadata['origins']:
        tid, n, roi = o['test_id'], o['origin_cycle'], o['roi_id']
        prefix = []
        for cycle in o['history_cycles']:
            ident = tid, cycle, roi
            row, cat = response.get(ident), catalog[ident]
            expected = {'test_id', 'cycle', 'roi_id', 'current_length_mm', 'response',
                        'response_asset_id', 'geometry_asset_id', 'feature_pipeline_id', 'source_max_cycle'}
            if row is None or set(row) != expected or set(row['response']) != set(cnames):
                raise NotQualified('missing/incorrect prefix numeric response; do not impute')
            if any(row[a] != cat[b] for a, b in [('response_asset_id', 'response_asset_id'), ('geometry_asset_id', 'geometry_asset_id'), ('feature_pipeline_id', 'feature_pipeline_id')]):
                raise NotQualified('numeric response source does not match metadata')
            if number(row['source_max_cycle'], 'feature source maximum') > cycle or row['source_max_cycle'] != cat['feature_source_max_cycle']:
                raise NotQualified('future numeric response/source mismatch')
            number(row['current_length_mm'], 'current observed length')
            for name in cnames:
                number(row['response'][name], name)
            prefix.append(row)
        extra = cov.get((tid, n, roi))
        fields = {'test_id', 'origin_cycle', 'roi_id', 'values', 'available_at_cycle', 'load_plan_asset_id', 'geometry_asset_id', 'matching_stratum'}
        if extra is None or set(extra) != fields or set(extra['values']) != set(gnames):
            raise NotQualified('origin geometry/load/known-plan adapter unbound')
        if number(extra['available_at_cycle'], 'origin covariate availability') > n or extra['load_plan_asset_id'] != o['load_plan_asset_id'] or extra['geometry_asset_id'] != prefix[-1]['geometry_asset_id']:
            raise NotQualified('realized future load/covariate source mismatch')
        stratum = extra['matching_stratum']
        if not isinstance(stratum, list) or not stratum or not all(isinstance(v, str) and v for v in stratum):
            raise NotQualified('origin-known load/geometry support stratum not bound')
        cycles = o['history_cycles']
        a0 = number(prefix[-1]['current_length_mm'], 'a_obs')
        secant = (a0 - prefix[-2]['current_length_mm']) / (cycles[-1] - cycles[-2])
        g = array([a0, secant, math.sin(2*math.pi*o['phase_fraction']), math.cos(2*math.pi*o['phase_fraction'])]
                  + [number(extra['values'][name], name) for name in gnames])
        current = array(list(g) + [prefix[-1]['response'][name] for name in cnames])
        # Two observed local-response slopes. Actual cycles, never published stage offsets.
        history = array([(prefix[j+1]['response'][name] - prefix[j]['response'][name]) / (cycles[j+1] - cycles[j])
                         for j in range(2) for name in lnames])
        for h in cfg['horizons_cycles']:
            rc = refcat[tid, n+h, roi]
            ref = refs.get(rc['reference_id'])
            if ref is None or ref.get('reference_source_asset_id') != rc['reference_source_asset_id']:
                raise NotQualified('independent reference source missing; no silent origin exclusion')
            key = json.dumps([tid, n, roi, h], separators=(',', ':'))
            samples.append(Sample(key, entity[tid]['core_id'], tid, n, h, roi, a0, secant,
                                  g, current, history, o['phase_fraction'], tuple(stratum),
                                  rc['reference_id'], number(rc['reference_resolution_mm'], 'reference resolution')))
    return samples, References(refs), audit


def core_weights(samples):
    import numpy as np
    counts = Counter(s.core for s in samples)
    return np.asarray([1./counts[s.core]/len(counts) for s in samples])


def standardize(x, samples):
    import numpy as np
    x = array(x)
    w = core_weights(samples)
    mean = w @ x
    scale = np.sqrt(w @ ((x-mean)**2))
    scale[scale < 1e-8] = 1.
    return mean, scale


@dataclass
class Model:
    mean: object
    scale: object
    coef: object

    def predict(self, x):
        import numpy as np
        x = array(x)
        return array(np.c_[np.ones(len(x)), (x-self.mean)/self.scale] @ self.coef)


def fit(x, y, samples, role, trace, tick, locked=None):
    import numpy as np
    tick()
    x, y = array(x), array(y)
    if len(x) != len(y) or not len(x) or len(x) != len(samples):
        raise NotQualified('fit row mismatch')
    mean, scale = standardize(x, samples) if locked is None else locked
    z = np.c_[np.ones(len(x)), (x-mean)/scale]
    w = core_weights(samples)
    penalty = np.eye(z.shape[1])*ALPHA
    penalty[0, 0] = 0.
    coef = array(np.linalg.solve(z.T @ (w[:, None]*z) + penalty, z.T @ (w[:, None]*y if y.ndim == 2 else w*y)))
    trace.append({'role': role, 'cores': sorted({s.core for s in samples}), 'sample_keys': [s.key for s in samples],
                  'dimension': x.shape[1], 'alpha': ALPHA,
                  'mean': mean.tolist(), 'scale': scale.tolist()})
    return Model(mean, scale, coef)


def donors(pool, queries, mean, scale, cfg):
    """Origin geometry/load/plan + circular phase only. Never use future labels."""
    import numpy as np
    z = (array([s.g for s in pool])-mean)/scale
    order = sorted(range(len(pool)), key=lambda i: (pool[i].core, pool[i].test, pool[i].origin, pool[i].key))
    ids, reasons, distances = [], [], []
    for q in queries:
        phase = lambda p: min(abs(p.phase-q.phase), 1-abs(p.phase-q.phase))
        eligible = [i for i in order if pool[i].core != q.core and pool[i].stratum == q.stratum
                    and phase(pool[i]) <= cfg['phase_tolerance_fraction']]
        candidates = [(float(np.linalg.norm(z[i]-(q.g-mean)/scale)), i) for i in eligible]
        if not candidates:
            ids.append(None); reasons.append('NO_OTHER_FIT_CORE_LOAD_PHASE_SUPPORT'); distances.append(None)
            continue
        distance, selected = min(candidates, key=lambda x: (x[0], order.index(x[1])))
        if distance > cfg['donor_max_standardized_distance']:
            ids.append(None); reasons.append('OUTSIDE_DECLARED_DEVELOPMENT_MATCH_DISTANCE'); distances.append(distance)
        else:
            ids.append(selected); reasons.append(None); distances.append(distance)
    return ids, reasons, distances


def gaussian_crps(mu, sigma, target):
    sigma = number(sigma, 'shared sigma')
    if sigma <= 0:
        raise NotQualified('positive common E0 scale required')
    z = (number(target, 'target')-number(mu, 'conditional mean'))/sigma
    cdf = .5*(1+math.erf(z/math.sqrt(2)))
    pdf = math.exp(-.5*z*z)/math.sqrt(2*math.pi)
    return sigma*(z*(2*cdf-1)+2*pdf-1/math.sqrt(math.pi))


def compare(samples, references, cfg, tick=lambda: None):
    """One fixed family. Numeric access after source qualification; no search or refits of old runs."""
    import numpy as np
    config_check(cfg)
    trace, output, fold_info = [], [], []
    cores = sorted({s.core for s in samples})
    if len(cores) < 3:
        raise NotQualified('insufficient distinct mother cores')
    for held in cores:
        for horizon in cfg['horizons_cycles']:
            tick()
            train = [s for s in samples if s.core != held and s.horizon == horizon]
            query = [s for s in samples if s.core == held and s.horizon == horizon]
            dev = set(cores)-{held}
            if {s.core for s in train} != dev or not query:
                raise NotQualified('missing predeclared core/horizon origins')
            scope = held + '/H' + str(horizon)
            # Sigma only from C whole-core cross-fit inside the development side.
            residual, residual_samples = [], []
            for calibration_core in sorted(dev):
                inner = [s for s in train if s.core != calibration_core]
                cal = [s for s in train if s.core == calibration_core]
                yi = (references.get(inner, dev-{calibration_core}, scope+'/scale/train')-array([s.current_length for s in inner]))/horizon
                inner_model = fit([s.current for s in inner], yi, inner, scope+'/scale/C', trace, tick)
                mu = array([s.current_length for s in cal])+horizon*inner_model.predict([s.current for s in cal])
                residual.extend((references.get(cal, {calibration_core}, scope+'/scale/calibrate')-mu).tolist())
                residual_samples.extend(cal)
            sigma = max(cfg['sigma_floor_mm'], math.sqrt(float(core_weights(residual_samples) @ (array(residual)**2))))
            y = (references.get(train, dev, scope+'/final/train')-array([s.current_length for s in train]))/horizon
            ctrain, cquery = array([s.current for s in train]), array([s.current for s in query])
            gtrain, gquery = array([s.g for s in train]), array([s.g for s in query])
            cm = fit(ctrain, y, train, scope+'/final/C', trace, tick)
            gm = fit(gtrain, y, train, scope+'/final/G', trace, tick)
            ht, hq = array([s.history for s in train]), array([s.history for s in query])
            m = fit(ctrain, ht, train, scope+'/input/m', trace, tick, locked=(cm.mean, cm.scale))
            et, eq = ht-m.predict(ctrain), hq-m.predict(cquery)
            em, es = standardize(et, train)
            # Both H and D get exactly this transform/penalty; C prefix is unchanged.
            locked = np.r_[cm.mean, em], np.r_[cm.scale, es]
            hm = fit(np.c_[ctrain, et], y, train, scope+'/final/H', trace, tick, locked=locked)
            train_donor, train_reason, train_dist = donors(train, train, cm.mean[:gtrain.shape[1]], cm.scale[:gtrain.shape[1]], cfg)
            query_donor, query_reason, query_dist = donors(train, query, cm.mean[:gtrain.shape[1]], cm.scale[:gtrain.shape[1]], cfg)
            dm = None
            if all(i is not None for i in train_donor):
                dm = fit(np.c_[ctrain, et[train_donor]], y, train, scope+'/final/D', trace, tick, locked=locked)
            rates = {'C': cm.predict(cquery), 'G': gm.predict(gquery), 'H': hm.predict(np.c_[cquery, eq])}
            # Query-only unsupported D stays unavailable; it never drops an H/C origin.
            dmeans = {}
            if dm is not None:
                supported = [i for i, donor in enumerate(query_donor) if donor is not None]
                if supported:
                    dp = dm.predict(np.c_[cquery[supported], et[[query_donor[i] for i in supported]]])
                    dmeans = dict(zip(supported, dp.tolist()))
            truth = references.get(query, {held}, scope+'/outer/evaluate_after_fit')
            for i, s in enumerate(query):
                tick()
                d_reason = query_reason[i] if dm is not None else 'TRAIN_DONOR_UNSUPPORTED_NO_D_FIT'
                mus = {'G': s.current_length+horizon*rates['G'][i],
                       'C': s.current_length+horizon*rates['C'][i],
                       'H': s.current_length+horizon*rates['H'][i],
                       'D': None if i not in dmeans else s.current_length+horizon*dmeans[i],
                       'P': s.current_length, 'S': s.current_length+horizon*s.growth}
                for arm in ARMS:
                    mu = mus[arm]
                    output.append({'sample_key': s.key, 'core_id': held, 'test_id': s.test, 'origin_cycle': s.origin,
                                   'H_cycles': horizon, 'arm': arm, 'mu_mm': None if mu is None else float(mu),
                                   'sigma_mm': sigma, 'reference_id': s.reference_id, 'reference_mm': float(truth[i]),
                                   'crps_mm': None if mu is None else gaussian_crps(mu, sigma, truth[i]),
                                   'increment_mae_mm': None if mu is None else abs(float(mu-truth[i])),
                                   'status': 'DONOR_UNSUPPORTED' if mu is None else 'AVAILABLE',
                                   'reason': d_reason if mu is None else None})
            fold_info.append({'held_core': held, 'H_cycles': horizon, 'development_cores': sorted(dev), 'sigma_mm': sigma,
                              'sigma_basis': 'C development-core crossfit RMS, equal-core; floor declared before outer outcomes',
                              'training_keys': [s.key for s in train], 'query_keys': [s.key for s in query],
                              'train_donor_keys': [None if i is None else train[i].key for i in train_donor],
                              'query_donor_keys': [None if i is None else train[i].key for i in query_donor],
                              'train_donor_reasons': train_reason, 'query_donor_reasons': query_reason,
                              'train_donor_distances': train_dist, 'query_donor_distances': query_dist,
                              'donor_training_supported': dm is not None})
    cells = defaultdict(list)
    for row in output:
        cells[row['core_id'], row['H_cycles'], row['arm']].append(row)
    per_core = []
    for (core, h, arm), rr in sorted(cells.items()):
        complete = all(r['status'] == 'AVAILABLE' for r in rr)
        per_core.append({'core_id': core, 'H_cycles': h, 'arm': arm, 'n_planned': len(rr),
                         'n_available': sum(r['status'] == 'AVAILABLE' for r in rr),
                         'crps_mm': sum(r['crps_mm'] for r in rr)/len(rr) if complete else None,
                         'increment_mae_mm': sum(r['increment_mae_mm'] for r in rr)/len(rr) if complete else None,
                         'status': 'COMPLETE' if complete else 'NOT_INTERPRETABLE_NO_ORIGIN_EXCLUSION'})
    lookup = {(r['core_id'], r['H_cycles'], r['arm']): r for r in per_core}
    by_h = {}
    for h in cfg['horizons_cycles']:
        means = {}
        for arm in ARMS:
            values = [lookup[core, h, arm]['crps_mm'] for core in cores]
            means[arm] = None if any(v is None for v in values) else sum(values)/len(values)
        by_h[str(h)] = {'equal_core_crps_mm': means,
                       'delta_state_H_minus_C_mm': means['H']-means['C'],
                       'H_minus_comparators_mm': {arm: None if means[arm] is None else means['H']-means[arm] for arm in ('D', 'G', 'P', 'S')}}
    primary = by_h[str(cfg['primary_horizon_cycles'])]
    paired_core = []
    for core in cores:
        h = cfg['primary_horizon_cycles']
        per = {arm: lookup[core, h, arm]['crps_mm'] for arm in ARMS}
        paired_core.append({'core_id': core, 'primary_H_cycles': h,
                            'delta_state_H_minus_C_mm': per['H']-per['C'],
                            'H_minus_comparators_mm': {arm: None if per[arm] is None else per['H']-per[arm] for arm in ('D','G','P','S')},
                            'largest_reference_resolution_mm': max(s.resolution_mm for s in samples if s.core == core and s.horizon == h)})
    return {'scope': 'CONDITIONAL_STATE_COMPARISON_E0_NOT_OBSERVATION_UQ_ABC',
            'predictions': output, 'per_core': per_core, 'by_horizon': by_h,
            'primary_delta_state_mm': primary['delta_state_H_minus_C_mm'], 'primary_per_core': paired_core,
            'reference_effect_delta_mm': cfg['reference_effect_delta_mm'],
            'method_fit_trace': trace, 'folds': fold_info, 'reference_access_log': references.access_log,
            'fit_counts': dict(Counter(t['role'].split('/')[-2] for t in trace)),
            'actual_closed_form_solves': len(trace), 'no_model_or_weight_search': True,
            'interpretation': 'negative primary favors own history under shared E0; reference resolution, donor support and core stability still govern scientific route'}


def inspect_real_case(case, cfg, authority=None):
    """Metadata-only admission report. Does not open any scientific numerical file."""
    case = Path(case)
    metadata = json.loads((case/'state_interface_preparation_20261020/received_metadata.json').read_text())
    missing = [n for n in ('entities', 'frame_load_join', 'response_catalog', 'reference_catalog', 'origins', 'splits') if not metadata.get(n)]
    unbound = []
    try:
        config_check(cfg)
    except (NotQualified, TypeError, KeyError) as e:
        unbound.append(str(e))
    bindings_path = case/'state_interface_preparation_20261020/minimum_source_bindings.json'
    bindings = json.loads(bindings_path.read_text()) if bindings_path.exists() else {}
    if not bindings.get('dataset_id') or not bindings.get('files') or not bindings.get('normalized_payload_relative_path'):
        unbound.append('actual source files, permission and normalized numerical payload unbound')
    permitted = bool(authority and authority.get('scope') == 'SCB_STATE_FOUR_ARM_CPU' and authority.get('scientific_run_authorized') is True)
    ready = not missing and not unbound and permitted
    return {'status': 'DECLARED_READY_REQUIRES_PRODUCER_CHECK' if ready else 'REFUSED_UNBOUND_OR_UNAUTHORIZED_REAL_EXECUTION',
            'missing_metadata_tables': missing, 'unbound': unbound, 'execution_permission_present': permitted,
            'scientific_payloads_opened': 0, 'real_fits': 0, 'actual_core_count': None if not metadata.get('entities') else len({r['core_id'] for r in metadata['entities']}),
            'source_request': str(bindings_path)}


def _real_run(case, cfg, authority, out):
    real_started = time.monotonic()
    report = inspect_real_case(case, cfg, authority)
    if report['status'] != 'DECLARED_READY_REQUIRES_PRODUCER_CHECK':
        return report
    # This is a future authorized producer entry, never the artificial benchmark route.
    if platform.system() != 'Linux' or platform.node() != authority.get('approved_hostname'):
        raise PermissionError('real scientific fitting only on the explicitly approved Linux CPU producer, never Mac')
    budget = cfg['execution_budget']
    if any(not isinstance(budget.get(k), (int, float)) or budget[k] <= 0 for k in ('total_wall_seconds', 'max_address_space_bytes', 'max_source_bytes', 'max_output_bytes')):
        raise PermissionError('complete scientific budget not approved')
    if authority.get('budget') != budget or not authority.get('permission_reference'):
        raise PermissionError('data permission and one consolidated budget decision required')
    case, out = Path(case).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError('retain prior output; no overwriting')
    binding = json.loads((case/'state_interface_preparation_20261020/minimum_source_bindings.json').read_text())
    if binding['dataset_id'] != authority.get('dataset_id') or not binding.get('permission_reference'):
        raise PermissionError('source/permission binding mismatch')
    if cfg.get('real_scientific_execution_authorized') is not True:
        raise PermissionError('real execution remains disabled')
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_AS, (min(int(budget['max_address_space_bytes']), 8*2**30),)*2)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    started = real_started
    def tick(*_):
        if time.monotonic()-started >= budget['total_wall_seconds']:
            raise TimeoutError('whole authorized CPU task deadline')
    def alarm(*_):
        raise TimeoutError('whole authorized CPU task deadline')
    signal.signal(signal.SIGALRM, alarm)
    remaining = budget['total_wall_seconds']-(time.monotonic()-started)
    if remaining <= 0:
        raise TimeoutError('whole task expired during metadata admission')
    signal.setitimer(signal.ITIMER_REAL, remaining)
    out.mkdir(parents=True, exist_ok=False)
    try:
        files = binding['files']
        if sum(f['bytes'] for f in files) > budget['max_source_bytes']:
            raise NotQualified('source volume exceeds approved budget')
        manifest = {}; source_ids = set()
        for f in files:
            tick()
            p = case/f['relative_path']
            if Path(f['relative_path']).is_absolute() or '..' in Path(f['relative_path']).parts or p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(case):
                raise NotQualified('source path must be an explicit case-local bound file')
            if not f.get('permission_reference') or not f.get('asset_id') or f['relative_path'] in manifest or f['asset_id'] in source_ids:
                raise NotQualified('source permission/duplicate identity')
            h = hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    tick(); h.update(block)
            if p.stat().st_size != f['bytes'] or h.hexdigest() != f['sha256']:
                raise NotQualified('source scientific identity mismatch')
            manifest[f['relative_path']] = f; source_ids.add(f['asset_id'])
        rel = binding['normalized_payload_relative_path']
        if rel not in manifest:
            raise NotQualified('normalized payload must be in the qualified source manifest')
        metadata = json.loads((case/'state_interface_preparation_20261020/received_metadata.json').read_text())
        # Every logical observation/source ID must have a delivered file or a
        # documented lineage record. Existing author DIC exports need not pretend
        # that the original camera images have been received.
        proof = binding.get('asset_evidence', {})
        for table, fields in {'entities':['entity_source_asset_id'],
                              'frame_load_join':['left_asset_id','right_asset_id','machine_source_asset_id','sync_source_asset_id'],
                              'response_catalog':['response_asset_id','geometry_asset_id'],
                              'reference_catalog':['reference_source_asset_id'],
                              'origins':['load_plan_asset_id']}.items():
            for row in metadata[table]:
                for field in fields:
                    ident = row[field]
                    evidence = proof.get(ident, {})
                    if ident not in source_ids and not (evidence.get('evidence_asset_id') in source_ids and evidence.get('kind') in ('direct_file','documented_lineage')):
                        raise NotQualified('unbound physical source identity: '+ident)
        processing = binding.get('processing_qualification', {})
        if processing.get('qualification_record_asset_id') not in source_ids:
            raise NotQualified('common ROI/calibration/feature and independent-reference qualification record missing')
        for table, field, declared in [('response_catalog','feature_pipeline_id','feature_pipeline_ids'),
                                        ('frame_load_join','registration_id','registration_ids'),
                                        ('origins','roi_id','roi_ids')]:
            if not {r[field] for r in metadata[table]} <= set(processing.get(declared, [])):
                raise NotQualified('processing/ROI identity not bound')
        payload = json.loads((case/rel).read_text())
        samples, refs, audit = adapt_normalized(metadata, payload, cfg)
        result = compare(samples, refs, cfg, tick)
        blob=(json.dumps(result, indent=2, allow_nan=False)+'\n').encode()
        if len(blob) > budget['max_output_bytes']:
            raise NotQualified('output budget before publication')
        (out/'result.json').write_bytes(blob)
        (out/'receipt.json').write_text(json.dumps({'status': 'COMPLETED_CONDITIONAL_COMPARISON', 'audit': audit,
            'hostname': platform.node(), 'elapsed_seconds': time.monotonic()-started, 'dataset_id': binding['dataset_id'],
            'budget': budget, 'real_scientific_execution_authorized': True}, indent=2)+'\n')
        tick()
        return {'status': 'COMPLETED_CONDITIONAL_COMPARISON', 'output': str(out)}
    except BaseException as e:
        (out/'failure.json').write_text(json.dumps({'status': 'STOPPED', 'error': type(e).__name__+': '+str(e), 'elapsed_seconds': time.monotonic()-started}, indent=2)+'\n')
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['inspect', 'run'])
    p.add_argument('--case', required=True)
    p.add_argument('--config', default=str(Path(__file__).with_name('scb_state_config.json')))
    p.add_argument('--authority'); p.add_argument('--out')
    args=p.parse_args(); cfg=json.loads(Path(args.config).read_text())
    authority=json.loads(Path(args.authority).read_text()) if args.authority else None
    if args.mode == 'run':
        if not args.out:
            p.error('--out required for scientific run')
        result=_real_run(args.case, cfg, authority, args.out)
    else:
        result=inspect_real_case(args.case, cfg, authority)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] != 'REFUSED_UNBOUND_OR_UNAUTHORIZED_REAL_EXECUTION' else 2


if __name__ == '__main__':
    raise SystemExit(main())
