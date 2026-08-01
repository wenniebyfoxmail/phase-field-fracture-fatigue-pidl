classdef rebuiltMexQ2MetricsTest < matlab.unittest.TestCase
    methods (Test)
        function testMasksUseOnlyParentAndFixedThreshold(testCase)
            parent = metricParent();
            masks = build_q2_parent_masks(parent);

            expected = parent.fields.raw.values > max(1e-14, ...
                1e-12 * max(abs(parent.fields.raw.values)));
            verifyEqual(testCase, masks.fields.raw.mask, expected);
            verifyEqual(testCase, masks.fields.raw.threshold, ...
                max(1e-14, 1e-12 * max(abs(parent.fields.raw.values))), ...
                'AbsTol', 0);
            verifyEqual(testCase, masks.log_floor, 1e-14, 'AbsTol', 0);
            verifyEqual(testCase, masks.variance_tolerance, 1e-14, 'AbsTol', 0);
            verifyEqual(testCase, masks.negative_tolerance, 1e-14, 'AbsTol', 0);

            candidate = metricCandidate(parent);
            metrics = compare_q2_cycle1_fields(parent, candidate, masks);
            verifyEqual(testCase, metrics.mask_set_sha256, masks.mask_set_sha256);
            verifyEqual(testCase, metrics.fields.raw.support_count, nnz(expected));
        end

        function testMaskArtifactIsHashBoundAndNoClobber(testCase)
            parent = metricParent();
            folder = matlab.unittest.fixtures.TemporaryFolderFixture;
            testCase.applyFixture(folder);
            outputPath = fullfile(folder.Folder, 'Q2_PARENT_MASKS.mat');

            masks = build_q2_parent_masks(parent, outputPath);

            verifyTrue(testCase, isfile(outputPath));
            saved = load(outputPath, 'mask_artifact');
            verifyEqual(testCase, saved.mask_artifact.mask_set_sha256, ...
                masks.mask_set_sha256);
            verifyEqual(testCase, saved.mask_artifact.parent_cycle1_sha256, ...
                parent.parent_cycle1_sha256);
            verifyError(testCase, @() build_q2_parent_masks(parent, outputPath), ...
                'rebuiltMexQ2:OutputExists');
        end

        function testExactCandidatePassesAllFieldGates(testCase)
            parent = metricParent();
            candidate = metricCandidate(parent);
            masks = build_q2_parent_masks(parent);

            metrics = compare_q2_cycle1_fields(parent, candidate, masks);

            verifyTrue(testCase, metrics.passed);
            verifyEqual(testCase, metrics.fields.damage.mae, 0);
            verifyEqual(testCase, metrics.fields.history.log10_mae, 0);
            verifyEqual(testCase, metrics.fields.raw.log10_rmse, 0);
            verifyEqual(testCase, metrics.fields.active.log10_correlation, 1);
            verifyEqual(testCase, ...
                metrics.fields.fatigue_degradation.correlation, ...
                'not_applicable_zero_variance');
            verifyNotEqual(testCase, ...
                metrics.fields.fatigue_degradation.correlation, 1);
        end

        function testRejectsNegativeBeforeLogClipping(testCase)
            parent = metricParent();
            parent.fields.history.values(2) = -2e-14;
            verifyError(testCase, @() build_q2_parent_masks(parent), ...
                'rebuiltMexQ2:NegativeField');

            parent = metricParent();
            masks = build_q2_parent_masks(parent);
            candidate = metricCandidate(parent);
            candidate.fields.raw.values(2) = -2e-14;
            verifyError(testCase, @() compare_q2_cycle1_fields( ...
                parent, candidate, masks), 'rebuiltMexQ2:NegativeField');

            candidate = metricCandidate(parent);
            candidate.fields.raw.values(1) = -5e-15;
            metrics = compare_q2_cycle1_fields(parent, candidate, masks);
            verifyEqual(testCase, metrics.log_transform, ...
                'log10(max(q,0)+1e-14)');
        end

        function testOutsideMaskUsesFixedAbsoluteGates(testCase)
            parent = metricParent();
            masks = build_q2_parent_masks(parent);
            candidate = metricCandidate(parent);
            outside = ~masks.fields.raw.mask;
            candidate.fields.raw.values(find(outside, 1)) = 2e-10;

            verifyError(testCase, @() compare_q2_cycle1_fields( ...
                parent, candidate, masks), 'rebuiltMexQ2:GateFailed');

            candidate = metricCandidate(parent);
            candidate.fields.raw.values(find(outside, 1)) = 5e-13;
            metrics = compare_q2_cycle1_fields(parent, candidate, masks);
            verifyLessThanOrEqual(testCase, ...
                metrics.fields.raw.outside_absolute_mae, 1e-12);
            verifyLessThanOrEqual(testCase, ...
                metrics.fields.raw.outside_absolute_max_error, 1e-10);
        end

        function testEmptySupportUsesWholeFieldAbsoluteGates(testCase)
            parent = metricParent();
            parent.fields.active.values(:) = 0;
            candidate = metricCandidate(parent);
            candidate.fields.active.values(:) = 5e-13;
            masks = build_q2_parent_masks(parent);

            metrics = compare_q2_cycle1_fields(parent, candidate, masks);

            verifyEqual(testCase, metrics.fields.active.support_count, 0);
            verifyEqual(testCase, metrics.fields.active.log10_correlation, ...
                'not_applicable_zero_variance');
            verifyTrue(testCase, metrics.fields.active.absolute_only);
        end

        function testZeroVarianceRulesArePredeclared(testCase)
            parent = metricParent();
            masks = build_q2_parent_masks(parent);
            verifyTrue(testCase, ...
                masks.fields.fatigue_degradation.reference_zero_variance);

            candidate = metricCandidate(parent);
            metrics = compare_q2_cycle1_fields(parent, candidate, masks);
            verifyEqual(testCase, ...
                metrics.fields.fatigue_degradation.correlation, ...
                'not_applicable_zero_variance');

            candidate = metricCandidate(parent);
            support = masks.fields.history.mask;
            candidate.fields.history.values(support) = 1;
            verifyError(testCase, @() compare_q2_cycle1_fields( ...
                parent, candidate, masks), 'rebuiltMexQ2:GateFailed');
        end

        function testEveryImmutableThresholdFailsClosed(testCase)
            parent = metricParent();
            masks = build_q2_parent_masks(parent);

            candidate = metricCandidate(parent);
            candidate.fields.damage.values = ...
                candidate.fields.damage.values + 0.006;
            verifyGateFailure(testCase, parent, candidate, masks);

            names = {'history', 'raw', 'damage_degradation', 'active'};
            for index = 1:numel(names)
                candidate = metricCandidate(parent);
                name = names{index};
                support = masks.fields.(name).mask;
                candidate.fields.(name).values(support) = ...
                    candidate.fields.(name).values(support) * 10^0.11;
                verifyGateFailure(testCase, parent, candidate, masks);
            end

            candidate = metricCandidate(parent);
            candidate.fields.fatigue_degradation.values = ...
                candidate.fields.fatigue_degradation.values + 2e-12;
            verifyGateFailure(testCase, parent, candidate, masks);
        end

        function testRejectsChangedMasksAndCandidateFieldSubstitution(testCase)
            parent = metricParent();
            masks = build_q2_parent_masks(parent);
            candidate = metricCandidate(parent);

            masks.fields.raw.mask = ~masks.fields.raw.mask;
            verifyError(testCase, @() compare_q2_cycle1_fields( ...
                parent, candidate, masks), 'rebuiltMexQ2:MaskIdentityMismatch');

            masks = build_q2_parent_masks(parent);
            candidate.fields.active.source = 'native:f_alpha_elem';
            verifyError(testCase, @() compare_q2_cycle1_fields( ...
                parent, candidate, masks), ...
                'rebuiltMexQ2:ProhibitedFieldSubstitute');
        end
    end
