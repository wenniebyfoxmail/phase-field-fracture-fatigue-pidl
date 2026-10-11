% Copyright (C) 2021-2022 ETH Zurich, SIS ID and CompMech D-MAVT
%
% Licensed under the Apache License, Version 2.0 (the "License");
% you may not use this file except in compliance with the License.
% You may obtain a copy of the License at
%
%    http://www.apache.org/licenses/LICENSE-2.0
%
% Unless required by applicable law or agreed to in writing, software
% distributed under the License is distributed on an "AS IS" BASIS,
% WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
% See the License for the specific language governing permissions and
% limitations under the License.

% this script implements the adaptive acceleration scheme proposed in
% Heinzmann et al. (2024): An adaptive acceleration scheme for phase-field fatigue computations
% https://doi.org/10.48550/arXiv.2404.07003

disp('=========================================================================')
disp(['JUMPING ', num2str(Dn), ' CYCLES']);
disp(['     stage               ' num2str(cycl_jump_stage)]);
disp(['     Dn                = ' num2str(Dn)]);
disp(['     DLambda_jump      = ' num2str(DLambda_jump)]);
disp(['     DLambda_predicted = ' num2str(DLambda_predicted)]);

%initialize flag for convergence of trial-cycle
accept_jump = true;
cyclejump_criterion_satisfied = true;

%save current state as restoring point
SOL_CYCL_VAR.RESTORE.KK               = sys.STIFFNESS_MATRIX.KK;
SOL_CYCL_VAR.RESTORE.displ            = displ;
SOL_CYCL_VAR.RESTORE.p_field          = p_field;
SOL_CYCL_VAR.RESTORE.p_field_old      = p_field_old;
SOL_CYCL_VAR.RESTORE.strain_en_undgr  = strain_en_undgr;
SOL_CYCL_VAR.RESTORE.history_vars_old = history_vars_old;

%extrapolate accumulating variables for actual cylcle jump (for this model: fatigue history variable)
history_vars_old(:,:,2) = phase_field.fem.solver.cycl_jump.extrapolate(SOL_JUMP_PAR,SOL_JUMP_VAR.HISTORY,Dn);

%extrapolate also for jump-following cycles to evaluate errors post-jump (optional)
if SOL_JUMP_PAR.prediction_error_estimation
    for Dn_extra = 1:(SOL_JUMP_PAR.n_stencil-1)
        SOL_JUMP_VAR.ERROR_PREDICTIONS(:,:,Dn_extra) = phase_field.fem.solver.cycl_jump.extrapolate(SOL_JUMP_PAR,SOL_JUMP_VAR.HISTORY,Dn+Dn_extra);
    end
end

