"""S04-E027-SYNMEM: lawful histories with a fixed common continuation.

No training, field splicing, parameter search or legacy-data loading. Calling
run_experiment is scientific execution; the Linux supervisor is the only CLI.
"""
from dataclasses import asdict
from pathlib import Path
import shutil
from time import monotonic

import numpy as np

from hybrid_coupled_acceleration import CouplingSettings
from hybrid_incremental import NativeQ4Backend, SolverSettings, solve_step
from hybrid_kinematics import build_portable_native_q4_kinematics
from hybrid_producer_common import write_json, append_event, object_sha, compare_states
from hybrid_state_contract import bind_proposal, verify_expected
from hybrid_transaction import StateStore
from hybrid_work_trace import PersistentWorkTrace
from synthetic_history_inputs import (structured_q4_mesh, unsettled_zero_state,
                                     build_branch_schedule, make_pair_contract,
                                     verify_pair_contract)
from synthetic_history_observation import (mask_of, camera_damage, current_match,
                                          robust_difference, numeric_fields_equal)


def frozen_spec():
    return dict(
        experiment_id='S04-E027-SYNMEM', protocol='1.0', domain='synthetic',
        claim='whether fixed digital geometry aliases histories with distinct common-load futures',
        geometry=dict(domain=[-.5, .5, -.5, .5], crack_tip=0.),
        material=dict(youngs_modulus=1., poisson_ratio=.3, gc=.01,
                      length_scale=.125, alpha_t=.005, power=2., thickness=1.),
        variants=[dict(id='base', cells=16, subdivisions=1),
                  dict(id='space', cells=32, subdivisions=1),
                  dict(id='load_step', cells=16, subdivisions=2)],
        cycle_fractions=[.25, .5, .75, 1., 0.],
        histories=dict(low=[.005]*20, high=[.010]*20),
        probe=[.005], future=[.030]*20, horizons=[5, 10, 20], primary_horizon=20,
        observation=dict(pixels=64, threshold=.5, sensitivity_thresholds=[.45, .55],
                         matching='exact whole mask across 2 arms and 3 variants'),
        solver=asdict(SolverSettings(force_scale=1., damage_gradient_scale=1., wall_seconds=120.)),
        coupling=asdict(CouplingSettings(mode='projected_anderson_monotone',
                                         max_rejections=3, mechanics_solver='direct')),
        budget=dict(wall_seconds=14400, cpu_threads=4, gpu_count=0,
                    ram_bytes=8*1024**3, storage_bytes=8*1024**3,
                    maximum_steps=1846, step_hard_seconds=120., cleanup_seconds=20),
        producer=dict(alias='gpu-server', hostname='GPUServer8',
                      root='/mnt/data2/drtao/wennie'),
        stop='first scientific/numerical/resource failure; no automatic retry or resume')


def validate_spec(spec):
    if spec != frozen_spec():
        raise ValueError('spec differs from reviewed SYNMEM 1.0; amend and review before execution')
    return dict(maximum_steps=1846, trajectories=6, restart_suffixes=2,
                primary_horizon=20, execution_authorized=False)


def subdivide(fractions, count):
    previous = 0.
    output = []
    for value in fractions:
        output.extend(previous + (value-previous)*i/count for i in range(1, count+1))
        previous = value
    return output


def schedule_for(spec, variant, arm):
    return build_branch_schedule(
        trajectory_id=variant['id']+'_'+arm,
        prehistory_amplitudes=spec['histories'][arm], probe_amplitudes=spec['probe'],
        future_amplitudes=spec['future'],
        fractions=subdivide(spec['cycle_fractions'], variant['subdivisions']))


