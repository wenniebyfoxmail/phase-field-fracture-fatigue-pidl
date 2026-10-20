"""Bind existing archived source text and state headers, without numerical replay."""
import argparse
import hashlib
import json
from pathlib import Path

import h5py


def source_entry(root, relative, expected):
    path = root/relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"archived source identity changed: {relative}")
    return dict(path=str(path), sha256=actual, matches_existing_lock=True)


def location(path, needle):
    lines = path.read_text().splitlines()
    matches = [i+1 for i, line in enumerate(lines) if needle in line]
    if not matches:
        raise ValueError(f"required source anchor missing: {needle}")
    return dict(path=str(path), line=matches[0], matching_lines=matches,
                literal=needle)


def schema(path, group):
    with h5py.File(path) as h:
        return {name: dict(shape=list(obj.shape), dtype=str(obj.dtype))
                for name,obj in h[group].items() if isinstance(obj,h5py.Dataset)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--source-lock', required=True, type=Path)
    parser.add_argument('--case', required=True, type=Path)
    parser.add_argument('--common-initial', required=True, type=Path)
    parser.add_argument('--step-post-source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    a = parser.parse_args()
    locks = json.loads(a.source_lock.read_text())
    sources = {name:source_entry(a.source_root,name,expected) for name,expected in locks.items()}
    runner = a.source_root/'Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m'
    init = a.source_root/'Scripts/fatigue_fracture/init_fatigue_fracture.m'
    solve = a.source_root/'Scripts/fatigue_fracture/solve_fatigue_fracture.m'
    stag = a.source_root/'Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m'
    anchors = dict(
        zero_u=location(init,'displ       = zeros'),
        zero_history=location(init,'history_vars_old = zeros'),
        recovery_call=location(runner,'res_pf_recovery, p_field'),
        reset_A=location(runner,'history_vars_old(:,:,2) = 0.0'),
        reset_q=location(runner,'history_vars_old(:,:,3) = 0.0'),
        reset_f=location(runner,'history_vars_old(:,:,4) = 1.0'),
        state0_saved=location(runner,"'state0_node', 'state0_p_field'"),
        boundary=location(runner,"'fix_Y', NODESET.bot_edge, 'disp_Y', NODESET.top_edge"),
        commit_lower=location(solve,'p_field_old = p_field;'),
        optional_clip=location(solve,'p_field = min(p_field, damage_upper_bound);'),
        history_commit=location(solve,'[~, ~, ~, history_vars_old] = assembly_pf_fh'),
        scalar_response=location(solve,'SOL_STEP_VAR = phase_field.fem.solver.step.post_iter_update'),
        post_snapshot=location(solve,'phase_field.audit.capture_post_commit_state(request28_state)'),
        peak_oracle=location(solve,'matlab_residual = phase_field.audit.assemble_residual_oracle'),
        cached_stiffness=location(stag,'KK_updated = sparse'),
        mirror_Fy=location(a.step_post_source,'SOL_STEP_VAR.F_Y(i_step) = - sum'))
    scalar = {}
    with h5py.File(a.case/'initial_state_metadata.mat') as h:
        g=h['initial_state_metadata']
        for name in ('Umax','R','alpha_T','alpha_bar_initial','driver_degraded_initial','f_alpha_initial','n_step','recovery_residual'):
            scalar[name]=float(g[name][()].item())
    if scalar['alpha_bar_initial'] != 0 or scalar['driver_degraded_initial'] != 0 or scalar['f_alpha_initial'] != 1:
        raise ValueError('initial reset scalar contract differs')
    with h5py.File(a.common_initial) as h:
        common_version=float(h['common/version'][()].item())
        source_commit=''.join(chr(int(x)) for x in h['common_meta/source_commit'][()].ravel())
        stored_error=float(h['common_meta/state0_maxerr'][()].item())
    if common_version != 0:
        raise ValueError('common initial is not version0')
    result=dict(scope='offline source/header binding only; no scientific-array decode or FEM',
        sources=sources, anchors=anchors,
        initial=dict(raw_state0=str(a.case/'state0_analysis.mat'),
            raw_state0_schema=schema(a.case/'state0_analysis.mat','/'),
            reset_metadata=scalar, recovery_is_physical_cycle=False,
            complete_common_state=str(a.common_initial), common_schema=schema(a.common_initial,'common'),
            common_source_commit=source_commit, common_version=common_version,
            existing_stored_state0_maxerr=stored_error,
            status='full common-state header exists; stored scalar comparison reused, no new array equivalence check',
            derivative_policy='fixed_recovered_profile, zero initial tangents by declared inverse problem; do not claim recovery was differentiated'),
        reaction=dict(boundary='fixed bottom Y nodes (minimum y), sign minus internal-force sum',
            matlab_dofs='fix_Y + N in 1-based [ux_all;uy_all]',
            python_dofs='2*(node_id_matlab-1)+1 in interleaved 0-based ordering',
            scalar_file_phase='written after history commit using final-staggered cached K',
            force_state='cached K assembled before possible damage clipping/history commit; not guaranteed exact post-clip snapshot force',
            peak_oracle_phase='separate freshly assembled converged peak, BEFORE damage/history commit, with frozen pre_phase history/lower',
            target_new_contract='fresh force at exact supplied u,d; source family, units and phase must match',
            step_source_mirror=dict(path=str(a.step_post_source),sha256=hashlib.sha256(a.step_post_source.read_bytes()).hexdigest(),
                status='local library mirror; exact legacy producer blob not in four-file source lock'),
            remaining='original scalar-vs-fresh-force equivalence and recovery/common array identity need authorized numerical comparison'),
        snapshot=dict(first_file=str(a.case/'request28_post_commit/c0001_s001_post_commit.mat'),
            field_schema=schema(a.case/'request28_post_commit/c0001_s001_post_commit.mat','request28_snapshot'),
            phase='post damage/history commit and cyclemax update; opaque channel1 preserved'),
        qualifications=dict(source_text_and_headers=True, numerical_equivalence=False,
            original_solver_matches_changed_nodalK_model=False, native_execution_authorized=False))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'source_files_matched':len(sources),'output':str(a.output),'numerical_replay':False}))


if __name__=='__main__':
    main()
