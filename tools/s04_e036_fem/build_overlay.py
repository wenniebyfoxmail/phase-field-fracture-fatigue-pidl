#!/usr/bin/env python3
"""Build an opt-in FEM source overlay; never modify the input or contact a host.

Accept only the two exact files read from clean CITPC12 source 862992a6 on
2026-10-21. The output is preparation, not an applied or executed repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PINNED = {
    "solve_fatigue_fracture.m": "c1a399b7cd8d659080770af86353f9cbbdc4d775824a31ec4698ed382dd75082",
    "run_SENS_hard_recovery_native_q4_capture.m": "d46dfd5a9ded2e8bdb0f5cc100d1961ff6c7de9d1a1ac3fde57ce3f841ec1c06",
}
PRE_ITER = "        % ========STAGGERED ITERATION==============================================\n"
ACCEPT = "            if stag_converged\n"
COMMIT = """                % update the history variables
                p_field_old = p_field;
                if exist('damage_upper_bound', 'var')
                    p_field_old = min(p_field_old, damage_upper_bound);
                    p_field = min(p_field, damage_upper_bound);
                end
                [~, ~, ~, history_vars_old] = assembly_pf_fh(...
                    sys.MESH, sys.DOFS, sys.GEOM.t,...
                    sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
                    p_field, p_field_old, strain_en_undgr,...
                    sys.stress_state.as_number,...
                    history_vars_old...
                );