% =========================================================================
%   TRIAL-CYCLE
% =========================================================================
for i_step = 1:SOL_STEP_PAR.n_step
    disp('=========================================================================')
    disp([' TRIAL-CYCLE Nr.:', num2str(SOL_CYCL_VAR.n_cycle+Dn), ' STEP Nr.: ', num2str(i_step)]);
    disp('=========================================================================')
    
    [displ, res_displ, D_RHS_tract] = phase_field.fem.solver.step.pre_iter_update(i_step, sys, displ, SOL_STEP_PAR);
    res_displ_0 = norm(res_displ(sys.DOFS.active_dof,1));
    
    % ========STAGGERED ITERATION==============================================
    for i_stag = 1:SOL_STAG_PAR.max_iter
        disp([' STAG ITER Nr.: ', num2str(i_stag), '---------------------------']);
        
        % ======NEWTON-RAPHSON ITERATION FOR THE EQUILIBRIUM EQUATION==========
        [res_displ_0, res_displ, displ, strain_en_undgr, ~, non_conv] = phase_field.fem.solver.newton_raphson(...
            assembly_equilibrium_fh,...
            sys,...
            displ, 0.0, p_field,...
            0.0,...
            sys.DOFS.active_dof,...
            sys.STIFFNESS_MATRIX.i_row,...
            sys.STIFFNESS_MATRIX.j_col,...
            'D_RHS_tract', D_RHS_tract,...
            'max_iter', SOL_PAR.max_iter_displ,...
            'res_tol', SOL_PAR.tol_displ...
        );
        if isnan(res_displ) || non_conv
            accept_jump = false;
            warning('displacement residual is NaN or Newton-Raphson did not converge');
            break;
        end

        % =======NEWTON-RAPHSON ITERATION FOR THE PHASE FIELD EQUATION=========
        [i_res_pf_0, res_pf, p_field, ~, history_vars_trial, non_conv] = phase_field.fem.solver.newton_raphson(...
            assembly_pf_fh,...
            sys,...
            p_field, p_field_old, strain_en_undgr,...
            history_vars_old,...
            sys.DOFS.active_dof_pf,...
            sys.STIFFNESS_MATRIX.i_row_pf,...
            sys.STIFFNESS_MATRIX.j_col_pf,...
            'max_iter', SOL_PAR.max_iter_pf,...
            'res_tol', SOL_PAR.tol_p_field...
        );
        if isnan(res_pf) || non_conv
            accept_jump = false;
            warning('phase-field residual is NaN or Newton-Raphson did not converge');
            break;
        end

        if i_stag == 1
            res_pf_0 = i_res_pf_0;
        end
        
        % ==================CHECK FOR STAGGERED CONVERGENCE====================
        [SOL_STAG_VAR, strain_en_undgr, stag_converged, sys.STIFFNESS_MATRIX.KK] = phase_field.fem.solver.stag.post_iter_update(...
            assembly_equilibrium_fh, i_stag, SOL_STAG_VAR,...
            sys,...
            D_RHS_tract,...
            p_field, displ,...
            res_pf_0, res_pf, res_displ_0,...
            SOL_STAG_PAR...
        );
        if stag_converged
            % update the history variables
            p_field_old = p_field;
            [~, ~, ~, history_vars_trial] = assembly_pf_fh(...
                sys.MESH, sys.DOFS, sys.GEOM.t,...
                sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
                p_field, p_field_old, strain_en_undgr,...
                sys.stress_state.as_number,...
                history_vars_old...
            );
            %do not update the increment of the fatigue history variable
            history_vars_old(:,:,1) = history_vars_trial(:,:,1);
            history_vars_old(:,:,3) = history_vars_trial(:,:,3);
            history_vars_old(:,:,4) = history_vars_trial(:,:,4);
            break;
        end
        
        % ==================EVALUATE NON-CONVERGENCE OR NAN RESIDUAL====================
        if i_stag == SOL_STAG_PAR.max_iter
            accept_jump = false;
            warning('staggered loop did not converge!');
            break;
        end
    end
    
    % ============================STEP POST-PROCESSING=============================
    if accept_jump
        %convergence information
        SOL_STEP_VAR = phase_field.fem.solver.step.post_iter_update(i_step, SOL_STEP_VAR,sys.STIFFNESS_MATRIX,displ,sys.NODE_BOUNDARIES,sys.MESH.num_node,SOL_STEP_PAR,example_name);
        i_SOL_STAG_VAR = SOL_STAG_VAR(1:i_stag, :);
        cols = [res_displ_0 * ones(i_stag,1), res_pf_0 * ones(i_stag,1),...
            i_SOL_STAG_VAR.el_en, i_SOL_STAG_VAR.fract_en, i_SOL_STAG_VAR.tot_en,...
            i_SOL_STAG_VAR.normal_res_displ, i_SOL_STAG_VAR.normal_res_pf,...
            i_SOL_STAG_VAR.normal_var_en_tot, i_SOL_STAG_VAR.normal_res,...
            i_SOL_STAG_VAR.normal_var_res...
            ];
        
        phase_field.mex.output.dat_output(...
            [i_step * ones(1,i_stag) ; 1:i_stag]', {'Load Step', 'iter'}, ...
            cols, {'RES_displ(0)', 'RES_PF(0)', 'Elast_en', 'Fract_en', 'Total_en', 'RES_displ', 'RES_PF', 'Norm_EN_tot', 'Norm_RES_tot', 'Norm_var_RES'}, ...
            [example_name filesep 'convergence_' sprintf('%05d', i_step) '.log']);
        
        % reset SOL_STAG_VAR for the next staggered iteration
        SOL_STAG_VAR = phase_field.fem.solver.stag.vars(SOL_STAG_PAR);

    else
        %end trial-cycle
        break;
    end
    
