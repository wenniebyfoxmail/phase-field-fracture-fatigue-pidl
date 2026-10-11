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

% =========================================================================
%   INITIALIZATION
% =========================================================================

% Check for existing checkpoint before touching the output directory
checkpoint_file = [example_name filesep 'checkpoint.mat'];
checkpoint_exists = exist(checkpoint_file, 'file') == 2;
step_checkpoint_file = [example_name filesep 'step_checkpoint.mat'];
step_checkpoint_exists = exist(step_checkpoint_file, 'file') == 2;

if step_checkpoint_exists
    disp(['[STEP CHECKPOINT] Found: ' step_checkpoint_file ' - will resume from saved load step.']);
elseif checkpoint_exists
    disp(['[CHECKPOINT] Found: ' checkpoint_file ' — will resume from saved state.']);
else
    % Fresh run: wipe and recreate output directory
    if exist(example_name, 'dir')
        rmdir(example_name, 's');
    end
    mkdir(example_name);
end

displ       = zeros(DOFS.num_dof, 1);
p_field     = zeros(MESH.num_node, 1);
p_field(DOFS.non_hom_dirichlet_bc_pf, 1) = 1;
p_field_old = zeros(size(p_field));
res_p_field = zeros(size(p_field));

history_vars_old = zeros(MESH.num_elem, QUADRATURE.num_gauss_pts, 4);
%   convention:
%   (element, G_pts, 1) ... history variable for phase-field (irrev: history)
%                       ... current strain energy density (irrev: penalty)
%   (element, G_pts, 2) ... fatigue history variable
%   (element, G_pts, 3) ... fatigue history variable increment
%   (element, G_pts, 4) ... fatigue degradation function

SIG0 = sparse(MESH.tensors * MESH.num_node, DOFS.num_dof);

% =========================================================================
%   SYSTEM SETUP
% =========================================================================

% solver setup
SOL_STAG_VAR = phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
SOL_STEP_VAR = phase_field.fem.solver.step.vars(SOL_STEP_PAR);
SOL_CYCL_VAR = phase_field.fem.solver.cycl.vars(SOL_CYCL_PAR);
SOL_JUMP_VAR = phase_field.fem.solver.cycl_jump.vars(SOL_JUMP_PAR, MESH, QUADRATURE);

CRACK_VAR = phase_field.fem.crack.vars(CRACK_PAR);

% create system
sys = phase_field.System(...
    MAT_CHAR, GEOM, QUADRATURE, DOFS, NODE_BOUNDARIES, SOL_STEP_PAR,...
    MESH, stress_state, p_field, diss_fct...
);

% Prepare assembly function handles
assembly_pf_fh = str2func(...
    sprintf('phase_field.mex.fem.assembly.pf.%s_%s_FATIGUE', diss_fct, irrev)...
);
assembly_equilibrium_fh = str2func(...
    sprintf('phase_field.mex.fem.assembly.equilibrium.%s', split_type)...
);

%clear duplicates from memory
clear MAT_CHAR GEOM QUADRATURE DOFS NODE_BOUNDARIES MESH stress_state split_type diss_fct

% Load checkpoint state if available (overwrites zero-initialized fields above)
if step_checkpoint_exists
    ckpt = load(step_checkpoint_file, ...
        'displ', 'p_field', 'p_field_old', 'history_vars_old', ...
        'SOL_CYCL_VAR', 'SOL_STEP_VAR', 'CRACK_VAR', 'SOL_JUMP_VAR', ...
        'peak_psi_plus', 'i_step_completed');
    displ                 = ckpt.displ;
    p_field               = ckpt.p_field;
    p_field_old           = ckpt.p_field_old;
    history_vars_old      = ckpt.history_vars_old;
    SOL_CYCL_VAR          = ckpt.SOL_CYCL_VAR;
    SOL_STEP_VAR          = ckpt.SOL_STEP_VAR;
    CRACK_VAR             = ckpt.CRACK_VAR;
    SOL_JUMP_VAR          = ckpt.SOL_JUMP_VAR;
    step_resume_available = true;
    step_resume_cycle     = SOL_CYCL_VAR.n_cycle;
    step_resume_next_step = ckpt.i_step_completed + 1;
    if isfield(ckpt, 'peak_psi_plus')
        step_resume_peak_psi_plus = ckpt.peak_psi_plus;
    end
    if SOL_CYCL_VAR.n_cycle > 0
        SOL_CYCL_VAR.n_cycle = SOL_CYCL_VAR.n_cycle - 1;
    end
    disp(['[STEP CHECKPOINT] Resumed cycle ' num2str(step_resume_cycle) ...
          ', next load step ' num2str(step_resume_next_step) '.']);
    clear ckpt
elseif checkpoint_exists
    ckpt = load(checkpoint_file, ...
        'displ', 'p_field', 'p_field_old', 'history_vars_old', ...
        'SOL_CYCL_VAR', 'CRACK_VAR', 'SOL_JUMP_VAR');
    displ            = ckpt.displ;
    p_field          = ckpt.p_field;
    p_field_old      = ckpt.p_field_old;
    history_vars_old = ckpt.history_vars_old;
    SOL_CYCL_VAR     = ckpt.SOL_CYCL_VAR;
    CRACK_VAR        = ckpt.CRACK_VAR;
    SOL_JUMP_VAR     = ckpt.SOL_JUMP_VAR;
    disp(['[CHECKPOINT] Resumed from cycle ' num2str(SOL_CYCL_VAR.n_cycle) '.']);
    clear ckpt
end
clear checkpoint_exists checkpoint_file step_checkpoint_exists step_checkpoint_file