"""
START_HOOK = """        % E036 is opt-in; default preserves native control flow and assemblies.
        e036_enabled = exist('e036_final_acceptance','var') && ...
            isstruct(e036_final_acceptance) && e036_final_acceptance.enabled;
        if e036_enabled
            assert(exist('damage_upper_bound','var') && damage_upper_bound == 1, ...
                'E036:Bounds','This adapter requires the audited [old,1] output domain');
            e036_version = (SOL_CYCL_VAR.n_cycle-1)*SOL_STEP_PAR.n_step+i_step-1;
            e036_old = struct('lower',p_field_old,'history',history_vars_old,'version',e036_version);
            e036_fixed_u = setdiff((1:numel(displ))',sys.DOFS.active_dof(:));
            e036_fixed_d = setdiff((1:numel(p_field))',sys.DOFS.active_dof_pf(:));
            e036_bc = struct('fixed_u',e036_fixed_u,'fixed_d',e036_fixed_d, ...
                'u',displ(e036_fixed_u),'d',p_field(e036_fixed_d));
            e036_trace = [];
        end

"""
AUDIT_HOOK = """            if e036_enabled
                assert(isequaln(p_field_old,e036_old.lower) && ...
                    isequaln(history_vars_old,e036_old.history), ...
                    'E036:Preimage','Accepted history changed during the substep');
                e036_native_accepted = stag_converged;
                [e036_audit,e036_proposal] = phase_field.audit.e036_native_candidate( ...
                    sys,assembly_equilibrium_fh,assembly_pf_fh,displ,p_field, ...
                    damage_upper_bound,e036_old,e036_bc,D_RHS_tract, ...
                    e036_final_acceptance.policy,history_vars_new(:,:,4));
                e036_row = struct('outer',i_stag,'native_accepted',e036_native_accepted, ...
                    'joint_pass',e036_audit.joint_pass,'u_l2',e036_audit.u_free_l2, ...
                    'd_raw_l2',e036_audit.d_raw_free_l2,'d_box_l2',e036_audit.d_nodal_box_l2, ...
                    'criterion',e036_audit.criterion,'feasible',e036_audit.feasible, ...
                    'assemblies_u',e036_audit.assembly_calls_u,'assemblies_d',e036_audit.assembly_calls_d);
                if isempty(e036_trace),e036_trace=e036_row;else,e036_trace(end+1)=e036_row;end
                stag_converged = e036_audit.joint_pass;
                strain_en_undgr = e036_audit.raw;
            end
"""
COMMIT_HOOK = """                if e036_enabled
                    assert(e036_audit.joint_pass && ~isempty(e036_proposal), ...
                        'E036:CommitBeforePass','Fresh common-state acceptance required');
                    assert(isequaln(history_vars_old,e036_old.history) && ...
                        isequaln(p_field_old,e036_old.lower),'E036:Preimage','Commit preimage changed');
                    % Persist a pure proposal before assignment. Native subsequent
                    % step checkpoint remains the authoritative committed state.
                    e036_path = fullfile(example_name,sprintf('e036_c%04d_s%02d_proposal.mat', ...
                        SOL_CYCL_VAR.n_cycle,i_step));
                    assert(~isfile(e036_path) && ~isfile([e036_path '.tmp']), ...
                        'E036:ExistingReceipt','Refusing to replace an acceptance receipt');
                    e036_status = 'validated_proposal_before_native_assignment';
                    save([e036_path '.tmp'],'e036_audit','e036_proposal','e036_old', ...
                        'e036_trace','e036_status','-v7.3');
                    movefile([e036_path '.tmp'],e036_path);
                    p_field_old = e036_proposal.lower;
                    history_vars_old = e036_proposal.history;
                else
""" + COMMIT + """                end
"""


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"nonunique or missing audited anchor: {old[:70]!r}")
    return text.replace(old, new, 1)


def patch_solver(text: str) -> str:
    text = replace_once(text, PRE_ITER, START_HOOK + PRE_ITER)
    text = replace_once(text, ACCEPT, AUDIT_HOOK + ACCEPT)
    text = replace_once(text, COMMIT, COMMIT_HOOK)
    failure = "            if i_stag == SOL_STAG_PAR.max_iter\n"
    record = """                if e036_enabled
                    e036_failure_path = fullfile(example_name,sprintf('e036_c%04d_s%02d_rejected.mat', ...
                        SOL_CYCL_VAR.n_cycle,i_step));
                    assert(~isfile(e036_failure_path),'E036:ExistingReceipt','Existing rejection receipt');
                    e036_status = 'rejected_no_history_commit';
                    save(e036_failure_path,'e036_audit','e036_old','e036_trace','e036_status','-v7.3');
                end
"""
    return replace_once(text, failure, failure + record)


def patch_runner(text: str) -> str:
    hook = """% Explicit policy is supplied only for the new acceptance arm.
e036_final_acceptance = struct('enabled',false);
if isfield(options,'e036_final_acceptance')
    e036_final_acceptance = options.e036_final_acceptance;
    assert(isstruct(e036_final_acceptance) && isscalar(e036_final_acceptance) && ...
        isfield(e036_final_acceptance,'enabled') && islogical(e036_final_acceptance.enabled) && ...
        isscalar(e036_final_acceptance.enabled),'E036:Policy','Invalid opt-in configuration');
    if e036_final_acceptance.enabled
        assert(isfield(e036_final_acceptance,'policy'),'E036:Policy','Missing explicit policy');
    end
end

"""
    return replace_once(text, "\nsolve_fatigue_fracture\n", "\n" + hook + "solve_fatigue_fracture\n")


def build(source_dir: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Output must be a new directory: {output}")
    # Validate everything before even creating output.
    contents = {}
    for name, expected in PINNED.items():
        raw = (source_dir / name).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError(f"Audited source identity mismatch: {name}: {actual}")
        contents[name] = raw.decode("utf-8").replace("\r\n", "\n")
    patched = {
        "solve_fatigue_fracture.m": patch_solver(contents["solve_fatigue_fracture.m"]),
        "run_SENS_hard_recovery_native_q4_capture.m": patch_runner(contents["run_SENS_hard_recovery_native_q4_capture.m"]),
    }
    output.mkdir(parents=True)
    target = output / "Scripts/fatigue_fracture"
    target.mkdir(parents=True)
    for name, text in patched.items():
        (target / name).write_text(text, encoding="utf-8")
    helpers = output / "Sources/+phase_field/+audit"
    helpers.mkdir(parents=True)
    for name in ("e036_final_candidate.m", "e036_native_candidate.m", "e036_policy.m"):
        (helpers / name).write_bytes(Path(__file__).with_name(name).read_bytes())
    receipt = {"scope": "local overlay preparation only; not applied or executed", "source_commit": "862992a60edc7f59335365beacb5c71fc8592a7a", "source_sha256": PINNED, "default": "legacy; zero extra assemblies", "files": {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob("*.m"))}}
    (output / "overlay_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audited-source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.audited_source_dir, args.output), indent=2))
