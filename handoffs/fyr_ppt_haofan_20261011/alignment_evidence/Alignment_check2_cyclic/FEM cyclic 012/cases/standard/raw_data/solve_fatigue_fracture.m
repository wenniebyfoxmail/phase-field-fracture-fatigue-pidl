% Copyright (C) 2021-2023 ETH Zurich, SIS ID and CompMech D-MAVT
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

% =========================================================================
%   COMPUTE CYCLES
% =========================================================================

%cycle loop
while SOL_CYCL_VAR.n_cycle <= (SOL_CYCL_PAR.max_cycle-1)

    % =========================================================================
    %   STEP-BY-STEP SOLUTION
    % =========================================================================
    cycle_tic = tic;
    
    %count up explicitly computed cycle
    SOL_CYCL_VAR.n_cycle = SOL_CYCL_VAR.n_cycle + 1;

    % ── Track peak ψ⁺ across steps within cycle (for Kt / field export) ──
    peak_psi_plus = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);

    % ========STEP ITERATION===================================================
    for i_step = 1:SOL_STEP_PAR.n_step
        disp('=========================================================================')
        disp([' CYCLE Nr.:', num2str(SOL_CYCL_VAR.n_cycle), ' STEP Nr.: ', num2str(i_step)]);
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
                'res_tol', SOL_PAR.tol_displ,...
                'line_search', SOL_STEP_PAR.line_search...
            );
            if isnan(res_displ) || non_conv
                phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);
                error('displacement residual is NaN or Newton-Raphson did not converge');
            end

            % =======NEWTON-RAPHSON ITERATION FOR THE PHASE FIELD EQUATION=========
            [i_res_pf_0, res_pf, p_field, ~, history_vars_new, non_conv] = phase_field.fem.solver.newton_raphson(...
                assembly_pf_fh,...
                sys,...
                p_field, p_field_old, strain_en_undgr,...
                history_vars_old,...
                sys.DOFS.active_dof_pf,...
                sys.STIFFNESS_MATRIX.i_row_pf,...
                sys.STIFFNESS_MATRIX.j_col_pf,...
                'max_iter', SOL_PAR.max_iter_pf,...
                'res_tol', SOL_PAR.tol_p_field,...
                'line_search', SOL_STEP_PAR.line_search,...
                'regularize_pf_only', strcmp(sys.diss_fct, 'PF_CZM')...
            );
            if isnan(res_pf) || non_conv
                phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);
                error('phase-field residual is NaN or Newton-Raphson did not converge');
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
                [~, ~, ~, history_vars_old] = assembly_pf_fh(...
                    sys.MESH, sys.DOFS, sys.GEOM.t,...
                    sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
                    p_field, p_field_old, strain_en_undgr,...
                    sys.stress_state.as_number,...
                    history_vars_old...
                );
                break;
            end

            % ==================CHECK FOR NON-CONVERGENCE OR NAN RESIDUAL====================
            if i_stag == SOL_STAG_PAR.max_iter
                phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);
                error('staggered loop did not converge!');
            end
        end

        % ============================STEP POST-PROCESSING=============================
        
        %convergence information
        SOL_STEP_VAR = phase_field.fem.solver.step.post_iter_update(...
            i_step, SOL_STEP_VAR,...
            sys.STIFFNESS_MATRIX, displ, sys.NODE_BOUNDARIES, sys.MESH.num_node,...
            SOL_STEP_PAR, example_name...
        );
        i_SOL_STAG_VAR = SOL_STAG_VAR(1:i_stag, :);

        indexCols = [i_step * ones(1,i_stag) ; 1:i_stag]';
        indexColumnHeader = {'Load Step', 'iter'};
        cols = [res_displ_0 * ones(i_stag,1), res_pf_0 * ones(i_stag,1),...
            i_SOL_STAG_VAR.el_en, i_SOL_STAG_VAR.fract_en, i_SOL_STAG_VAR.tot_en,...
            i_SOL_STAG_VAR.normal_res_displ, i_SOL_STAG_VAR.normal_res_pf,...
            i_SOL_STAG_VAR.normal_var_en_tot, i_SOL_STAG_VAR.normal_res,...
            i_SOL_STAG_VAR.normal_var_res...
        ];
        columnHeader = {'RES_displ(0)', 'RES_PF(0)', 'Elast_en', 'Fract_en', 'Total_en', 'RES_displ', 'RES_PF', 'Norm_EN_tot', 'Norm_RES_tot', 'Norm_var_RES'};
        logPath = [example_name filesep 'CONV_' example_name sprintf('%05d', i_step) '.log'];

        phase_field.mex.output.dat_output(indexCols, indexColumnHeader, cols, columnHeader, logPath);

        % reset SOL_STAG_VAR for the next staggered iteration
        SOL_STAG_VAR = phase_field.fem.solver.stag.vars(SOL_STAG_PAR);

        % ── Update peak ψ⁺ (running max over steps within cycle) ────────
        peak_psi_plus = max(peak_psi_plus, strain_en_undgr);

        % ── Peak-load VTK at cycle 1 for SIF / elastic validation ───────
        %   Saves u, epsilon, sigma at the final loading step (before unload)
        %   of the first cycle. Only runs once; no effect on other cycles.
        if SOL_CYCL_VAR.n_cycle == 1 && i_step == (SOL_STEP_PAR.n_step - 1)
            [~, stress_L2] = phase_field.mex.fem.processing.L2_PROJECTION(...
                sys.MESH, sys.DOFS, sys.GEOM.t, sys.num_materials, ...
                sys.QUADRATURE, sys.CC, p_field, 4, history_vars_old);
            stress_L2_matrix = sparse(sys.STIFFNESS_MATRIX.i_row_eps, ...
                                      sys.STIFFNESS_MATRIX.j_col_eps, stress_L2);
            phase_field.output.paraview_step(...
                [example_name filesep 'peak_load_c1.vtk'], ...
                sys.STIFFNESS_MATRIX, sys.MESH, ...
                {'d','u'}, ...
                {p_field, reshape(displ, [sys.MESH.num_node, 2])}, ...
                {'epsilon','sigma'}, ...
                {reshape(sys.STIFFNESS_MATRIX.eps * displ, [sys.MESH.num_node, 3]), ...
                 reshape(stress_L2_matrix * displ, [sys.MESH.num_node, 3])} ...
            );
            fprintf('[SIF] Saved peak-load VTK: %s/peak_load_c1.vtk\n', example_name);
        end

    end
    
    % =========================================================================
    %   POST-PROCESSNG (CYCLE-WISE)
    % =========================================================================

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

    %display elapsed time for the cycle
    disp(['cycle computation time: ' num2str(toc(cycle_tic)) 's'])

    %output cputime for the cycle
    phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle 1], {'cycle' 'type'}, [cputime toc(cycle_tic)], {'totaltime' 'cycletime'}, [example_name filesep 'cputime.dat']);

    % ============================PSI-PLUS FIELD EXPORT========================
    % Save per-element peak ψ⁺, α, f(α) + compute Kt/f_mean/alpha_mean.
    % Output: <example_name>/psi_fields/cycle_NNNN.mat  (per-element arrays)
    %         <example_name>/extra_scalars.dat           (per-cycle summary)
    psi_field_dir = [example_name filesep 'psi_fields'];
    if ~exist(psi_field_dir, 'dir'), mkdir(psi_field_dir); end

    % Per-element means over Gauss points (n_elem × 1)
    psi_elem  = mean(peak_psi_plus, 2);
    alpha_elem = mean(history_vars_old(:,:,2), 2);
    f_alpha_elem = mean(history_vars_old(:,:,4), 2);
    % d_elem: per-element damage averaged from nodal p_field via mesh connectivity
    % (matches `augment_snapshots_with_d.m` pattern; added 2026-05-13 for PIDL
    % α-direct supervision per Mac mirror commit f7ba430).
    d_elem = mean(p_field(sys.MESH.elem(:, 1:sys.MESH.nel)), 2);

    % Save per-cycle field snapshot (.mat, loadable by Python via scipy.io)
    cycle_file = [psi_field_dir filesep sprintf('cycle_%04d.mat', SOL_CYCL_VAR.n_cycle)];
    save(cycle_file, 'psi_elem', 'alpha_elem', 'f_alpha_elem', 'd_elem', '-v7');

    % Scalar reductions
    psi_peak = max(psi_elem);
    alpha_bar_mean = mean(alpha_elem);
    f_mean = mean(f_alpha_elem);

    % Kt: sqrt(psi_tip / psi_nominal)
    %   psi_tip     = mean of top-10 highest-ψ⁺ elements
    %   psi_nominal = mean over far-field elements (|y_centroid|>0.3 AND x_centroid>-0.3)
    [psi_sorted, ~] = sort(psi_elem, 'descend');
    psi_tip = mean(psi_sorted(1:min(10, numel(psi_sorted))));

    if ~exist('centroids_x', 'var')   % compute once, reuse across cycles
        centroids_x = zeros(sys.MESH.num_elem, 1);
        centroids_y = zeros(sys.MESH.num_elem, 1);
        for e_idx = 1:sys.MESH.num_elem
            el_nd = sys.MESH.elem(e_idx, 1:sys.MESH.nel);
            centroids_x(e_idx) = mean(sys.MESH.node(el_nd, 1));
            centroids_y(e_idx) = mean(sys.MESH.node(el_nd, 2));
        end
    end
    far_mask = abs(centroids_y) > 0.3 & centroids_x > -0.3;
    if any(far_mask)
        psi_nominal = mean(psi_elem(far_mask));
    else
        psi_nominal = mean(psi_elem);  % fallback for plate.m geometry
    end
    Kt_val = sqrt(max(psi_tip, 0) / max(psi_nominal, eps));

    % Append to summary file
    extra_file = [example_name filesep 'extra_scalars.dat'];
    extra_cols = [SOL_CYCL_VAR.n_cycle, Kt_val, f_mean, alpha_bar_mean, psi_peak, psi_tip, psi_nominal];
    extra_hdr  = {'N', 'Kt', 'f_mean', 'alpha_bar_mean', 'psi_peak', 'psi_tip', 'psi_nominal'};
    phase_field.mex.output.dat_output(SOL_CYCL_VAR.n_cycle, {'N'}, extra_cols(2:end), extra_hdr(2:end), extra_file);

    % ============================PENETRATION CHECK============================
    % Stop when crack reaches any outer boundary of the specimen.
    % Strategy: flag all perimeter nodes, then exclude any that were
    % prescribed as d=1 from the start (non_hom_dirichlet_bc_pf) so that
    % a phase-field notch BC on the entry edge does not trigger a false positive.
    % Works for any crack direction: SENT (right), SENS 45-deg (bottom/right),
    % TPB (top), CT (right), etc.
    x_coords = sys.MESH.node(:,1);
    y_coords = sys.MESH.node(:,2);
    bc_tol = 1e-10;
    boundary_mask = abs(x_coords - max(x_coords)) < bc_tol | ...
                    abs(x_coords - min(x_coords)) < bc_tol | ...
                    abs(y_coords - max(y_coords)) < bc_tol | ...
                    abs(y_coords - min(y_coords)) < bc_tol;
    boundary_mask(sys.DOFS.non_hom_dirichlet_bc_pf) = false;  % exclude initial d=1 BCs
    if exist('initial_precrack_exclusion_nodes', 'var')
        boundary_mask(initial_precrack_exclusion_nodes) = false;
    end
    penetration_trigger = any(p_field(boundary_mask) >= 0.95);
    if penetration_trigger
        disp(['[PENETRATION] Crack reached specimen boundary at cycle ' num2str(SOL_CYCL_VAR.n_cycle) '. Stopping after this cycle.']);
    end

    % ============================PARAVIEW OUTPUT=============================
    % Three conditions trigger VTK output (any is sufficient):
    %   1. crack growth >= da_paraview (original behaviour)
    %   2. periodic: every vtk_freq cycles (set in INPUT file; default Inf)
    %   3. penetration: always write final state
    if ~exist('vtk_freq', 'var'), vtk_freq = Inf; end
    crack_growth_trigger = (CRACK_VAR.crack_regularized(end,3) - SOL_CYCL_VAR.da_paraview_last) >= SOL_CYCL_PAR.da_paraview;
    periodic_trigger     = (mod(SOL_CYCL_VAR.n_cycle, vtk_freq) == 0);
    if crack_growth_trigger || periodic_trigger || penetration_trigger

        %prepare the L2-projection for the postprocessing
        [history_vars_L2, stress_L2] = phase_field.mex.fem.processing.L2_PROJECTION(sys.MESH, sys.DOFS, sys.GEOM.t, sys.num_materials, sys.QUADRATURE, sys.CC, p_field, 4, history_vars_old);

        %write paraview output file
        stress_L2_matrix = sparse(sys.STIFFNESS_MATRIX.i_row_eps, sys.STIFFNESS_MATRIX.j_col_eps, stress_L2);
        phase_field.output.paraview_step(...
            [example_name filesep 'fields_' sprintf('%06d_%03d', SOL_CYCL_VAR.n_cycle, i_step) '.vtk'],...
            sys.STIFFNESS_MATRIX, sys.MESH,...
            {'d', 'u'},...
            {p_field, reshape(displ, [sys.MESH.num_node, 2])},...
            {'epsilon', 'sigma', 'H', 'alpha', 'Dalpha', 'f(alpha)'},...
            {reshape(sys.STIFFNESS_MATRIX.eps * displ, [sys.MESH.num_node, 3]), reshape(stress_L2_matrix * displ, [sys.MESH.num_node, 3]), history_vars_L2(:,1), history_vars_L2(:,2), history_vars_L2(:,3), history_vars_L2(:,4)}...
            );

        %save last crack increment of output (only update when crack-growth triggered)
        if crack_growth_trigger
            SOL_CYCL_VAR.da_paraview_last = CRACK_VAR.crack_regularized(end,3);
        end
    end

    % =========================================================================
    %   CHECKPOINT SAVE
    % =========================================================================
    if ~exist('checkpoint_freq', 'var'), checkpoint_freq = Inf; end
    if mod(SOL_CYCL_VAR.n_cycle, checkpoint_freq) == 0
        ckpt_dir  = example_name;
        ckpt_tmp  = [ckpt_dir filesep 'checkpoint_tmp.mat'];
        ckpt_file = [ckpt_dir filesep 'checkpoint.mat'];
        save(ckpt_tmp, 'displ', 'p_field', 'p_field_old', 'history_vars_old', ...
             'SOL_CYCL_VAR', 'CRACK_VAR', 'SOL_JUMP_VAR');
        movefile(ckpt_tmp, ckpt_file);   % atomic replace — avoids corrupt file on crash
        disp(['[CHECKPOINT] Saved at cycle ' num2str(SOL_CYCL_VAR.n_cycle) '.']);
    end

    % Stop loop after penetration: force checkpoint, then break
    if penetration_trigger
        ckpt_dir  = example_name;
        ckpt_tmp  = [ckpt_dir filesep 'checkpoint_tmp.mat'];
        ckpt_file = [ckpt_dir filesep 'checkpoint.mat'];
        save(ckpt_tmp, 'displ', 'p_field', 'p_field_old', 'history_vars_old', ...
             'SOL_CYCL_VAR', 'CRACK_VAR', 'SOL_JUMP_VAR');
        movefile(ckpt_tmp, ckpt_file);
        disp(['[CHECKPOINT] Final state saved at cycle ' num2str(SOL_CYCL_VAR.n_cycle) ' (penetration).']);
        break;
    end

    % =========================================================================
    %   CYCLE-JUMP
    % =========================================================================
    if SOL_JUMP_PAR.cycl_jump
        accelerate_fatigue_fracture;
    end

end
