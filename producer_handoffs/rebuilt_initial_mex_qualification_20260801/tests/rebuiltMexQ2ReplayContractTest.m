function tests = rebuiltMexQ2ReplayContractTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
family = fullfile(fileparts(handoff), ...
    'toy_to_road_independent_fem_20260731');
familyTests = fullfile(family, 'tests');
addpath(familyTests);
testCase.addTeardown(@() rmpath(familyTests));
end

function testCurrentParentBlocksBeforeAnySolverStage(testCase)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
handoff = fileparts(fileparts(mfilename('fullpath')));
family = fullfile(fileparts(handoff), ...
    'toy_to_road_independent_fem_20260731');
config = struct( ...
    'output_root', fullfile(folder.Folder, 'q2_blocked'), ...
    'parent_root', 'C:/q4diag/toy-road-parent-20260729', ...
    'parent_lock_path', fullfile(family, 'PARENT_LOCK.json'), ...
    'runtime_lock_path', fullfile(folder.Folder, 'must_not_be_read.json'), ...
    'runtime_root', fullfile(folder.Folder, 'must_not_be_read_runtime'), ...
    'source_root', fullfile(folder.Folder, 'must_not_be_read_source'));

receipt = run_q2_parent_cycle1_replay(config);

verifyEqual(testCase, receipt.status, 'blocked');
verifyEqual(testCase, sort(receipt.blockers), sort({ ...
    'blocked_missing_parent_damage_degradation_field', ...
    'blocked_missing_parent_active_field'}));
verifyEqual(testCase, receipt.stage, 'parent_evidence_gate');
verifyFalse(testCase, receipt.recovery_started);
verifyFalse(testCase, receipt.system_started);
verifyFalse(testCase, receipt.newton_started);
verifyFalse(testCase, receipt.cycle_started);
verifyTrue(testCase, isfile(fullfile(config.output_root, ...
    'Q2_PARENT_BLOCKER.json')));
verifyFalse(testCase, isfile(fullfile(config.output_root, ...
    'Q2_CYCLE1_TERMINAL.json')));
end

function testHistoricalRecoveryClipsResetsAndKeepsOriginalSystem(testCase)
dofs = struct('active_dof_pf', [2; 3]);
stiffness = struct('i_row_pf', [1; 2], 'j_col_pf', [1; 2]);
initialSystem = ToyRoadRecoverySystem(struct(), struct(), struct(), dofs, ...
    struct(), struct(), struct(), struct(), zeros(4, 1), 'AT1', stiffness);
history = zeros(2, 2, 4);
input = struct( ...
    'sys', initialSystem, ...
    'assembly_pf_fh', @unusedAssembly, ...
    'p_field', [1; 0; 0; 1], ...
    'p_field_old', zeros(4, 1), ...
    'history_vars_old', history, ...
    'num_elem', 2, 'num_gauss_points', 2, ...
    'max_iter_pf', 250, 'tol_p_field', 4e-4);
operators = struct('newton_raphson', @recoveryNewton);

[sys, damage, damageOld, recoveredHistory, residual, audit] = ...
    recover_q2_parent_initial_state(input, operators);

verifyEqual(testCase, sys, initialSystem);
verifyEqual(testCase, damage, [0; 0.2; 1; 1]);
verifyEqual(testCase, damageOld, damage);
verifyEqual(testCase, recoveredHistory(:, :, 2:3), zeros(2, 2, 2));
verifyEqual(testCase, recoveredHistory(:, :, 4), ones(2, 2));
verifyEqual(testCase, residual, 2e-5);
verifyEqual(testCase, audit.recovery_projection, 'clip_[0,1]');
verifyFalse(testCase, audit.rebuild_sys_after_recovery);
verifyTrue(testCase, audit.reset_fatigue_after_recovery);

    function [initialResidual, finalResidual, field, coupling, h, failed] = ...
            recoveryNewton(varargin)
        verifyEqual(testCase, varargin{2}, initialSystem);
        verifyEqual(testCase, varargin{5}, zeros(2, 2));
        initialResidual = 1;
        finalResidual = 2e-5;
        field = [-1e-8; 0.2; 1.2; 1];
        coupling = zeros(4, 1);
        h = zeros(2, 2, 4);
        h(:, :, 1) = 0.3;
        failed = false;
    end
end

function testExporterUsesGaussPointProductAndExactElementOrder(testCase)
input = exportFixture();

state = export_q2_cycle1_fields(input);

expectedDamageGp = input.p_field(input.connectivity) * ...
    q4ShapeFunctions(input.quadrature_points).';
