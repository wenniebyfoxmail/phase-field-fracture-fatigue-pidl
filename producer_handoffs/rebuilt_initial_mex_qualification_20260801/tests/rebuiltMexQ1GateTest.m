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

        function testRunnerPublishesRuntimeBoundPassingArtifacts(testCase)
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

            receipt = run_q1_initial_mex_qualification(config);

            verifyTrue(testCase, receipt.passed);
            verifyEqual(testCase, receipt.runtime_lock_sha256, runtimeReceipt.lock_sha256);
            verifyEqual(testCase, receipt.runtime_initial_sha256, runtimeReceipt.initial_sha256);
            verifyEqual(testCase, receipt.source_commit, runtimeReceipt.source_commit);
            verifyEqual(testCase, strlength(string(receipt.input_sha256)), 64);
            verifyEqual(testCase, receipt.metrics.probe.name, ...
                'deterministic_internal_force_probe');
            verifyEqual(testCase, numel(fieldnames(receipt.metrics.output_shapes)), 12);
            verifyTrue(testCase, isfile(fullfile(outputRoot, 'Q1_RESULT.json')));
            verifyTrue(testCase, isfile(fullfile(outputRoot, 'Q1_METRICS.mat')));
            verifyTrue(testCase, isfile(fullfile(outputRoot, 'Q1_RECEIPT.json')));
            result = jsondecode(fileread(fullfile(outputRoot, 'Q1_RESULT.json')));
            verifyTrue(testCase, result.passed);
            verifyFalse(testCase, contains(lower(fileread( ...
                fullfile(outputRoot, 'Q1_RECEIPT.json'))), 'residual'));
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
