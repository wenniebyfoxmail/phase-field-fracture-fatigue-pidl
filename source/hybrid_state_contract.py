"""Accepted-state envelope for the existing hybrid solver, never a new solver.

Old archives remain readable but cannot be silently qualified for new labels
or scoring. Physical keys describe prescribed load states, not wall time.
"""
from dataclasses import replace
import hashlib
import json

import numpy as np

from hybrid_history import frozen_array


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def array_id(value):
    a = np.ascontiguousarray(value, dtype=np.float64)
    return hashlib.sha256(str(a.shape).encode() + a.tobytes()).hexdigest()


FIELD_CONTRACT = {
    'schema': 'hybrid-accepted-field-timing-v1',
    'family': 'AT1-Amor-Carrara-eta0-nodal-K-v1',
    'physical_key_fields': ['initial_state_id','inputs_sha256','mesh_id','physics_id',
                            'settings_id','coupling_policy_id','schedule_id','boundary_id',
                            'reaction_dofs','step','cycle','substep','prescribed_load','branch','time_basis'],
    'transaction': 'parent state fingerprint; numeric state fingerprint; context and evidence hashes bound to certificate; atomic NPZ',
    'support': {'nodal': 'original Q4 nodes; u interleaved x,y',
                'gp': 'original element order; Q4 GP (++),(-+),(+-),(--)'},
    'fields': {
        'displacement': ['nodal', 'accepted fresh mechanical equilibrium at final damage'],
        'damage': ['nodal', 'accepted box-QP solution; own old accepted damage is lower bound'],
        'accumulated': ['gp', 'commit trial from fixed old accepted A,r and final u,d; once only'],
        'driver': ['gp', 'commit (1-d_GP)^2 psi_raw(final u); current value, not history maximum'],
        'fatigue': ['gp', 'f_commit=f(A_commit); accepted fresh check, not last QP input'],
        'f_solve_gp': ['gp', 'actual coefficient in last solved damage QP, before final re-equilibrium'],
        'psi_raw_commit_gp': ['gp', 'undegraded tensile energy from final accepted displacement'],
        'opaque': ['source support', 'inherited unchanged; no physical update claimed'],
        'reaction': ['ordered constrained dofs', 'fresh equilibrium at accepted u,d'],
        'features_old': ['nodal/GP to nodal', 'old accepted state only'],
        'u_pred,psi_pred': ['nodal,gp', 'common mechanical predictor at old damage, target load; before damage solve'],
        'NN_output': ['nodal', 'feasible damage initializer only; never accepted damage or teacher'],
        'd_target': ['nodal', 'accepted output damage; target only, never an input feature'],
    },
}
CONTRACT_ID = digest(FIELD_CONTRACT)
EVIDENCE_NAMES = ('f_solve_gp', 'psi_raw_commit_gp')
FEATURE_TIMING = 'old_accepted_plus_common_mechanical_predictor_before_damage_solve'


def step_context(card, spec, state, step, dofs, unit_bc):
    from dataclasses import asdict
    from hybrid_incremental import SolverSettings
    from hybrid_coupled_acceleration import CouplingSettings
    base = np.asarray(card['base_load_cycle'], dtype=float)
    amplitude = float(spec['amplitude_multiplier'])
    if (base.ndim != 1 or not len(base) or not np.isfinite(base).all()
            or not np.isfinite(amplitude) or amplitude <= 0
            or type(step) is not int or not 0 <= step <= spec['cycles'] * len(base)):
        raise ValueError('invalid physical load context')
    if step:
        cycle, sub = divmod(step - 1, len(base))
        load = float(base[sub] * amplitude)
        branch = 'unloaded' if load == 0 else ('peak' if base[sub] == base.max() else 'loading')
        cycle, sub = cycle + 1, sub + 1
    else:
        cycle, sub, load, branch = 0, 0, 0., 'initial'
    physical = dict(mesh_id=state.mesh_id, physics_id=state.physics_id,
                    initial_state_id=card['state0_id'], inputs_sha256=card['inputs_sha256'],
                    settings_id=digest(asdict(SolverSettings(**card['solver']))),
                    coupling_policy_id=digest(asdict(CouplingSettings(**card.get('coupling',{})))),
                    schedule_id=digest(dict(base=base.tolist(), amplitude=amplitude)),
                    boundary_id=digest(dict(dofs=np.asarray(dofs).tolist(), unit_values=np.asarray(unit_bc).tolist())),
                    reaction_dofs=np.asarray(dofs).tolist(),
                    step=step, cycle=cycle, substep=sub, prescribed_load=load, branch=branch,
                    time_basis='prescribed_quasistatic_load_not_wall_time')
    return dict(trajectory_id=spec['id'], physical=physical)


def envelope(state, context, parent_id, evidence):
    return dict(contract_id=CONTRACT_ID, state_id=state.fingerprint(), parent_id=parent_id,
                context=context, evidence_sha256={k: array_id(v) for k, v in evidence.items()})


