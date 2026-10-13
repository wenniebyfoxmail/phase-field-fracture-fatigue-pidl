#!/usr/bin/env python3
"""Build frozen-baseline, joint fixed-point sufficient-decrease backtracking."""
import argparse,json,hashlib
from pathlib import Path
from prepare_s04_e011_endpoint_tight import build as tight_build


def build(driver,solver,hashes):
    s=tight_build(driver,solver,hashes).replace('run_s04_e011_endpoint_tight','run_s04_e011_endpoint_backtrack')
    s=s.replace('predecessor.cycle==83','predecessor.cycle==options.cycle').replace('b.converged_peak_solution.cycle==83','b.converged_peak_solution.cycle==options.cycle')
    s=s.replace('b.converged_peak_solution.staggered_iteration==20','b.converged_peak_solution.staggered_iteration==options.expected_iterations')
    s=s.replace('SOL_CYCL_VAR.n_cycle=83;','SOL_CYCL_VAR.n_cycle=options.cycle;').replace("'physical_cycle',83","'physical_cycle',options.cycle")
    s=s.replace('control_pass=false;',"control_pass=false; descent_stalled=false; current_metrics=baseline_metrics; trial_trace=struct('extra',{},'lambda',{},'merit',{},'accepted',{});")
    s=s.replace('for i_stag=baseline_iteration+1:baseline_iteration+max_extra',"for i_stag=baseline_iteration+1:baseline_iteration+max_extra\ncurrent_KK=sys.STIFFNESS_MATRIX.KK;")
    anchor='    extra=i_stag-baseline_iteration;'
    insertion=r'''
    extra=i_stag-baseline_iteration;
    full_candidate=candidate; full_oracle=candidate_oracle;
    if options.cycle==83 && extra==1
        assert(strcmpi(phase_field.audit.sha256_file(options.direction_reference),options.direction_reference_sha256));
        z=load(options.direction_reference,'candidate','candidate_oracle');
        assert(max(abs(z.candidate.displ-full_candidate.displ))<=1e-10 && max(abs(z.candidate.p_field-full_candidate.p_field))<=1e-10,'First tight direction mismatch');
        assert(max(abs(z.candidate_oracle.R_u_free-full_oracle.R_u_free))<=1e-10 && max(abs(z.candidate_oracle.R_d_free-full_oracle.R_d_free))<=1e-10,'Direction residual mismatch');
    end
    found=false;
    for trial_index=0:6
        lambda=2^(-trial_index);
        trial=struct('displ',last_completed.displ+lambda*(full_candidate.displ-last_completed.displ), ...
            'p_field',last_completed.p_field+lambda*(full_candidate.p_field-last_completed.p_field));
        prescribed=oracle.prescribed_dof_u;
        assert(max(abs(trial.displ(prescribed)-baseline_state.displ(prescribed)))<=1e-12,'Peak BC changed');
        assert(all(trial.p_field>=frozen_damage-1e-12) && all(trial.p_field<=1+1e-12));
        [trial_K,~,trial_raw,~]=assembly_equilibrium_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
            trial.displ,0.0,trial.p_field,sys.stress_state.as_number,0.0);
        trial.strain_en_undgr=trial_raw;
        trial_oracle=phase_field.audit.assemble_residual_oracle(sys,assembly_equilibrium_fh,assembly_pf_fh,trial,frozen,D_RHS_tract);
        [trial_metrics,trial_active]=endpoint_monitor(sys,trial,trial_oracle,frozen,4e-6);
        accepted=trial_metrics.converged || trial_metrics.projected_stop_sum<=(1-1e-4*lambda)*current_metrics.projected_stop_sum;
        trial_trace(end+1)=struct('extra',extra,'lambda',lambda,'merit',trial_metrics.projected_stop_sum,'accepted',accepted);
        save(fullfile(work_dir,sprintf('trial_%02d_%02d.mat',extra,trial_index+1)), ...
            'trial','trial_oracle','trial_metrics','trial_active','lambda','accepted','frozen','-v7.3');
        if accepted
            candidate=trial;candidate_oracle=trial_oracle;metrics=trial_metrics;active_gp=trial_active;
            displ=trial.displ;p_field=trial.p_field;strain_en_undgr=trial_raw;
            sys.STIFFNESS_MATRIX.KK=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,trial_K);
            current_metrics=metrics;found=true;break;
        end
    end
    save(fullfile(work_dir,'trial_trace.mat'),'trial_trace','-v7');
    if ~found
        displ=last_completed.displ;p_field=last_completed.p_field;strain_en_undgr=last_completed.strain_en_undgr;
        sys.STIFFNESS_MATRIX.KK=current_KK;descent_stalled=true;break;
    end
'''
    if s.count(anchor)!=1:raise ValueError('extra source drift')
    s=s.replace(anchor,insertion)
    s=s.replace("if control_pass,status='PASS_PROJECTED_ABSOLUTE_SCREEN';else,status='EXTRA_BUDGET_EXHAUSTED';end", "if control_pass,status='PASS_PROJECTED_ABSOLUTE_SCREEN';elseif descent_stalled,status='NO_ADMISSIBLE_DESCENT_WITHIN_TRIAL_BUDGET';else,status='EXTRA_BUDGET_EXHAUSTED';end\nmetrics=current_metrics;")
    s=s.replace("'baseline_metrics',baseline_metrics,'final_metrics',metrics,", "'baseline_metrics',baseline_metrics,'final_metrics',metrics,'physical_cycle',options.cycle,'trial_count',numel(trial_trace),")
    s=s.replace('E011_TIGHT','E011_BACKTRACK').replace('Frozen Q4 reference must be iter20','Frozen Q4 reference iteration mismatch')
    s=s.replace("c83s3 -> c83s4 U=%.12g", "cycle=%d s3 -> s4 U=%.12g").replace("sum(SOL_STEP_PAR.uy_increment(1:4)));", "options.cycle,sum(SOL_STEP_PAR.uy_increment(1:4)));")
    s=s.replace('s04e011-c83-single-step-baseline-v1','s04e011-single-step-baseline-v2').replace('fixed-s3-history c83s4 solver-control sensitivity; not a teacher certificate','fixed-s3-history same-cycle peak joint backtracking sensitivity; not a teacher certificate')
    s=s.replace("    end\n    found=false;","        fprintf('[E011_DIRECTION_REFERENCE_PASS] cycle=83 first tight candidate\\n');\n    end\n    found=false;")
    return s


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    paths=['Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m','Scripts/fatigue_fracture/solve_fatigue_fracture.m','Scripts/fatigue_fracture/init_fatigue_fracture.m','Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m']
    hashes={p:hashlib.sha256((a.source_root/p).read_bytes()).hexdigest() for p in paths};s=build((a.source_root/paths[0]).read_text(),(a.source_root/paths[1]).read_text(),hashes)
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'run_s04_e011_endpoint_backtrack.m').write_text(s);(a.output/'source_lock.json').write_text(json.dumps(hashes,indent=2)+'\n')
if __name__=='__main__':main()
