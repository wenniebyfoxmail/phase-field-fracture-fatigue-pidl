function [res_0, res, field_vars, coupling_vars_out, history_vars_new, non_conv] = newton_raphson_f1b(...
    assembly_fh,...
    sys,...
    field_vars,...
    field_vars_old,...
    coupling_vars_in,...
    history_vars_old,...
    active_dof,...
    i_row,...
    j_col,...
    args...
)
%NEWTON_RAPHSON Newton-Raphson iterative solver of the phase field equation
%  ...

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

arguments
    assembly_fh (1, 1) function_handle
    sys (1, 1) handle
    field_vars (:, :) double
    field_vars_old (:, :) double
    coupling_vars_in (:, :) double
    history_vars_old (:, :, :) double
    active_dof (:, :) double
    i_row (:, 1) double
    j_col (:, 1) double
    args.max_iter (1, 1) double {mustBeInteger, mustBePositive} = 500
    args.min_iter (1, 1) double {mustBeInteger, mustBePositive} = 1
    args.res_tol (1, 1) double {mustBePositive} = 1e-6
    args.D_RHS_tract (:, 1) double = 0.0
    args.line_search (1,1) logical = false
    args.line_search_maxiter (1,1) = 20
    args.debug_name (1,1) string = ""
    args.regularize_pf_only (1,1) logical = false
    args.tangent_scale (1,1) double {mustBePositive} = 1.0
    % Wu PF-CZM non-PD-local mitigation (Wu/Huang/Nguyen 2019 CMAME §3.2):
    %   K_dd at d=0 is locally indefinite (alpha''=-2, dominant negative N·N^T).
    %   Vanilla Newton overshoots → NaN. Damping caps step + backtracks on residual.
    args.pf_czm_damping (1,1) logical = false
    args.pf_czm_dd_cap (1,1) double {mustBePositive} = 0.05
    args.pf_czm_max_backtrack (1,1) double {mustBeInteger, mustBeNonnegative} = 10
    args.pf_czm_backtrack_factor (1,1) double {mustBePositive} = 0.5
end

non_conv = false;

%iterative solution process
for n_iter=1:args.max_iter

    %call assembly routine
    [K_vect, res_field_vars, coupling_vars_out, history_vars_new] = assembly_fh(...
        sys.MESH, sys.DOFS, sys.GEOM.t,...
        sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
        field_vars, field_vars_old, coupling_vars_in,...
        sys.stress_state.as_number,...
        history_vars_old...
    );

    %assemble sparse matrix
    KK = sparse(i_row, j_col, K_vect);

    %subtract external RHS vector if existent
    if any(args.D_RHS_tract ~= 0.0)
        res_field_vars = res_field_vars - args.D_RHS_tract;
    end
    
    % diagnose
    KKa = KK(active_dof, active_dof);
    rhs = -res_field_vars(active_dof, 1);

    if args.debug_name ~= ""
        fprintf('--- entering %s Newton ---\n', args.debug_name);
        dKK = full(diag(KKa));
        fprintf('min(diag(KKa)) = %.3e\n', min(dKK));
        fprintf('max(diag(KKa)) = %.3e\n', max(dKK));
        fprintf('any(diag<=0)   = %d\n', full(any(dKK <= 0)));
        fprintf('condest(KKa)   = %.3e\n', condest(KKa));
        fprintf('nnz(isnan(KKa)) = %d\n', nnz(isnan(KKa)));
        fprintf('nnz(isinf(KKa)) = %d\n', nnz(isinf(KKa)));
    end
    
    
    if args.regularize_pf_only
    KKa = 0.5 * (KKa + KKa.');
    dKK = full(diag(KKa));
    shift_floor = 1e-8 * args.tangent_scale;
    shift_seed = 1e-12 * args.tangent_scale;
    shift = max(0, -min(dKK) + shift_floor);

    ok = false;
    for itry = 1:8
        Ktest = KKa + shift * speye(size(KKa,1));
        Dfield_vars = cholmod2(Ktest, rhs);

        if all(isfinite(Dfield_vars))
            fprintf('PF shift used = %.3e\n', shift);
            ok = true;
            break;
        end

        shift = max(shift_floor, 10 * max(shift, shift_seed));
    end

    if ~ok
        error('PF Newton failed even after diagonal regularization.');
    end
else
    Dfield_vars = cholmod2(KKa, rhs);
    end
    
    %solve the system equation
    %Dfield_vars = cholmod2(KK(active_dof, active_dof), -res_field_vars(active_dof, 1));

    if args.pf_czm_damping
        % Wu PF-CZM non-PD-local mitigation per Wu/Huang/Nguyen 2019 CMAME §3.2:
        % (1) cap step magnitude to delta_d_cap, then
        % (2) backtrack (factor 0.5) until residual stops increasing.
        res_baseline = norm(res_field_vars(active_dof, 1));
        step = Dfield_vars;
        step_max = max(abs(step));
        if isfinite(step_max) && step_max > args.pf_czm_dd_cap
            step = step * (args.pf_czm_dd_cap / step_max);
        end
        n_back = 0;
        for i_back = 0:args.pf_czm_max_backtrack
            field_vars_trial = field_vars;
            field_vars_trial(active_dof, 1) = field_vars_trial(active_dof, 1) + step;
            [~, res_trial, ~, ~] = assembly_fh(...
                sys.MESH, sys.DOFS, sys.GEOM.t,...
                sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
                field_vars_trial, field_vars_old, coupling_vars_in,...
                sys.stress_state.as_number,...
                history_vars_old...
            );
            if any(args.D_RHS_tract ~= 0.0)
                res_trial = res_trial - args.D_RHS_tract;
            end
            res_trial_norm = norm(res_trial(active_dof, 1));
            if isfinite(res_trial_norm) && res_trial_norm <= res_baseline
                break;
            end
            step = step * args.pf_czm_backtrack_factor;
            n_back = n_back + 1;
        end
        if n_back > 0
            fprintf('         PF-CZM damping: %d backtracks, |step|_inf=%.3e, res_trial=%.3e (baseline %.3e)\n', ...
                n_back, max(abs(step)), res_trial_norm, res_baseline);
        end
        field_vars(active_dof, 1) = field_vars(active_dof, 1) + step;
    elseif (n_iter > args.line_search_maxiter) && args.line_search
        field_vars = phase_field.fem.solver.line_search(...
            sys, ...
            field_vars, ...
            field_vars_old, ...
            coupling_vars_in, ...
            history_vars_old, ...
            active_dof, ...
            Dfield_vars, ...
            assembly_fh, ...
            args.D_RHS_tract, ...
            args.res_tol);
    else
        field_vars(active_dof, 1) = field_vars(active_dof, 1) + Dfield_vars;
    end

    %compute residual norm
    res = norm(res_field_vars(active_dof,1));
    if (n_iter == 1)
        res_0 = res;
    end
    fprintf('         Newton-Raphson iteration:  %d  res_norm:   %g\n', n_iter, res);

    % convergence test
    if n_iter >= args.min_iter && res < args.res_tol
        break;
    end

    if n_iter == args.max_iter
        warning('         Newton-Raphson did not converge!')
        non_conv = true;
        break;
    end

end

end
