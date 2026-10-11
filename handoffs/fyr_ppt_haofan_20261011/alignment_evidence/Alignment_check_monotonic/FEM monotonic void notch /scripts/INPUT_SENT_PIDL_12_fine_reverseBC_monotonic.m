% =========================================================================
% PIDL-aligned monotonic SENT case.
%
% Same mesh/material/split/BC setting as INPUT_SENT_PIDL_12_fine_reverseBC:
%   - SENT_pidl_fine_lh5.inp
%   - AT1 + AMOR + PENALTY
%   - reverseBC: fix_X on top+bottom, fix_Y bottom, disp_Y top
%
% Difference:
%   - monotonic loading, one cycle, for direct FEM/PIDL field comparison
% =========================================================================

split_type = 'AMOR';
diss_fct   = 'AT1';
irrev      = 'PENALTY';

if ~exist('pidl_mono_example_name', 'var')
    pidl_mono_example_name = 'SENT_PIDL_12_fine_reverseBC_monotonic';
end
if ~exist('pidl_mono_uy_final', 'var')
    pidl_mono_uy_final = 0.12;
end
if ~exist('pidl_mono_n_step', 'var')
    pidl_mono_n_step = 8;
end
if ~exist('pidl_mono_alpha_T', 'var')
    pidl_mono_alpha_T = 0.5;
end
if exist('pidl_mono_uy_steps', 'var')
    pidl_mono_uy_steps = pidl_mono_uy_steps(:).';
    pidl_mono_uy_final = pidl_mono_uy_steps(end);
    pidl_mono_n_step = numel(pidl_mono_uy_steps);
end

example_name = pidl_mono_example_name;

[MESH, GEOM] = specimen.external.abaqus_import( ...
    'Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp', ...
    't', 1 ...
);

MAT_CHAR(1) = phase_field.init.material_characteristic( ...
    GEOM.L, diss_fct, ...
    'E',         1.0, ...
    'ni',        0.3, ...
    'Gc',        0.01, ...
    'ell',       0.01, ...
    'res_stiff', 1e-6, ...
    'alpha_T',   pidl_mono_alpha_T, ...
    'p',         2.0 ...
);
MESH.elem_material_id = ones(MESH.num_elem, 1);

bottom     = find(MESH.node(:,2) == -0.5);
top        = find(MESH.node(:,2) ==  0.5);
top_bottom = unique([top; bottom]);

NODE_BOUNDARIES = phase_field.fem.bc.set_boundaries( ...
    'fix_X',  top_bottom, ...
    'fix_Y',  bottom, ...
    'disp_Y', top ...
);

DOFS = phase_field.init.dofs(MESH, NODE_BOUNDARIES);
QUADRATURE = phase_field.init.quadrature(MESH.dim);
stress_state = phase_field.StressState.PlaneStrain;

SOL_PAR = phase_field.fem.solver.params( ...
    'tol_displ',      1e-6, ...
    'tol_p_field',    1e-5, ...
    'max_iter_displ', 250, ...
    'max_iter_pf',    250 ...
);
SOL_STAG_PAR = phase_field.fem.solver.stag.params('tol', 1e-4, 'max_iter', 1000);

SOL_STEP_PAR = phase_field.fem.solver.step.params( ...
    'n_step',         pidl_mono_n_step, ...
    'loading',        'monotonic', ...
    'discretization', 'loading', ...
    'uy_final',       pidl_mono_uy_final, ...
    'R',              0.0, ...
    'line_search',    true ...
);

if exist('pidl_mono_uy_steps', 'var')
    SOL_STEP_PAR.uy_values = pidl_mono_uy_steps;
    SOL_STEP_PAR.uy_increment = diff([0, pidl_mono_uy_steps]);
    SOL_STEP_PAR.ux_increment = zeros(1, SOL_STEP_PAR.n_step);
    SOL_STEP_PAR.load_factors = pidl_mono_uy_steps ./ pidl_mono_uy_final;
end

SOL_CYCL_PAR = phase_field.fem.solver.cycl.params( ...
    'max_cycle',   1, ...
    'da_paraview', 0.01 ...
);

SOL_JUMP_PAR = phase_field.fem.solver.cycl_jump.params('cycl_jump', false);
CRACK_PAR = phase_field.fem.crack.params(MAT_CHAR, diss_fct);

checkpoint_freq = 1;
vtk_freq        = 1;
enable_step_checkpoint = true;
step_checkpoint_freq = 1;

fprintf('=== PIDL-aligned monotonic SENT, u=%.4g ===\n', pidl_mono_uy_final);
fprintf('  Mesh: %d nodes, %d quads (SENT_pidl_fine_lh5.inp)\n', MESH.num_node, MESH.num_elem);
fprintf('  Model: AT1 + AMOR + PENALTY, alpha_T=%.4g, p=2\n', pidl_mono_alpha_T);
fprintf('  Loading: monotonic, n_step=%d\n', SOL_STEP_PAR.n_step);
if isfield(SOL_STEP_PAR, 'uy_values')
    fprintf('  Explicit uy steps: %s\n', mat2str(SOL_STEP_PAR.uy_values, 6));
end
fprintf('  BC: fix_X top+bottom, fix_Y bottom, disp_Y top\n');