end

% =========================================================================
%   CHECK CYCLE-JUMP CRITERION
% =========================================================================

%check if increments of cycle jump are withing bounds (only if computations converged)
if strcmp(SOL_JUMP_PAR.jumpmethod,'adaptive') && accept_jump
    
    %check for the trial change of Lambda
    Dmaxfat_trial = max(history_vars_old(:,:,2),[],'all')-SOL_CYCL_VAR.MONITOR.fat(end,3);
    Dmaxd_trial = max(p_field(:))-SOL_CYCL_VAR.MONITOR.d(end,3);
    [CRACK_VAR_TRIAL] = phase_field.fem.crack.crack_regularized(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name, 'output', false);
    Da_trial = CRACK_VAR_TRIAL.crack_regularized(end,3)-CRACK_VAR.crack_regularized(end,3);
    switch cycl_jump_stage
        case 1
            DLambda_trial = Dmaxfat_trial;
        case 2
            DLambda_trial = Dmaxd_trial;
        case 3
            DLambda_trial = Da_trial;
    end
    
    %do not accept cycle jump after all if increment was too large
    if DLambda_trial > 1.5*DLambda_jump
        warning(['the trial-cycle gave an increment of ' num2str(DLambda_trial) ' which is > 150% of ' num2str(DLambda_jump)])
        accept_jump = false;
        cyclejump_criterion_satisfied = false;
    else
        disp(['the trial-cycle gave an increment of ' num2str(DLambda_trial) ' which is <= 150% of ' num2str(DLambda_jump)])
    end
end


% =========================================================================
%   POSTPROCESS TRIAL-CYCLE
% =========================================================================