def bind_proposal(proposal, context):
    evidence = {k: frozen_array(proposal.field_evidence[k]) for k in EVIDENCE_NAMES}
    contract = envelope(proposal.state, context, proposal.previous_id, evidence)
    certificate = dict(proposal.certificate, state_contract_id=CONTRACT_ID,
                       state_envelope_sha256=digest(contract))
    result = replace(proposal, certificate=certificate, accepted_contract=contract, field_evidence=evidence)
    verify_envelope(result.state, dict(state_contract=contract, certificate=certificate), evidence)
    return result


def verify_envelope(state, metadata, evidence):
    c = metadata.get('state_contract')
    if not isinstance(c, dict) or c.get('contract_id') != CONTRACT_ID:
        raise RuntimeError('missing/incompatible accepted-state field timing contract')
    physical = c['context']['physical']
    if (c.get('state_id') != state.fingerprint() or physical['step'] != state.load_index
            or physical['mesh_id'] != state.mesh_id or physical['physics_id'] != state.physics_id
            or not c['context']['trajectory_id']):
        raise RuntimeError('accepted-state context/identity mismatch')
    initial = state.load_index == 0
    if initial:
        if (c['parent_id'] is not None or evidence or c['evidence_sha256']
                or physical['initial_state_id'] != state.fingerprint()):
            raise RuntimeError('initial state cannot pretend to be an accepted transition')
    else:
        cert = metadata.get('certificate', {})
        if (set(evidence) != set(EVIDENCE_NAMES) or not c.get('parent_id')
                or cert.get('passed') is not True or cert.get('state_id') != state.fingerprint()
                or cert.get('previous_id') != c['parent_id']
                or cert.get('state_contract_id') != CONTRACT_ID
                or cert.get('settings_id') != physical['settings_id']
                or cert.get('coupling_policy_id') != physical['coupling_policy_id']
                or cert.get('state_envelope_sha256') != digest(c)):
            raise RuntimeError('accepted-state certificate/envelope mismatch')
        for k, a in evidence.items():
            if (a.shape != state.fatigue.shape or not np.isfinite(a).all()
                    or array_id(a) != c['evidence_sha256'].get(k)):
                raise RuntimeError('field evidence support/digest mismatch')
        f = evidence['f_solve_gp']
        if np.any(f < 0) or np.any(f > 1) or np.any(evidence['psi_raw_commit_gp'] < 0):
            raise RuntimeError('invalid field evidence range')
        # The two coefficients need not be identical: their measured difference
        # is the existing solver acceptance residual, not a new relaxed bound.
        measured = float(np.max(np.abs(f - state.fatigue)))
        if not np.isclose(measured, cert['fatigue_residual'], rtol=1.e-12, atol=1.e-15):
            raise RuntimeError('f_solve/f_commit residual evidence mismatch')
    if c['evidence_sha256'] != {k: array_id(v) for k, v in evidence.items()}:
        raise RuntimeError('unexpected field evidence')
    return c


def verify_transition(old, old_meta, new, new_meta):
    a, b = old_meta.get('state_contract'), new_meta.get('state_contract')
    if not a or not b or a['contract_id'] != CONTRACT_ID or b['contract_id'] != CONTRACT_ID:
        raise RuntimeError('legacy/uncontracted state is not a prospective label')
    ac, bc = a['context'], b['context']
    if (b['parent_id'] != old.fingerprint() or new.load_index != old.load_index + 1
            or ac['trajectory_id'] != bc['trajectory_id']
            or any(ac['physical'][k] != bc['physical'][k]
                   for k in ('schedule_id', 'boundary_id', 'mesh_id', 'physics_id',
                             'initial_state_id', 'inputs_sha256', 'settings_id', 'coupling_policy_id',
                             'reaction_dofs'))):
        raise RuntimeError('accepted predecessor/trajectory context mismatch')


def verify_expected(state, metadata, expected):
    if metadata.get('state_contract', {}).get('context') != expected:
        raise RuntimeError('physical cycle/substep/load/trajectory mismatch')
    if state.load_index != expected['physical']['step']:
        raise RuntimeError('physical step mismatch')
    if state.load_index and metadata['certificate']['mechanics']['reaction_dofs'] != expected['physical']['reaction_dofs']:
        raise RuntimeError('reaction support/order differs from prescribed boundary')


def verify_comparable(a, am, b, bm):
    if (am.get('state_contract', {}).get('contract_id') != CONTRACT_ID
            or bm.get('state_contract', {}).get('contract_id') != CONTRACT_ID
            or am['state_contract']['context']['physical'] != bm['state_contract']['context']['physical']
            or a.mesh_id != b.mesh_id or a.physics_id != b.physics_id):
        raise RuntimeError('cannot compare different physical states or field timings')
    if am['certificate']['mechanics']['reaction_dofs'] != bm['certificate']['mechanics']['reaction_dofs']:
        raise RuntimeError('reaction support/order differs')