class Trajectory:
    def __init__(self, spec, variant, arm, root, source_id, marker):
        self.spec, self.variant, self.arm = spec, variant, arm
        self.path = Path(root)/(variant['id']+'_'+arm)
        self.path.mkdir()
        (self.path/'states').mkdir()
        self.marker = marker
        self.mesh = structured_q4_mesh(variant['cells'], variant['cells'], 0.)
        kin = build_portable_native_q4_kinematics(self.mesh.points, self.mesh.cells)
        self.backend = NativeQ4Backend(kin, self.mesh.crack, **spec['material'])
        self.old = unsettled_zero_state(self.mesh, mesh_id=self.backend.mesh_id,
                                        physics_id=self.backend.physics_id)
        self.initial_id = self.old.fingerprint()
        # Symmetric vertical opening; one horizontal pin removes translation.
        self.dofs = np.concatenate((2*self.mesh.bottom_nodes+1,
                                    2*self.mesh.top_nodes+1,
                                    [2*self.mesh.bottom_nodes[0]])).astype(np.int64)
        self.unit = np.concatenate((np.full(len(self.mesh.bottom_nodes), -.5),
                                    np.full(len(self.mesh.top_nodes), .5), [0.]))
        self.schedule = schedule_for(spec, variant, arm)
        self.origin = max(s.step for s in self.schedule if s.segment == 'probe')
        self.pair = make_pair_contract(source_id=source_id, root_state=self.old,
                                      material=spec['material'], boundary_dofs=self.dofs,
                                      boundary_unit_values=self.unit, schedule=self.schedule,
                                      origin_step=self.origin)
        self.settings = SolverSettings(**spec['solver'])
        self.coupling = CouplingSettings(**spec['coupling'])
        self.store = StateStore(self.path/'latest.npz')
        self.store.initialize(self.old, context=self.context(self.old, 0))
        shutil.copy2(self.store.path, self.state_path(0))
        write_json(self.path/'schedule.json', [asdict(s) for s in self.schedule])
        write_json(self.path/'pair_contract.json', asdict(self.pair))
        np.savez(self.path/'mesh.npz', points=self.mesh.points, cells=self.mesh.cells,
                 crack=self.mesh.crack, dofs=self.dofs, unit=self.unit)

    def context(self, state, index):
        load = self.schedule[index-1] if index else None
        physical = dict(
            initial_state_id=self.initial_id, inputs_sha256=object_sha(self.spec),
            mesh_id=state.mesh_id, physics_id=state.physics_id,
            settings_id=object_sha(asdict(self.settings)),
            coupling_policy_id=object_sha(asdict(self.coupling)),
            schedule_id=self.pair.schedule_id, boundary_id=self.pair.boundary_id,
            reaction_dofs=self.dofs.tolist(), step=index,
            cycle=load.cycle if load else 0, substep=load.substep if load else 0,
            prescribed_load=load.prescribed_load if load else 0.,
            branch=load.branch if load else 'initial',
            time_basis='prescribed_quasistatic_load_not_wall_time',
            segment=load.segment if load else 'initial',
            segment_cycle=load.segment_cycle if load else 0,
            phase=load.phase if load else 'initial')
        return dict(trajectory_id=self.schedule[0].trajectory_id, physical=physical)

    def state_path(self, step):
        return self.path/'states'/f'state{step:04d}.npz'

    def advance(self, through, *, replay_of=None):
        for load in self.schedule[self.old.load_index:through]:
            self.marker(self.path.name, load.step)
            start = monotonic()
            trace = PersistentWorkTrace(self.path/'work_trace.jsonl', self.path.name, load.step)
            try:
                proposal = solve_step(self.backend, self.old, self.dofs,
                                      self.unit*load.prescribed_load,
                                      next_load_id=f'{load.trajectory_id}:{load.step}:{load.prescribed_load:.17g}',
                                      settings=self.settings, coupling=self.coupling,
                                      work_observer=trace.call, iteration_observer=trace.record_iteration)
            except Exception as exc:
                write_json(self.path/'failure.json', dict(step=load.step, error=repr(exc),
                           accepted_state_id=self.old.fingerprint(), work=getattr(exc, 'work', None)))
                raise
            proposal = bind_proposal(proposal, self.context(proposal.state, load.step))
            self.store.commit(proposal)
            restored, meta = self.store.load()
            verify_expected(restored, meta, self.context(restored, load.step))
            if restored.fingerprint() != proposal.state.fingerprint():
                raise RuntimeError('durable state differs from accepted proposal')
            self.old = restored
            shutil.copy2(self.store.path, self.state_path(load.step))
            if replay_of is not None:
                expected, _ = StateStore(replay_of/f'states/state{load.step:04d}.npz').load()
                if expected.fingerprint() != self.old.fingerprint():
                    raise RuntimeError('full-state restart did not reproduce exact reference')
            append_event(self.path/'steps.jsonl', dict(load=asdict(load), state_id=self.old.fingerprint(),
                          wall_seconds=monotonic()-start, f_min=float(self.old.fatigue.min()),
                          A_max=float(self.old.accumulated.max()), certificate=proposal.certificate))
            self.marker(self.path.name, None)

    def at_cycle(self, cycle):
        candidates = [s.step for s in self.schedule if s.segment == 'future'
                      and s.segment_cycle == cycle]
        return StateStore(self.state_path(max(candidates))).load()[0]

    def replay(self):
        # Rebuild backend to remove hidden workspace/cached-factor state.
        self.backend = NativeQ4Backend(build_portable_native_q4_kinematics(
            self.mesh.points, self.mesh.cells), self.mesh.crack, **self.spec['material'])
        reference = self.path
        origin_path = self.state_path(self.origin)
        self.path = self.path.with_name(self.path.name+'_restart')
        self.path.mkdir(); (self.path/'states').mkdir()
        self.store = StateStore(self.path/'latest.npz')
        shutil.copy2(origin_path, self.store.path)
        self.old, metadata = self.store.load()
        verify_expected(self.old, metadata, self.context(self.old, self.origin))
        shutil.copy2(self.store.path, self.state_path(self.origin))
        self.advance(len(self.schedule), replay_of=reference)
        self.path = reference


