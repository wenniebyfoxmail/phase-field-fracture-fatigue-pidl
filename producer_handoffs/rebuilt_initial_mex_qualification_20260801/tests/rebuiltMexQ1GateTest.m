classdef rebuiltMexQ1GateTest < matlab.unittest.TestCase
    methods (Test)
        function testComparatorPassesExactOutputsAndFixedProbe(testCase)
            fixture = q1Fixture();
            metrics = compare_q1_initial_outputs( ...
                fixture.reference, fixture.reference, fixture.input);
            verifyTrue(testCase, metrics.passed);
            verifyEqual(testCase, metrics.probe.name, ...
                'deterministic_internal_force_probe');
            verifyEqual(testCase, metrics.probe.top_y_value, 0.03);
            verifyEqual(testCase, metrics.probe.relative_l2, 0);
            verifyFalse(testCase, contains(lower(jsonencode(metrics)), 'residual'));
        end

        function testComparatorRejectsIndexAndShapeDifferences(testCase)
            fixture = q1Fixture();
            candidate = fixture.reference;
            candidate.i_row(1) = candidate.i_row(1) + 1;
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');

            candidate = fixture.reference;
            candidate.K_vect(end) = [];
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');
        end

        function testComparatorAppliesNumericalAndZeroGates(testCase)
            fixture = q1Fixture();
            candidate = fixture.reference;
            candidate.K_vect = candidate.K_vect * (1 + 2e-12);
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');

            candidate = fixture.reference;
            candidate.M_vector = candidate.M_vector * (1 + 2e-12);
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');

            fixture.reference.sig0_vector(:) = 0;
            candidate = fixture.reference;
            candidate.sig0_vector(1) = 2e-14;
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');
        end

        function testComparatorRejectsNonfiniteAndOutOfRangeIndices(testCase)
            fixture = q1Fixture();
            candidate = fixture.reference;
            candidate.M_vector(1) = Inf;
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');

            candidate = fixture.reference;
            candidate.i_row_pf(1) = fixture.input.MESH.num_node + 1;
            verifyError(testCase, @() compare_q1_initial_outputs( ...
                fixture.reference, candidate, fixture.input), ...
                'rebuiltMexQ1:GateFailed');
        end

        function testRunnerRefusesClobberAndBindsReceipts(testCase)
            fixture = matlab.unittest.fixtures.TemporaryFolderFixture;
            testCase.applyFixture(fixture);
            outputRoot = fullfile(fixture.Folder, 'q1');
            mkdir(outputRoot);
            fclose(fopen(fullfile(outputRoot, 'Q1_RECEIPT.json'), 'w'));
            verifyError(testCase, @() run_q1_initial_mex_qualification( ...
                struct('output_root', outputRoot)), 'rebuiltMexQ1:OutputExists');
        end

        function testProductionRunnerRejectsOperationsOverride(testCase)
            folder = matlab.unittest.fixtures.TemporaryFolderFixture;
            testCase.applyFixture(folder);
            fixture = q1Fixture();
            outputRoot = fullfile(folder.Folder, 'q1');
            runtimeReceipt = struct( ...
                'lock_sha256', repmat('a', 1, 64), ...
                'initial_sha256', repmat('b', 1, 64), ...
                'source_commit', repmat('c', 1, 40), ...
                'source_clean', true, ...
                'runtime_artifact_path', 'fixture/initial.mexw64');
            operations = struct( ...
                'validate_runtime', @(varargin) runtimeReceipt, ...
                'build_input', @(varargin) fixture.input, ...
                'call_initial', @(varargin) fixture.reference);
            config = struct('output_root', outputRoot, ...
                'runtime_lock_path', 'fixture/RUNTIME_LOCK.json', ...
                'runtime_root', 'fixture/runtime', ...
                'source_root', 'fixture/source', 'operations', operations);

            verifyError(testCase, @() run_q1_initial_mex_qualification(config), ...
                'rebuiltMexQ1:InvalidConfig');
            verifyFalse(testCase, isfolder(outputRoot));
        end

        function testRuntimeResolverUsesApprovedArtifact(testCase)
            runtimeRoot = fullfile(handoffRoot(), 'runtime');
            receipt = runtimeReceipt(fullfile(runtimeRoot, 'initial.mexw64'), ...
                approvedInitialHash());

            resolved = resolve_q1_initial_runtime(receipt, runtimeRoot);

            verifyEqual(testCase, canonicalPath(resolved), ...
                canonicalPath(fullfile(runtimeRoot, 'initial.mexw64')));
            verifyEqual(testCase, canonicalPath(which('initial')), canonicalPath(resolved));
        end

        function testRuntimeResolverRejectsWrongHashAndPath(testCase)
            runtimeRoot = fullfile(handoffRoot(), 'runtime');
            approvedPath = fullfile(runtimeRoot, 'initial.mexw64');
            badHash = runtimeReceipt(approvedPath, repmat('d', 1, 64));
            verifyError(testCase, @() resolve_q1_initial_runtime( ...
                badHash, runtimeRoot), 'rebuiltMexQ1:RuntimeArtifactMismatch');

            folder = matlab.unittest.fixtures.TemporaryFolderFixture;
            testCase.applyFixture(folder);
            copiedPath = fullfile(folder.Folder, 'initial.mexw64');
            copyfile(approvedPath, copiedPath);
            wrongPath = runtimeReceipt(copiedPath, approvedInitialHash());
            verifyError(testCase, @() resolve_q1_initial_runtime( ...
                wrongPath, runtimeRoot), 'rebuiltMexQ1:RuntimeResolutionMismatch');
        end

        function testNativeSensInputMatchesLockedAssumptions(testCase)
            input = build_q1_native_input(griphfithRoot());

            verifyEqual(testCase, input.MESH.num_node, 86756);
            verifyEqual(testCase, input.MESH.num_elem, 86408);
            verifyEqual(testCase, input.MESH.nel, 4);
            verifyEqual(testCase, input.MESH.dim, 2);
            verifyEqual(testCase, input.MESH.tensors, 3);
            verifyEqual(testCase, input.QUADRATURE.num_gauss_pts, 4);
            verifyEqual(testCase, input.t, 1.0);
            verifyEqual(testCase, input.MAT_CHAR.E, 1.0);
            verifyEqual(testCase, input.MAT_CHAR.ni, 0.3);
            verifyEqual(testCase, input.MAT_CHAR.Gc, 0.01);
            verifyEqual(testCase, input.MAT_CHAR.ell, 0.01);
            verifyEqual(testCase, input.MAT_CHAR.res_stiff, 0.0);
            verifyEqual(testCase, input.MAT_CHAR.alpha_T, 0.5);
            verifyEqual(testCase, input.MAT_CHAR.p, 2.0);
            verifyTrue(testCase, all(abs(input.MESH.node(input.top_node_ids, 2) - 0.5) <= 1e-12));
            verifyTrue(testCase, all(abs(input.MESH.node(input.crack_node_ids, 2)) <= 1e-12));
            verifyTrue(testCase, all(input.MESH.node(input.crack_node_ids, 1) <= 1e-12));
            verifyEqual(testCase, find(input.field_vars == 1), input.crack_node_ids);
            verifyTrue(testCase, all(input.field_vars == 0 | input.field_vars == 1));
            verifyEqual(testCase, input.DOFS.non_hom_dirichlet_bc_pf(:), ...
                input.crack_node_ids);
            verifyEqual(testCase, input.state_semantics, ...
                'unrecovered_native_sens_hard_crack');
        end

        function testSourceContainsNoEquilibriumMexReferenceCall(testCase)
            source = fileread(fullfile(handoffRoot(), ...
                'assemble_initial_reference_q4.m'));
            verifyFalse(testCase, contains(source, ...
                'phase_field.mex.fem.assembly.equilibrium'));
        end
    end