end

function verifyGateFailure(testCase, parent, candidate, masks)
verifyError(testCase, @() compare_q2_cycle1_fields(parent, candidate, masks), ...
    'rebuiltMexQ2:GateFailed');
end

function parent = metricParent()
fields = struct;
fields.damage = q2Field([0; 0.01; 0.04; 0.2; 0.6; 0.9], 'native:d_elem');
fields.history = q2Field([0; 1e-8; 1e-6; 1e-4; 1e-2; 1], ...
    'native:alpha_bar_elem');
fields.fatigue_degradation = q2Field(ones(6, 1), 'native:f_alpha_elem');
fields.raw = q2Field([0; 1e-9; 1e-7; 1e-5; 1e-3; 1e-1], ...
    'native:psi_raw_elem');
fields.damage_degradation = q2Field([1; 0.99; 0.9; 0.7; 0.2; 0.01], ...
    'native:g_elem');
fields.active = q2Field([0; 2e-10; 3e-8; 4e-6; 5e-4; 6e-2], ...
    'native:psi_active_elem');
parent = struct( ...
    'schema_version', 'rebuilt_initial_mex_q2_parent_receipt_v1', ...
    'status', 'ready', 'blockers', {{}}, ...
    'q2_input_lock_sha256', repmat('a', 1, 64), ...
    'parent_lock_sha256', repmat('b', 1, 64), ...
    'parent_cycle1_sha256', repmat('c', 1, 64), ...
    'parent_reference_id', 'fixture_parent', ...
    'mesh_ordering_sha256', repmat('d', 1, 64), ...
    'num_elem', 6, 'fields', fields);
end

function candidate = metricCandidate(parent)
candidate = struct( ...
    'parent_cycle1_sha256', parent.parent_cycle1_sha256, ...
    'parent_reference_id', parent.parent_reference_id, ...
    'mesh_ordering_sha256', parent.mesh_ordering_sha256, ...
    'num_elem', parent.num_elem, 'fields', parent.fields);
end

function value = q2Field(values, source)
value = struct('source', source, 'values', values(:));
end