def run_experiment(spec, root, source_id, marker):
    validate_spec(spec)
    root = Path(root)
    trajectories = []
    for variant in spec['variants']:
        pair = [Trajectory(spec, variant, arm, root, source_id, marker)
                for arm in ('low', 'high')]
        verify_pair_contract(pair[0].pair, pair[1].pair)
        for trajectory in pair:
            trajectory.advance(1)
        if not numeric_fields_equal(pair[0].old, pair[1].old):
            raise RuntimeError('identical zero-settle yielded different numeric fields')
        for trajectory in pair:
            trajectory.advance(trajectory.origin)
        trajectories.append(pair)
    origin_masks = np.array([[mask_of(t.mesh, t.old) for t in pair] for pair in trajectories])
    match = current_match(origin_masks)
    diagnostics = []
    for pair in trajectories:
        diagnostic = compare_states(pair[0].backend, pair[1].old, pair[0].old)
        probe_states = []
        for t in pair:
            peak = max(s.step for s in t.schedule if s.segment == 'probe' and s.phase == 'peak')
            probe_states.append(StateStore(t.state_path(peak)).load()[0])
        diagnostic.update(variant=pair[0].variant['id'],
            probe_u_difference_inf=float(np.max(abs(probe_states[0].displacement-probe_states[1].displacement))),
            A_max=[float(t.old.accumulated.max()) for t in pair],
            f_min=[float(t.old.fatigue.min()) for t in pair],
            note='hidden-field and full probe-response diagnostics; not matched inputs, not unique A attribution')
        diagnostics.append(diagnostic)
    write_json(root/'origin_state_diagnostics.json', diagnostics)
    write_json(root/'current_match.json', match)
    np.savez(root/'origin_observations.npz', masks=origin_masks,
             sampled_damage=np.array([[camera_damage(t.mesh, t.old.damage) for t in pair]
                                      for pair in trajectories]))
    if not match['anchor_valid']:
        raise RuntimeError('fixed precrack anchor missing from sensor')
    if not match['identical']:
        result = dict(verdict='inconclusive', reason='no fixed current-observation match',
                      future_executed=False, disposition='redesign observation/loading prospectively')
        write_json(root/'result.json', result)
        return result
    for pair in trajectories:
        for trajectory in pair:
            trajectory.advance(len(trajectory.schedule))
    horizons = {}
    for horizon in spec['horizons']:
        masks = np.array([[mask_of(t.mesh, t.at_cycle(horizon)) for t in pair]
                          for pair in trajectories])
        diff = robust_difference(masks)
        np.savez(root/f'future_h{horizon:02d}.npz', masks=masks,
                 robust=diff.pop('robust'), unstable=diff.pop('unstable'))
        horizons[str(horizon)] = diff
    sensitivity = {}
    for threshold in spec['observation']['sensitivity_thresholds']:
        a = np.array([[mask_of(t.mesh, StateStore(t.state_path(t.origin)).load()[0], threshold)
                       for t in pair] for pair in trajectories])
        b = np.array([[mask_of(t.mesh, t.at_cycle(20), threshold) for t in pair]
                      for pair in trajectories])
        d = robust_difference(b)
        sensitivity[str(threshold)] = dict(current=current_match(a),
                                             future_robust_pixels=d['robust_pixels'])
    for trajectory in trajectories[0]:
        trajectory.replay()
    supported = horizons['20']['robust_pixels'] > 0
    result = dict(verdict='supports' if supported else 'negative',
                  scope=spec['claim'], future_executed=True, horizons=horizons,
                  sensitivity_diagnostic_only=sensitivity, full_state_restart='exact',
                  disposition='test stronger observations' if supported else 'do not expand a library from this design',
                  limits='one synthetic configuration; geometry-only; tested numerical sensitivity is not an error bound; no Q2 or physical claim')
    write_json(root/'result.json', result)
    return result
