function [SOL_STAG_VAR, coupling_vars_updated, converged, KK_updated] = post_iter_update(...
    assembly_equilibrium_fh,...
    i_stag, SOL_STAG_VAR,...
    sys,...
    D_RHS_tract,...
    p_field, displ,...
    res_pf_0, res_pf, res_displ_0,...
    SOL_STAG_PAR...
)
%POST_ITER_UPDATE Staggered-iteration post processing vectors update
%   ...

% Copyright (C) 2021 ETH Zurich, SIS ID and CompMech D-MAVT
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
    assembly_equilibrium_fh (1, 1) function_handle
    i_stag (1, 1) double {mustBeInteger, mustBePositive}
    SOL_STAG_VAR (:, 8) table
    sys (1, 1) handle
    D_RHS_tract (:, 1) double
    p_field (:, 1) double
    displ (:, 1) double
    res_pf_0 (1, 1) double
    res_pf (:, 1) double
    res_displ_0 (1, 1) double
    SOL_STAG_PAR (1, 1) struct
end

% =========================================================================

%update displacement field residual, stiffness matrix and coupling vars with converged phase-field
[K_vect_updated, res_displ_updated, coupling_vars_updated, ~] = assembly_equilibrium_fh(...
    sys.MESH, sys.DOFS, sys.GEOM.t,...
    sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
    displ, 0.0, p_field,...
    sys.stress_state.as_number,...
    0.0...
);
KK_updated = sparse(sys.STIFFNESS_MATRIX.i_row, sys.STIFFNESS_MATRIX.j_col, K_vect_updated);

%get displacement field residual norm
res_displ = res_displ_updated - D_RHS_tract;
norm_res_displ = norm(res_displ(sys.DOFS.active_dof,1));

%compute elastic energy of the system
el_en = 0.5*displ'*KK_updated*displ;
SOL_STAG_VAR.el_en(i_stag) = el_en;

%compute the fracture energy of the system
if strcmp(sys.diss_fct,'AT1')
    c_w = 8/3;
    order = 1;
elseif strcmp(sys.diss_fct,'AT2')
    c_w = 2;
    order = 2;
elseif strcmp(sys.diss_fct,'PF_CZM')
    % Wu PF-CZM alpha(d) = 2d - d^2, c_alpha = pi.
    % fracture_energy.f90 only supports order in {1,2}; approximate Wu's alpha
    % by its linear part 2d (order=1) with c_w=pi/2 so that t/c_w*Gc/ell*2d = (2/pi)*Gc/ell*d
    % matches Wu's leading-order dissipation for small d. Used for monitoring only;
    % solver convergence is on residuals (line 89), not energy.
    c_w = pi/2;
    order = 1;
end
fract_en = phase_field.mex.fem.processing.fracture_energy(...
    sys.MESH, sys.GEOM.t, sys.QUADRATURE,...
    sys.MAT_CHAR, sys.CC, p_field,...
    c_w, order...
);
SOL_STAG_VAR.fract_en(i_stag) = fract_en;

%compute total energy of the system
tot_en = el_en + fract_en;
SOL_STAG_VAR.tot_en(i_stag) = tot_en;


% =========================================================================

%store residuals of displacement and phase-field
SOL_STAG_VAR.normal_res_pf(i_stag) = res_pf;
SOL_STAG_VAR.normal_res_displ(i_stag) = norm_res_displ;

%decide whether the staggered loop has converged
res_sum = SOL_STAG_VAR.normal_res_displ(i_stag)+SOL_STAG_VAR.normal_res_pf(i_stag);
converged = res_sum <= SOL_STAG_PAR.tol;


%compute normalized residual criteria (just for output purposes)
if i_stag == 1
    normal_var_en_tot = 1;
    normal_res = 1;
    normal_var_res = 1;

    %set values of non-existent previous staggered iteration to zero
    tot_en_prev = 0;
    norm_res_displ_prev = 0;
    norm_res_pf_prev = 0;

else

    %get values of previous staggered iteration
    tot_en_prev = SOL_STAG_VAR.tot_en(i_stag-1);
    norm_res_displ_prev = SOL_STAG_VAR.normal_res_displ(i_stag-1);
    norm_res_pf_prev = SOL_STAG_VAR.normal_res_pf(i_stag-1);

    tot_en_0 = SOL_STAG_VAR.tot_en(1);

    normal_var_en_tot = abs( (tot_en_prev-tot_en)/(tot_en_0-tot_en) );
    normal_res        = abs( (norm_res_displ)/res_displ_0 ) + abs( (res_pf)/res_pf_0 );
    normal_var_res    = abs( (norm_res_displ_prev - norm_res_displ)/(res_displ_0 - norm_res_displ) ) ...
                        + abs( (norm_res_pf_prev - res_pf)/(res_pf_0 - res_pf) );
end
SOL_STAG_VAR.normal_var_en_tot(i_stag) = normal_var_en_tot;
SOL_STAG_VAR.normal_res(i_stag) = normal_res;
SOL_STAG_VAR.normal_var_res(i_stag) = normal_var_res;

%print information on staggered loop
disp([' STAG ITER Nr.: ', num2str(i_stag), '  tot_en=', num2str(tot_en), ' res_sum=', num2str(res_sum)]);
disp(' ');

end