end

function fixture = q1Fixture()
input = oneElementInput();
[values{1:12}] = assemble_initial_reference_q4(input.MESH, input.DOFS, ...
    input.t, input.QUADRATURE, input.MAT_CHAR, input.CC, input.field_vars);
names = {'K_vect'; 'i_row'; 'j_col'; 'M_vector'; 'i_row_sig'; ...
    'j_col_sig'; 'eps_vector'; 'i_row_eps'; 'j_col_eps'; ...
    'sig0_vector'; 'i_row_pf'; 'j_col_pf'};
fixture = struct('input', input, 'reference', cell2struct(values(:), names, 1));
end

function input = oneElementInput()
mesh = struct('num_node', 4, 'num_elem', 1, 'nel', 4, 'dim', 2, ...
    'tensors', 3, 'node', [0 0; 1 0; 1 1; 0 1], ...
    'elem', [1 2 3 4], 'elem_material_id', 1);
dofs = struct('num_dof_node', 2, 'num_dof', 8);
quadrature = struct('num_gauss_pts', 1, 'gauss_W', 4, ...
    'dNdxi', reshape([-0.25 0.25 0.25 -0.25; ...
                      -0.25 -0.25 0.25 0.25], 2, 4, 1), ...
    'Nxi', 0.25 * ones(4, 1));
input = struct('MESH', mesh, 'DOFS', dofs, 't', 2, ...
    'QUADRATURE', quadrature, 'MAT_CHAR', struct('res_stiff', 0.1), ...
    'CC', diag([2 3 4]), 'field_vars', [0; 0.2; 0.4; 0.6], ...
    'top_node_ids', [3; 4]);
end

function value = handoffRoot()
value = fileparts(fileparts(mfilename('fullpath')));
end

function value = griphfithRoot()
value = getenv('GRIPHFITH_SOURCE_ROOT');
if isempty(value)
    value = 'C:/q4diag/griphfith-f1b-355d4c83';
end
end

function value = approvedInitialHash()
value = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
end

function value = runtimeReceipt(path, hash)
value = struct('runtime_artifact_path', path, 'initial_sha256', hash);
end

function value = canonicalPath(path)
value = char(java.io.File(path).getCanonicalPath());
end