%only postprocess if cycle jump is accepted, otherwise restore old state
if accept_jump
    disp('extrapolated solution did converge during trial-cycle (and increment within acceptable bounds), accepting cycle jump!')
    
    %accept extrapolated solution
    SOL_JUMP_VAR.jumps(end+1,:) = [SOL_CYCL_VAR.n_cycle Dn SOL_CYCL_VAR.n_cycle+Dn];
    SOL_CYCL_VAR.n_cycle = SOL_CYCL_VAR.n_cycle + Dn;
    
    %count up explicitly computed cycles for statistics
    SOL_JUMP_VAR.n_resolved = SOL_JUMP_VAR.n_resolved + 1;
    phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle], {'n'}, [SOL_JUMP_VAR.n_resolved], {'n_resolved'}, [example_name filesep 'explicitcycles.dat']);
    
    % ============================CRACK PROCESSING=============================
    [CRACK_VAR] = phase_field.fem.crack.crack_regularized(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name);
    
    %crack growth rate evaluation for specific specimens
    if ismember(CRACK_PAR.specimen, {'ct', 'tpb', 'sent', 'dent', 'cct'})
        %crack tip monitoring
        [CRACK_VAR] = phase_field.fem.crack.crack_discretized(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name);
        [CRACK_VAR] = phase_field.fem.crack.crack_interpolated(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name);

        %crack growth rate and stress intensity factor amplitude computation to prepare Paris plot
        [CRACK_VAR] = phase_field.fem.crack.fatigue_crack_growth(sys, CRACK_PAR, CRACK_VAR, SOL_STEP_PAR, example_name);
    elseif strcmp(CRACK_PAR.specimen, 'bar') && any(p_field>CRACK_PAR.crack_thres)
        %fatigue life output for Woehler curve
        phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);
        
        %output cputime for the cycle
        phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle 1], {'cycle' 'type'}, [cputime toc(cycle_tic)], {'totaltime' 'cycletime'}, [example_name filesep 'cputime.dat']);
        error('bar specimen has cracked, stopping computations')
    end
    
    % ============================SYSTEM MONITORING=============================
    %norm-based monitoring of the system
    [SOL_CYCL_VAR] = phase_field.fem.solver.cycl.monitor(SOL_CYCL_VAR,displ,p_field,history_vars_old(:,:,2),example_name);

    %check for system change during cycle jump
    Dfat_inf = SOL_CYCL_VAR.MONITOR.fat(end,3)-SOL_CYCL_VAR.MONITOR.fat(end-1,3);
    Dd_inf = SOL_CYCL_VAR.MONITOR.d(end,3)-SOL_CYCL_VAR.MONITOR.d(end-1,3);
    Da_ell = CRACK_VAR.crack_regularized(end,3)-CRACK_VAR.crack_regularized(end-1,3);

    %output information about the cycle jump
    data = [SOL_JUMP_VAR.jumps(end,:) cycl_jump_stage];
    phase_field.mex.output.dat_output(...
        [SOL_JUMP_VAR.jumps(end,:) cycl_jump_stage], {'n' 'Dn' 'n+Dn' 'stage'}, ...
        [DLambda_jump DLambda_predicted Dfat_inf Dd_inf Da_ell], {'DLambda_jump' 'DLambda_predicted' 'D||fat||_inf' 'D||d||_inf' 'Da_ell'}, ...
        [example_name filesep 'cyclejump.dat']);
    
    % ============================PARAVIEW OUTPUT=============================
    %paraview output either step-by-step (da_paraview=0 as default) or once a certain crack growth has been reached
    if (CRACK_VAR.crack_regularized(end,3)-SOL_CYCL_VAR.da_paraview_last)>=SOL_CYCL_PAR.da_paraview
        %prepare the L2-projection for the postprocessing
        [history_vars_L2, stress_L2] = phase_field.mex.fem.processing.L2_PROJECTION(sys.MESH, sys.DOFS, sys.GEOM.t, sys.num_materials, sys.QUADRATURE, sys.CC, p_field, 4, history_vars_old);
        
        %write paraview output file
        stress_L2_matrix = sparse(sys.STIFFNESS_MATRIX.i_row_eps, sys.STIFFNESS_MATRIX.j_col_eps, stress_L2);
        phase_field.output.paraview_step(...
            [example_name filesep 'fields_' sprintf('%06d_%03d', SOL_CYCL_VAR.n_cycle, i_step) '.vtk'],...
            sys.STIFFNESS_MATRIX, sys.MESH,...
            {'d', 'u'},...
            {p_field, reshape(displ, [sys.MESH.num_node, 2])},...
            {'sigma', 'epsilon', 'H', 'alpha', 'Dalpha', 'f(alpha)'},...
            {reshape(sys.STIFFNESS_MATRIX.eps * displ, [sys.MESH.num_node, 3]), reshape(stress_L2_matrix * displ, [sys.MESH.num_node, 3]), history_vars_L2(:,1), history_vars_L2(:,2), history_vars_L2(:,3), history_vars_L2(:,4)}...
            );
        
        %save last crack increment of output
        SOL_CYCL_VAR.da_paraview_last = CRACK_VAR.crack_regularized(end,3);
    end
    
    % =========================================================================
    %save last n_stencil values of the state variables and their cycle count to act as basis for the extrapolation
    for n_state=1:SOL_JUMP_PAR.n_stencil-1
        SOL_JUMP_VAR.HISTORY.n(1,n_state) = SOL_JUMP_VAR.HISTORY.n(1,n_state+1);
        SOL_JUMP_VAR.HISTORY.fat(:,:,n_state) = SOL_JUMP_VAR.HISTORY.fat(:,:,n_state+1);
    end
    SOL_JUMP_VAR.HISTORY.n(1,end) = SOL_CYCL_VAR.n_cycle;
    SOL_JUMP_VAR.HISTORY.fat(:,:,end) = history_vars_old(:,:,2);
    
else
    warning('extrapolated solution did not converge during trial-cycle (or increment not within acceptable bounds), restoring old state')
    
    %restore old state
    sys.STIFFNESS_MATRIX.KK = SOL_CYCL_VAR.RESTORE.KK;
    displ                   = SOL_CYCL_VAR.RESTORE.displ;
    p_field                 = SOL_CYCL_VAR.RESTORE.p_field;
    p_field_old             = SOL_CYCL_VAR.RESTORE.p_field_old;
    strain_en_undgr         = SOL_CYCL_VAR.RESTORE.strain_en_undgr;
    history_vars_old        = SOL_CYCL_VAR.RESTORE.history_vars_old;
    
end %if accept_jump
