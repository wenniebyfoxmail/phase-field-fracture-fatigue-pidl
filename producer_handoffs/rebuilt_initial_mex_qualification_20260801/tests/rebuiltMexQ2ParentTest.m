classdef rebuiltMexQ2ParentTest < matlab.unittest.TestCase
    methods (Test)
        function testAcceptsOnlyAuthoritativeNativeElementFields(testCase)
            fixture = makeParentFixture(testCase, 'complete');

            receipt = validate_q2_parent_fields_test_only(fixture.q2_lock, ...
                fixture.parent_lock, fixture.parent_root);

            verifyEqual(testCase, receipt.status, 'ready');
            verifyEmpty(testCase, receipt.blockers);
            verifyEqual(testCase, receipt.fields.active.source, ...
                'native:psi_active_elem');
            verifyEqual(testCase, receipt.fields.damage_degradation.source, ...
                'native:g_elem');
            verifyEqual(testCase, receipt.fields.raw.source, ...
                'native:psi_raw_elem');
            verifyEqual(testCase, receipt.num_elem, 3);
        end

        function testRejectsFatigueDegradationAsActive(testCase)
            fixture = makeParentFixture(testCase, 'complete');
            parentLock = jsondecode(fileread(fixture.parent_lock));
            parentLock.state_semantics.field_map.active_driver = 'f_alpha_elem';
            writeJson(fixture.parent_lock, parentLock);
            rebindParentLock(fixture.q2_lock, fixture.parent_lock);

            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:ProhibitedFieldSubstitute');
        end

        function testIgnoresProhibitedElementDerivedDeclarations(testCase)
            fixture = makeParentFixture(testCase, 'missing_g_active');
            parentLock = jsondecode(fileread(fixture.parent_lock));
            parentLock.state_semantics.derived_fields = struct( ...
                'damage_degradation', '(1-damage)^2', ...
                'active_driver', 'damage_degradation*raw_driver');
            writeJson(fixture.parent_lock, parentLock);
            rebindParentLock(fixture.q2_lock, fixture.parent_lock);

            receipt = validate_q2_parent_fields_test_only(fixture.q2_lock, ...
                fixture.parent_lock, fixture.parent_root);

            verifyEqual(testCase, sort(receipt.blockers), sort({ ...
                'blocked_missing_parent_damage_degradation_field', ...
                'blocked_missing_parent_active_field'}));
            verifyEqual(testCase, receipt.status, 'blocked');
            verifyFalse(testCase, isfield(receipt.fields, 'active'));
            verifyFalse(testCase, isfield(receipt.fields, 'damage_degradation'));
        end

        function testRejectsElementMeanAndNodalDamageSubstitutes(testCase)
            fixture = makeParentFixture(testCase, 'missing_g_active');
            parentLock = jsondecode(fileread(fixture.parent_lock));
            parentLock.state_semantics.derived_fields = struct( ...
                'damage_degradation', '(1-d_elem)^2', ...
                'active_driver', '(1-d_elem)^2.*psi_raw_elem');
            writeJson(fixture.parent_lock, parentLock);
            rebindParentLock(fixture.q2_lock, fixture.parent_lock);

            receipt = validate_q2_parent_fields_test_only(fixture.q2_lock, ...
                fixture.parent_lock, fixture.parent_root);
            verifyEqual(testCase, numel(receipt.blockers), 2);

            parentLock.state_semantics.field_map.active_driver = ...
                'mean(g_gp,2).*mean(psi_raw_gp,2)';
            writeJson(fixture.parent_lock, parentLock);
            rebindParentLock(fixture.q2_lock, fixture.parent_lock);
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:ProhibitedFieldSubstitute');
        end

        function testReconstructsOnlyFromSealedGaussPointProduct(testCase)
            fixture = makeParentFixture(testCase, 'missing_g_active');
            g_gp = [1 1 1 1; 0.5 0.7 0.6 0.8; 0.01 0.03 0.05 0.07];
            psi_raw_gp = [0 0 0 0; 0.1 0.2 0.3 0.4; 1 2 3 4];
            configureGpSupplement(fixture, g_gp, psi_raw_gp);

            receipt = validate_q2_parent_fields_test_only(fixture.q2_lock, ...
                fixture.parent_lock, fixture.parent_root, ...
                struct('supplement_root', fixture.folder));

            verifyEqual(testCase, receipt.status, 'ready');
            verifyEqual(testCase, receipt.fields.damage_degradation.values, ...
                mean(g_gp, 2), 'AbsTol', 0);
            verifyEqual(testCase, receipt.fields.active.values, ...
                mean(g_gp .* psi_raw_gp, 2), 'AbsTol', 0);
            verifyNotEqual(testCase, receipt.fields.active.values, ...
                mean(g_gp, 2) .* mean(psi_raw_gp, 2));
            verifyEqual(testCase, receipt.fields.active.source, ...
                'sealed_gp:mean_gp(g_gp.*psi_raw_gp)');
            verifyEqual(testCase, receipt.supplement_provenance.parent_reference_id, ...
                'fixture_parent');
            verifyEqual(testCase, receipt.supplement_provenance.source_id, ...
                'fixture_gp_export_v1');
            verifyEqual(testCase, receipt.supplement_provenance.parent_cycle1_sha256, ...
                receipt.parent_cycle1_sha256);
            verifyEqual(testCase, receipt.supplement_provenance.mesh_ordering_sha256, ...
                receipt.mesh_ordering_sha256);
            verifyEqual(testCase, receipt.supplement_provenance.element_ids, ...
                int64((1:3)'));
        end

        function testSupplementRejectsIdentityAndOrderingMismatches(testCase)
            fixture = makeParentFixture(testCase, 'missing_g_active');
            g_gp = [1 1; 0.5 0.7; 0.01 0.03];
            psi_raw_gp = [0 0; 0.1 0.2; 1 2];
            configureGpSupplement(fixture, g_gp, psi_raw_gp);

            lock = jsondecode(fileread(fixture.q2_lock));
            lock.supplement.parent_reference_id = 'wrong_parent';
            writeJson(fixture.q2_lock, lock);
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root, ...
                struct('supplement_root', fixture.folder)), ...
                'rebuiltMexQ2:SupplementIdentityMismatch');

            configureGpSupplement(fixture, g_gp, psi_raw_gp);
            lock = jsondecode(fileread(fixture.q2_lock));
            lock.supplement.source_id = 'wrong_source';
            writeJson(fixture.q2_lock, lock);
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root, ...
                struct('supplement_root', fixture.folder)), ...
                'rebuiltMexQ2:SupplementIdentityMismatch');

            configureGpSupplement(fixture, g_gp, psi_raw_gp);
            supplementPath = fullfile(fixture.folder, 'parent_gp_supplement.mat');
            data = load(supplementPath);
            order = [2 1 3];
            data.g_gp = data.g_gp(order, :);
            data.psi_raw_gp = data.psi_raw_gp(order, :);
            data.element_ids = data.element_ids(order);
            save(supplementPath, '-struct', 'data');
            lock = jsondecode(fileread(fixture.q2_lock));
            lock.supplement.sha256 = sha256File(supplementPath);
            writeJson(fixture.q2_lock, lock);
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root, ...
                struct('supplement_root', fixture.folder)), ...
                'rebuiltMexQ2:SupplementOrderingMismatch');
        end

        function testPublishesOnlyApplicableBlockerForPartialNativeEvidence(testCase)
            fixture = makeParentFixture(testCase, 'complete');
            cyclePath = fullfile(fixture.parent_root, 'cycle_0001.mat');
            data = load(cyclePath);
            data = rmfield(data, 'psi_active_elem');
            save(cyclePath, '-struct', 'data');
            parentLock = jsondecode(fileread(fixture.parent_lock));
            cycleKey = matlab.lang.makeValidName('cycle_0001.mat');
            parentLock.source_files.(cycleKey).sha256 = sha256File(cyclePath);
            parentLock.state_semantics.field_map = rmfield( ...
                parentLock.state_semantics.field_map, 'active_driver');
            writeJson(fixture.parent_lock, parentLock);
            q2Lock = jsondecode(fileread(fixture.q2_lock));
            q2Lock.parent.cycle1_sha256 = sha256File(cyclePath);
            q2Lock.parent_lock_sha256 = sha256File(fixture.parent_lock);
            writeJson(fixture.q2_lock, q2Lock);

            receipt = validate_q2_parent_fields_test_only(fixture.q2_lock, ...
                fixture.parent_lock, fixture.parent_root);

            verifyEqual(testCase, receipt.blockers, ...
                {'blocked_missing_parent_active_field'});
            verifyTrue(testCase, isfield(receipt.fields, 'damage_degradation'));
            verifyEqual(testCase, receipt.fields.damage_degradation.source, ...
                'native:g_elem');
        end

        function testRejectsChangedParentBytesAndOrdering(testCase)
            fixture = makeParentFixture(testCase, 'complete');
            cyclePath = fullfile(fixture.parent_root, 'cycle_0001.mat');
            data = load(cyclePath);
            data.d_elem(1) = data.d_elem(1) + 0.01;
            save(cyclePath, '-struct', 'data');
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:ParentProvenanceMismatch');

            fixture = makeParentFixture(testCase, 'complete');
            q2Lock = jsondecode(fileread(fixture.q2_lock));
            q2Lock.parent.mesh_ordering_sha256 = repmat('a', 1, 64);
            writeJson(fixture.q2_lock, q2Lock);
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:ParentIdentityMismatch');
        end

        function testBlockerReceiptIsHashBoundAndNoClobber(testCase)
            fixture = makeParentFixture(testCase, 'missing_g_active');
            blockerPath = fullfile(fixture.folder, 'Q2_PARENT_BLOCKER.json');
            config = struct('blocker_output_path', blockerPath);

            receipt = validate_q2_parent_fields_test_only(fixture.q2_lock, ...
                fixture.parent_lock, fixture.parent_root, config);

            verifyTrue(testCase, isfile(blockerPath));
            published = jsondecode(fileread(blockerPath));
            verifyEqual(testCase, published.q2_input_lock_sha256, ...
                receipt.q2_input_lock_sha256);
            verifyEqual(testCase, published.parent_lock_sha256, ...
                receipt.parent_lock_sha256);
            verifyEqual(testCase, published.parent_cycle1_sha256, ...
                receipt.parent_cycle1_sha256);
            verifyError(testCase, @() validate_q2_parent_fields_test_only( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root, config), ...
                'rebuiltMexQ2:OutputExists');
        end

        function testCurrentEightFileParentPublishesBothBlockers(testCase)
            handoff = fileparts(fileparts(mfilename('fullpath')));
            parentHandoff = fullfile(fileparts(handoff), ...
                'toy_to_road_independent_fem_20260731');
            parentRoot = 'C:/q4diag/toy-road-parent-20260729';
            folder = matlab.unittest.fixtures.TemporaryFolderFixture;
            testCase.applyFixture(folder);
            outputPath = fullfile(folder.Folder, 'CURRENT_PARENT_BLOCKER.json');

            receipt = validate_q2_parent_fields( ...
                fullfile(handoff, 'Q2_INPUT_LOCK.json'), ...
                fullfile(parentHandoff, 'PARENT_LOCK.json'), parentRoot, ...
                struct('blocker_output_path', outputPath));

            verifyEqual(testCase, receipt.status, 'blocked');
            verifyEqual(testCase, sort(receipt.blockers), sort({ ...
                'blocked_missing_parent_damage_degradation_field', ...
                'blocked_missing_parent_active_field'}));
            verifyTrue(testCase, isfile(outputPath));
        end

        function testProductionRejectsMutatedParentHashLock(testCase)
            fixture = mutatedProductionLock(testCase, 'parent_hash');
            verifyError(testCase, @() validate_q2_parent_fields( ...
                fixture.lock_path, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:UnsealedInputLock');
        end

        function testProductionRejectsCompleteSyntheticReadyLock(testCase)
            fixture = makeParentFixture(testCase, 'complete');
            verifyError(testCase, @() validate_q2_parent_fields( ...
                fixture.q2_lock, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:UnsealedInputLock');
        end

        function testProductionRejectsMutatedFieldMapLock(testCase)
            fixture = mutatedProductionLock(testCase, 'field_map');
            verifyError(testCase, @() validate_q2_parent_fields( ...
                fixture.lock_path, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:UnsealedInputLock');
        end

        function testProductionRejectsSupplementEnablementMutation(testCase)
            fixture = mutatedProductionLock(testCase, 'supplement_enablement');
            verifyError(testCase, @() validate_q2_parent_fields( ...
                fixture.lock_path, fixture.parent_lock, fixture.parent_root), ...
                'rebuiltMexQ2:UnsealedInputLock');
        end

        function testSealedProductionPathsDoNotReferenceTestOnlyEntry(testCase)
            handoff = fileparts(fileparts(mfilename('fullpath')));
            production = fileread(fullfile(handoff, ...
                'validate_q2_parent_fields.m'));
            familyLauncher = fileread(fullfile(fileparts(handoff), ...
                'toy_to_road_independent_fem_20260731', ...
                'launch_toy_road_case.ps1'));
            verifyEqual(testCase, count(production, ...
                'validate_q2_parent_fields_test_only'), 1);
            verifyFalse(testCase, contains(familyLauncher, ...
                'validate_q2_parent_fields_test_only'));
        end
    end
end

function fixture = mutatedProductionLock(testCase, mutation)
handoff = fileparts(fileparts(mfilename('fullpath')));
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
lock = jsondecode(fileread(fullfile(handoff, 'Q2_INPUT_LOCK.json')));
switch mutation
    case 'parent_hash'
        lock.parent_lock_sha256 = repmat('0', 1, 64);
    case 'field_map'
        lock.required_field_map.active_driver = 'f_alpha_elem';
    case 'supplement_enablement'
        lock.supplement.permitted = true;
    otherwise
        error('Unexpected fixture mutation.');
end

lockPath = fullfile(folder.Folder, 'Q2_INPUT_LOCK.json');
writeJson(lockPath, lock);
fixture = struct( ...
    'lock_path', lockPath, ...
    'parent_lock', fullfile(fileparts(handoff), ...
        'toy_to_road_independent_fem_20260731', 'PARENT_LOCK.json'), ...
    'parent_root', 'C:/q4diag/toy-road-parent-20260729');
end

function configureGpSupplement(fixture, g_gp, psi_raw_gp)
q2Lock = jsondecode(fileread(fixture.q2_lock));
supplementPath = fullfile(fixture.folder, 'parent_gp_supplement.mat');
element_ids = int64((1:size(g_gp, 1))');
parent_reference_id = q2Lock.parent.reference_id;
source_id = 'fixture_gp_export_v1';
parent_cycle1_sha256 = q2Lock.parent.cycle1_sha256;
mesh_ordering_sha256 = q2Lock.parent.mesh_ordering_sha256;
save(supplementPath, 'g_gp', 'psi_raw_gp', 'element_ids', ...
    'parent_reference_id', 'source_id', 'parent_cycle1_sha256', ...
    'mesh_ordering_sha256');
q2Lock.supplement = struct('permitted', true, ...
    'relative_path', 'parent_gp_supplement.mat', ...
    'sha256', sha256File(supplementPath), ...
    'parent_reference_id', parent_reference_id, ...
    'source_id', source_id, ...
    'parent_cycle1_sha256', parent_cycle1_sha256, ...
    'mesh_ordering_sha256', mesh_ordering_sha256, ...
    'element_ids_field', 'element_ids', ...
    'element_order_sha256', sha256Bytes(typecast(element_ids, 'uint8')), ...
    'num_gauss_points', size(g_gp, 2), ...
    'g_field', 'g_gp', 'raw_field', 'psi_raw_gp', ...
    'damage_degradation_semantics', 'mean_gp(g_gp)', ...
    'active_semantics', 'mean_gp(g_gp.*psi_raw_gp)');
writeJson(fixture.q2_lock, q2Lock);
end

function fixture = makeParentFixture(testCase, mode)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
parentRoot = fullfile(folder.Folder, ['parent_', char(java.util.UUID.randomUUID)]);
mkdir(parentRoot);

d_elem = [0; 0.2; 0.8];
alpha_bar_elem = [0; 1e-4; 2e-3];
f_alpha_elem = ones(3, 1);
psi_raw_elem = [0; 0.4; 1.2];
cyclePath = fullfile(parentRoot, 'cycle_0001.mat');
if strcmp(mode, 'complete')
    g_elem = [1; 0.64; 0.04];
    psi_active_elem = [0; 0.23; 0.031];
    save(cyclePath, 'd_elem', 'alpha_bar_elem', 'f_alpha_elem', ...
        'psi_raw_elem', 'g_elem', 'psi_active_elem');
else
    save(cyclePath, 'd_elem', 'alpha_bar_elem', 'f_alpha_elem', ...
        'psi_raw_elem');
end

sourceFiles = makeEightFiles(parentRoot, cyclePath);
meshHash = sha256Bytes(typecast(int64([1 2 3]), 'uint8'));
fieldMap = struct('damage', 'd_elem', 'history', 'alpha_bar_elem', ...
    'fatigue_degradation', 'f_alpha_elem', 'raw_driver', 'psi_raw_elem');
if strcmp(mode, 'complete')
    fieldMap.damage_degradation = 'g_elem';
    fieldMap.active_driver = 'psi_active_elem';
end
parentLock = struct( ...
    'schema_version', 'fixture_parent_lock_v1', ...
    'parent_reference_id', 'fixture_parent', ...
    'mesh', struct('num_elem', 3, 'content_sha256', meshHash, ...
    'task4_parent_mesh_sha256', meshHash, ...
    'task4_parent_mesh_sha256_semantics', ...
    'sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1'), ...
    'state_semantics_id', 'cycle_peak_coherent_v1', ...
    'state_semantics', struct('peak_substep_ordinal', 4, ...
        'field_map', fieldMap), ...
    'source_files', sourceFiles);
parentLockPath = fullfile(folder.Folder, 'PARENT_LOCK.json');
writeJson(parentLockPath, parentLock);

q2Lock = struct( ...
    'schema_version', 'rebuilt_initial_mex_q2_input_lock_v1', ...
    'parent_lock_sha256', sha256File(parentLockPath), ...
    'parent', struct('reference_id', 'fixture_parent', 'num_elem', 3, ...
        'mesh_ordering_sha256', meshHash, 'cycle', 1, ...
        'cycle1_relative_path', 'cycle_0001.mat', ...
        'cycle1_sha256', sha256File(cyclePath)), ...
    'required_field_map', struct('damage', 'd_elem', ...
        'history', 'alpha_bar_elem', ...
        'fatigue_degradation', 'f_alpha_elem', ...
        'raw_driver_aliases', {{'psi_raw_elem', 'psi_elem'}}, ...
        'damage_degradation', 'g_elem', ...
        'active_driver', 'psi_active_elem'), ...
    'negative_tolerance', 1e-14, ...
    'supplement', struct('permitted', true, 'required_semantics', ...
        'mean_gp(g_gp.*psi_raw_gp)'), ...
    'prohibited_substitutes', {{'f_alpha_elem_as_active', ...
        '(1-d_elem)^2_as_g_elem', 'product_of_element_means_as_active'}});
q2LockPath = fullfile(folder.Folder, 'Q2_INPUT_LOCK.json');
writeJson(q2LockPath, q2Lock);

fixture = struct('folder', folder.Folder, 'parent_root', parentRoot, ...
    'parent_lock', parentLockPath, 'q2_lock', q2LockPath);
end

function sourceFiles = makeEightFiles(parentRoot, cyclePath)
names = {'initial_state_metadata.mat', 'state0_analysis.mat', ...
    'pre_run_lock.mat', 'cycle_0001.mat', 'cycle_0083.mat', ...
    'cycle_0086.mat', 'MANIFEST.csv', 'peak_load_c1.vtk'};
sourceFiles = struct;
for index = 1:numel(names)
    name = names{index};
    path = fullfile(parentRoot, name);
    if ~strcmp(path, cyclePath)
        fileId = fopen(path, 'wb');
        fwrite(fileId, uint8(name), 'uint8');
        fclose(fileId);
    end
    key = matlab.lang.makeValidName(name);
    sourceFiles.(key) = struct('relative_path', name, ...
        'sha256', sha256File(path));
end
end

function rebindParentLock(q2LockPath, parentLockPath)
q2Lock = jsondecode(fileread(q2LockPath));
q2Lock.parent_lock_sha256 = sha256File(parentLockPath);
writeJson(q2LockPath, q2Lock);
end

function writeJson(path, value)
fileId = fopen(path, 'w');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, jsonencode(value, PrettyPrint=true), 'char');
end

function digest = sha256File(path)
fileId = fopen(path, 'rb');
cleanup = onCleanup(@() fclose(fileId));
digest = sha256Bytes(fread(fileId, Inf, '*uint8'));
end

function digest = sha256Bytes(bytes)
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(uint8(bytes));
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end