expectedG = (1 - expectedDamageGp) .^ 2;
verifyEqual(testCase, state.element_ids, int64((1:2)'));
verifyEqual(testCase, state.d_elem, mean(expectedDamageGp, 2), 'AbsTol', 0);
verifyEqual(testCase, state.psi_raw_GP, input.psi_raw_GP, 'AbsTol', 0);
verifyEqual(testCase, state.psi_raw_elem, mean(input.psi_raw_GP, 2), 'AbsTol', 0);
verifyEqual(testCase, state.g_GP, expectedG, 'AbsTol', 0);
verifyEqual(testCase, state.g_elem, mean(expectedG, 2), 'AbsTol', 0);
verifyEqual(testCase, state.psi_active_elem, ...
    mean(expectedG .* input.psi_raw_GP, 2), 'AbsTol', 0);
verifyNotEqual(testCase, state.psi_active_elem, ...
    mean(expectedG, 2) .* mean(input.psi_raw_GP, 2));
verifyEqual(testCase, state.field_sources.psi_active_elem, ...
    'sealed_gp:mean_gp(g_gp.*psi_raw_gp)');
verifyFalse(testCase, state.family_terminal_eligible);
end

function testControlledReplayDisclosesConstructorAndEffectiveCadence(testCase)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
context = controlledContext(folder.Folder);
preSteps = [];
newtonCalls = 0;
context.operators = struct( ...
    'pre_iter_update', @preStep, ...
    'stag_vars', @(~) struct(), ...
    'newton_raphson', @newton, ...
    'stag_post_iter_update', @postStagger, ...
    'assembly_pf', @assemblyPf, ...
    'assembly_equilibrium', @assemblyEquilibrium);

result = solve_q2_parent_cycle1(context);

verifyEqual(testCase, preSteps, 1:5);
verifyEqual(testCase, newtonCalls, 10);
verifyEqual(testCase, result.status, 'q2_cycle1_diagnostic_complete');
verifyEqual(testCase, result.cycle, 1);
verifyEqual(testCase, result.constructor_request.n_step, 8);
verifyEqual(testCase, result.constructor_return.n_step, 5);
verifyEqual(testCase, result.effective_retained_factors, ...
    [0.25 0.5 0.75 1.0 0.0], 'AbsTol', 0);
verifyEqual(testCase, result.peak_substep_ordinal, 4);
verifyFalse(testCase, result.family_terminal_eligible);
verifyTrue(testCase, isfile(fullfile(folder.Folder, ...
    'Q2_CYCLE1_STATE.mat')));
verifyTrue(testCase, isfile(fullfile(folder.Folder, ...
    'Q2_CYCLE1_TERMINAL.json')));

    function [displ, residual, traction] = preStep(index, ~, displ, step)
        preSteps(end + 1) = index;
        verifyEqual(testCase, step.n_step, 5);
        verifyEqual(testCase, step.uy_increment, ...
            0.12 * diff([0 0.25 0.5 0.75 1 0]), 'AbsTol', 0);
        residual = 0;
        traction = zeros(8, 1);
    end

    function [r0, r, field, raw, coupling, failed] = newton(assembly, ~, ...
            field, ~, raw, varargin)
        newtonCalls = newtonCalls + 1;
        r0 = 1;
        r = 0;
        coupling = zeros(size(field));
        failed = false;
        if isequal(assembly, context.assembly_equilibrium_fh)
            raw = [0.1 0.4; 0.2 0.8];
        end
    end

    function [vars, raw, converged, stiffness] = postStagger(varargin)
        vars = varargin{3};
        raw = [0.1 0.4; 0.2 0.8];
        converged = true;
        stiffness = speye(8);
    end

    function [a, b, c, h] = assemblyPf(varargin)
        a = [];
        b = [];
        c = [];
        h = varargin{11};
        h(:, :, 2) = 0.2;
        h(:, :, 4) = 1;
    end

    function [stiffness, reaction, raw, h] = assemblyEquilibrium(varargin)
        stiffness = [];
        reaction = zeros(8, 1);
        raw = [0.1 0.4; 0.2 0.8];
        h = [];
    end
end

function testReplayRejectsHandSetOrIncompleteContracts(testCase)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
context = controlledContext(folder.Folder);
context.contract.constructor_request.n_step = 5;
verifyError(testCase, @() solve_q2_parent_cycle1(context), ...
    'rebuiltMexQ2:ReplayContractMismatch');

context = controlledContext(folder.Folder);
context.contract.constructor_return.n_step = 8;
verifyError(testCase, @() solve_q2_parent_cycle1(context), ...
    'rebuiltMexQ2:ReplayContractMismatch');

context = controlledContext(folder.Folder);
context.operators = rmfield(context.operators, 'newton_raphson');
verifyError(testCase, @() solve_q2_parent_cycle1(context), ...
    'rebuiltMexQ2:MissingSolverApi');
end

function testQ2TerminalMarkerCannotAppearInFamilyRunner(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
familySolver = fileread(fullfile(fileparts(handoff), ...
    'toy_to_road_independent_fem_20260731', 'solve_toy_to_road_case.m'));
q2Solver = fileread(fullfile(handoff, 'solve_q2_parent_cycle1.m'));
verifyFalse(testCase, contains(familySolver, ...
    'q2_cycle1_diagnostic_complete'));
verifyTrue(testCase, contains(q2Solver, ...
    'q2_cycle1_diagnostic_complete'));
end

function context = controlledContext(outputRoot)
mesh = struct('num_node', 4, 'num_elem', 2, 'nel', 4, ...
    'node', [0 0; 1 0; 1 1; 0 1], ...
    'elem', [1 2 3 4; 1 2 3 4]);
quadrature = struct('num_gauss_pts', 2, ...
    'gauss_pts', [-0.5 -0.5; 0.5 0.5], 'gauss_W', [1; 1]);
sys = struct('MESH', mesh, 'QUADRATURE', quadrature, ...
    'DOFS', struct('active_dof', (1:8)', 'active_dof_pf', (1:4)'), ...
    'STIFFNESS_MATRIX', struct('i_row', (1:8)', 'j_col', (1:8)', ...
    'i_row_pf', (1:4)', 'j_col_pf', (1:4)', 'KK', speye(8)), ...
    'GEOM', struct('t', 1), 'MAT_CHAR', struct('res_stiff', 0), ...
    'CC', eye(3), 'stress_state', struct('as_number', 2));
operators = struct( ...
    'pre_iter_update', @unusedAssembly, 'stag_vars', @unusedAssembly, ...
    'newton_raphson', @unusedAssembly, ...
    'stag_post_iter_update', @unusedAssembly, ...
    'assembly_pf', @unusedAssembly, ...
    'assembly_equilibrium', @unusedAssembly);
contract = struct( ...
    'case_id', 'Q2_native_parent_cycle1', 'unmapped_mesh', true, ...
    'eta', 0, 'Umax', 0.12, 'R', 0, 'one_cycle_only', true, ...
    'constructor_request', struct('n_step', 8, 'loading', 'cyclic', ...
    'discretization', 'loading', 'R', 0), ...
    'constructor_return', struct('n_step', 5), ...
    'effective_retained_factors', [0.25 0.5 0.75 1 0], ...
    'peak_substep_ordinal', 4, ...
    'rebuild_sys_after_recovery', false);
context = struct('output_root', outputRoot, 'contract', contract, ...
    'sys', sys, 'sol_par', struct('max_iter_displ', 250, ...
    'tol_displ', 1e-6, 'max_iter_pf', 250, 'tol_p_field', 4e-4), ...
    'sol_stag_par', struct('max_iter', 1, 'tol', 4e-4), ...
    'sol_step_par', struct('n_step', 5), ...
    'assembly_pf_fh', @unusedAssembly, ...
    'assembly_equilibrium_fh', @unusedAssembly, ...
    'displ', zeros(8, 1), 'p_field', [1; 0.2; 0.4; 1], ...
    'p_field_old', [1; 0.2; 0.4; 1], ...
    'history_vars_old', zeros(2, 2, 4), 'operators', operators);
end

function input = exportFixture()
input = struct( ...
    'connectivity', [1 2 3 4; 1 2 3 4], ...
    'element_ids', int64((1:2)'), ...
    'quadrature_points', [-0.5 -0.5; 0.5 0.5], ...
    'p_field', [1; 0.2; 0.4; 1], ...
    'history_vars', cat(3, zeros(2, 2), [0.1 0.2; 0.3 0.4], ...
    zeros(2, 2), ones(2, 2)), ...
    'psi_raw_GP', [0.1 0.4; 0.2 0.8], ...
    'eta', 0, 'cycle', 1, 'peak_substep_ordinal', 4);
end

function values = q4ShapeFunctions(points)
xi = points(:, 1);
eta = points(:, 2);
values = 0.25 * [(1-xi).*(1-eta), (1+xi).*(1-eta), ...
    (1+xi).*(1+eta), (1-xi).*(1+eta)];
end

function varargout = unusedAssembly(varargin)
varargout = cell(1, max(nargout, 1));
end
