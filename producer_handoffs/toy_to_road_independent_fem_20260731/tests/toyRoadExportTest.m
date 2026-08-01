function tests = toyRoadExportTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
testCase.addTeardown(@() rmpath(handoffDir()));
end

function testActiveDriverUsesGpProductBeforeMean(testCase)
gpG = [1 0 1 0; 0.25 0.25 0.25 0.25];
gpRaw = [2 100 4 100; 8 4 2 2];
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>

state = export_toy_road_peak_state(syntheticInput(gpG, gpRaw), outputRoot);

verifyEqual(testCase, state.psi_active_elem, mean(gpG .* gpRaw, 2), ...
    'AbsTol', 1e-14);
verifyNotEqual(testCase, state.psi_active_elem, ...
    mean(gpG, 2) .* mean(gpRaw, 2));
end

function testExportDeclaresNodalElementAndLatentSemantics(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputRoot);

verifySize(testCase, state.u, [8 1]);
verifySize(testCase, state.v, [8 1]);
verifySize(testCase, state.d_node, [8 1]);
verifySize(testCase, state.d_elem, [2 1]);
verifySize(testCase, state.alpha_bar_elem, [2 1]);
verifySize(testCase, state.f_alpha_elem, [2 1]);
verifySize(testCase, state.psi_raw_elem, [2 1]);
verifySize(testCase, state.g_elem, [2 1]);
verifySize(testCase, state.psi_active_elem, [2 1]);
verifySize(testCase, state.strain_elem, [2 3]);
verifyEqual(testCase, state.field_semantics.u, "nodal");
verifyEqual(testCase, state.field_semantics.d_elem, "element");
verifyEqual(testCase, state.field_semantics.psi_active_elem, ...
    "element_latent_fem_truth");
verifyEqual(testCase, state.field_semantics.strain_energy_raw_elem, ...
    "element_latent_fem_truth");
verifyEqual(testCase, state.field_semantics.strain_energy_active_elem, ...
    "element_latent_fem_truth");
verifyEqual(testCase, state.field_semantics.crack_tip_diagnostics, ...
    "derived_crack_diagnostic");
verifyEqual(testCase, state.field_semantics.connected_right_boundary_diagnostics, ...
    "derived_crack_diagnostic");
verifyEqual(testCase, state.state_semantics_id, "cycle_peak_coherent_v1");
verifyTrue(testCase, allFiniteNumericFields(state));
end

function testNativeQ4StrainAndReactionResultantsAreExported(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputRoot);

verifyEqual(testCase, state.strain_elem, repmat([2 4 2], 2, 1), ...
    'AbsTol', 1e-13);
verifySize(testCase, state.reaction_vector, [16 1]);
verifyEqual(testCase, state.top_node_ids, [3 4 7 8]);
verifyEqual(testCase, state.bottom_node_ids, [1 2 5 6]);
verifyEqual(testCase, state.reaction_top_xy, [22 62]);
verifyEqual(testCase, state.reaction_bottom_xy, [14 54]);
verifyEqual(testCase, state.reaction_top_resultant, hypot(22, 62), ...
    'AbsTol', 1e-14);
verifyEqual(testCase, state.reaction_bottom_resultant, hypot(14, 54), ...
    'AbsTol', 1e-14);
end

function testCrackMasksUseDeclaredElementThresholds(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
damageGp = [0.60 * ones(1, 4); 0.96 * ones(1, 4)];
input = syntheticInput((1 - damageGp) .^ 2, ones(2, 4));

state = export_toy_road_peak_state(input, outputRoot);

verifyEqual(testCase, state.crack_thresholds, [0.50 0.75 0.90 0.95]);
verifyEqual(testCase, state.crack_mask_elem, ...
    logical([1 0 0 0; 1 1 1 1]));
end

function testCycleMetadataAndMeshIdentityAreCoherent(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputRoot);

verifyEqual(testCase, state.cycle, 2);
verifyEqual(testCase, state.Umax_N, 0.12, 'AbsTol', 1e-14);
verifyEqual(testCase, state.peak_substep_ordinal, 4);
verifyEqual(testCase, state.raw_step_1_based, 9);
verifyEqual(testCase, state.branch, "loading_peak");
verifyEqual(testCase, state.cycle_index.file, "states/cycle_0002.mat");
verifyEqual(testCase, strlength(state.mesh_sha256), 64);
verifyEqual(testCase, state.cycle_index.mesh_sha256, state.mesh_sha256);
verifyEqual(testCase, state.mesh_ordering_id, "q4_node_connectivity_1_based_v1");
verifyEqual(testCase, state.state_ordering_id, "component_blocked_u_then_v_v1");
end

function testCanonicalMeshHasherMatchesExporterAndGeometryPayload(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputRoot);
canonicalHash = toy_road_mesh_sha256(input.node_coords, input.connectivity);
driverText = string(fileread(fullfile(handoffDir(), 'main_toy_to_road_case.m')));

verifyEqual(testCase, state.mesh_sha256, canonicalHash);
verifyEqual(testCase, state.cycle_index.mesh_sha256, canonicalHash);
verifyTrue(testCase, contains(driverText, ...
    "'mesh_sha256', toy_road_mesh_sha256(coords, connectivity)"));
end

function testExporterPublishesCompleteMatV73ShardWithoutTemporaryLink(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputRoot);

verifyTrue(testCase, isfile(outputPath));
hdf5Info = h5info(outputPath);
verifyNotEmpty(testCase, hdf5Info);
saved = load(outputPath, 'psi_active_elem', 'cycle', 'mesh_sha256', ...
    'cycle_index');
verifyEqual(testCase, saved.psi_active_elem, state.psi_active_elem);
verifyEqual(testCase, saved.cycle, state.cycle);
verifyEqual(testCase, string(saved.mesh_sha256), state.mesh_sha256);
verifyEqual(testCase, string(saved.cycle_index.file), ...
    "states/cycle_0002.mat");
files = dir(fullfile(outputRoot, 'states'));
files = files(~[files.isdir]);
verifyEqual(testCase, string({files.name}), "cycle_0002.mat");
verifyEmpty(testCase, dir(fullfile(outputRoot, 'states', '*.tmp.mat')));
verifyFalse(testCase, isfile([outputPath '.publish.lock']));
end

function testNoClobberPublisherUsesHardLinkWithoutCopyOrMove(testCase)
publisherPath = fullfile(handoffDir(), ...
    'publish_toy_road_state_no_clobber.m');
source = fileread(publisherPath);

verifyNotEmpty(testCase, regexp(source, ...
    'java\.nio\.file\.Files\.createLink', 'once'));
verifyEmpty(testCase, regexp(source, ...
    'java\.nio\.file\.Files\.move', 'once'));
verifyEmpty(testCase, regexp(source, ...
    'java\.nio\.file\.Files\.copy', 'once'));
verifyEmpty(testCase, regexp(source, 'REPLACE_EXISTING', 'once'));
end

function testTargetAppearingAtPublicationIsPreservedByteForByte(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
state = struct('sentinel', 1);
sentinelBytes = uint8([0 1 2 13 10 127 128 254 255]);

verifyError(testCase, ...
    @() publish_toy_road_state_no_clobber(state, outputPath, ...
    @(tempPath, targetPath) createRacingTargetThenLink( ...
    tempPath, targetPath, sentinelBytes)), ...
    "toyRoad:StatePublishConflict");
verifyEqual(testCase, readBytes(outputPath), sentinelBytes);
verifyNoTemporaryPublicationArtifacts(testCase, outputPath);
end

function testUnsupportedHardLinkLeavesNoAcceptedTargetOrArtifacts(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
state = struct('sentinel', 1);

verifyError(testCase, ...
    @() publish_toy_road_state_no_clobber( ...
    state, outputPath, @failUnsupportedHardLink), ...
    "toyRoad:HardLinkNotSupported");
verifyFalse(testCase, isfile(outputPath));
verifyNoTemporaryPublicationArtifacts(testCase, outputPath);
end

function testFailedHardLinkLeavesNoAcceptedTargetOrArtifacts(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
state = struct('sentinel', 1);

verifyError(testCase, ...
    @() publish_toy_road_state_no_clobber( ...
    state, outputPath, @failHardLinkIo), ...
    "toyRoad:StateWriteFailed");
verifyFalse(testCase, isfile(outputPath));
verifyNoTemporaryPublicationArtifacts(testCase, outputPath);
end

function testExporterRejectsMismatchedFileDestination(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
mismatchedPath = fullfile(outputRoot, 'cycle_0002.mat');
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

verifyError(testCase, ...
    @() export_toy_road_peak_state(input, mismatchedPath), ...
    "toyRoad:InvalidPeakStateOutput");
verifyFalse(testCase, isfile(mismatchedPath));
verifyFalse(testCase, isfolder(fullfile(mismatchedPath, 'states')));
end

function testExporterRejectsExistingCanonicalOutputWithoutChangingIt(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
statesDir = fileparts(outputPath);
mkdir(statesDir);
writeText(outputPath, 'existing-state-sentinel');
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

verifyError(testCase, ...
    @() export_toy_road_peak_state(input, outputRoot), ...
    "toyRoad:StateOutputExists");
verifyEqual(testCase, fileread(outputPath), 'existing-state-sentinel');
verifyEqual(testCase, stateDirectoryNames(statesDir), "cycle_0002.mat");
end

function testExporterRejectsPublishLockConflictAndLeavesNoTemporaryFile(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
statesDir = fileparts(outputPath);
mkdir(statesDir);
lockPath = [outputPath '.publish.lock'];
writeText(lockPath, 'publisher-one');
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

verifyError(testCase, ...
    @() export_toy_road_peak_state(input, outputRoot), ...
    "toyRoad:StatePublishConflict");
verifyFalse(testCase, isfile(outputPath));
verifyEqual(testCase, fileread(lockPath), 'publisher-one');
verifyEqual(testCase, stateDirectoryNames(statesDir), ...
    "cycle_0002.mat.publish.lock");
end

function testValidatorReportsRangesAndActiveIdentity(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);

metrics = validate_toy_road_state(state);

verifyTrue(testCase, metrics.is_valid);
verifyEqual(testCase, metrics.cycle, 2);
verifyEqual(testCase, metrics.raw_step_1_based, 9);
verifyEqual(testCase, metrics.mesh_sha256, state.mesh_sha256);
verifyEqual(testCase, metrics.damage_min, 0.5, 'AbsTol', 1e-14);
verifyEqual(testCase, metrics.damage_max, 0.5, 'AbsTol', 1e-14);
verifyLessThanOrEqual(testCase, metrics.active_identity_max_abs_error, 1e-14);
end

function testValidatorRejectsWithoutClippingOutOfRangeFields(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.d_node(1) = -0.01;
state.f_alpha_elem(1) = 1.01;
before = state;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
verifyEqual(testCase, state, before);
end

function testValidatorRejectsChangedActiveDriver(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.psi_active_elem(1) = state.psi_active_elem(1) + 0.1;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorIndependentlyRejectsFAlphaElementRangeCorruption(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.f_alpha_elem(1) = 1.01;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorIndependentlyRejectsNaNAndInf(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
nanState = state;
nanState.psi_raw_elem(1) = NaN;
infState = state;
infState.reaction_top_resultant = Inf;

verifyError(testCase, @() validate_toy_road_state(nanState), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(infState), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRejectsMeshHashTampering(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.mesh_sha256 = repmat("0", 1, 1);

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRejectsReactionVectorAndComponentTampering(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
badShape = state;
badShape.reaction_top_xy = badShape.reaction_top_xy.';
badVector = state;
badVector.reaction_vector = [(1:8)'; (11:18)'];
badVector.reaction_vector(3) = badVector.reaction_vector(3) + 1;

verifyError(testCase, @() validate_toy_road_state(badShape), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badVector), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRejectsReactionResultantTampering(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.reaction_bottom_resultant = state.reaction_bottom_resultant + 1;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRejectsSemanticAndOrderingTampering(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
badSemantics = state;
badSemantics.field_semantics.psi_active_elem = "road_sensor";
badMeshOrdering = state;
badMeshOrdering.mesh_ordering_id = "unknown_mesh_order";
badStateOrdering = state;
badStateOrdering.state_ordering_id = "interleaved_uv";
badIndexPath = state;
badIndexPath.cycle_index.file = "cycle_0002.mat";

verifyError(testCase, @() validate_toy_road_state(badSemantics), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badMeshOrdering), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badStateOrdering), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badIndexPath), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRequiresAndRecomputesStrainEnergyAliases(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
missingRaw = rmfield(state, 'strain_energy_raw_elem');
missingActive = rmfield(state, 'strain_energy_active_elem');
badRaw = state;
badRaw.strain_energy_raw_elem(1) = badRaw.strain_energy_raw_elem(1) + 0.1;
badActive = state;
badActive.strain_energy_active_elem(1) = ...
    badActive.strain_energy_active_elem(1) + 0.1;

verifyError(testCase, @() validate_toy_road_state(missingRaw), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(missingActive), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badRaw), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badActive), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRecomputesNativeQ4StrainFromMeshAndDisplacement(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.strain_gp(:, :, 1) = state.strain_gp(:, :, 1) + 0.25;
state.strain_elem = reshape(mean(state.strain_gp, 2), 2, 3);

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRequiresAndRecomputesCrackTipDiagnostics(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = exportCrackedState(outputRoot);
missing = rmfield(state, 'crack_tip_diagnostics');
badFound = state;
badFound.crack_tip_diagnostics.found = false;
badNode = state;
badNode.crack_tip_diagnostics.node_id = ...
    badNode.crack_tip_diagnostics.node_id + 1;
badCoordinates = state;
badCoordinates.crack_tip_diagnostics.coordinates(1) = ...
    badCoordinates.crack_tip_diagnostics.coordinates(1) + 0.1;
badThreshold = state;
badThreshold.crack_tip_diagnostics.threshold = 0.90;

verifyError(testCase, @() validate_toy_road_state(missing), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badFound), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badNode), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badCoordinates), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badThreshold), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRequiresAndRecomputesRightBoundaryDiagnostics(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = exportCrackedState(outputRoot);
missing = rmfield(state, 'connected_right_boundary_diagnostics');
badHit = state;
badHit.connected_right_boundary_diagnostics.hit = false;
badSize = state;
badSize.connected_right_boundary_diagnostics.connected_component_size = 3;
badCandidates = state;
badCandidates.connected_right_boundary_diagnostics.candidate_node_ids = [5; 6; 7];
badComponent = state;
badComponent.connected_right_boundary_diagnostics.connected_component_node_ids = [5; 6; 7];
badContract = state;
badContract.connected_right_boundary_diagnostics.x_min = 0.49;

verifyError(testCase, @() validate_toy_road_state(missing), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badHit), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badSize), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badCandidates), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badComponent), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badContract), ...
    "toyRoad:StateValidationFailed");
end

function testStandaloneValidatorRequiresScalarNonnegativeUmax(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
negative = state;
negative.Umax_N = -0.12;
negative.cycle_index.Umax_N = -0.12;
badShape = state;
badShape.Umax_N = [0.12 0.12];
badShape.cycle_index.Umax_N = [0.12 0.12];

verifyError(testCase, @() validate_toy_road_state(negative), ...
    "toyRoad:StateValidationFailed");
verifyError(testCase, @() validate_toy_road_state(badShape), ...
    "toyRoad:StateValidationFailed");
end

function testPersistedV73CorruptionClassesAreRejected(testCase)
[outputRoot, cleanup, outputPath] = freshOutputRoot(); %#ok<ASGLU>
exportCrackedState(outputRoot);
hdf5Info = h5info(outputPath);
verifyNotEmpty(testCase, hdf5Info);
validState = load(outputPath);

badState = validState;
badState.reaction_vector(3) = badState.reaction_vector(3) + 1;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.reaction_top_resultant = badState.reaction_top_resultant + 1;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.mesh_sha256 = repmat("0", 1, 1);
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.strain_energy_active_elem(1) = ...
    badState.strain_energy_active_elem(1) + 0.1;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.crack_tip_diagnostics.node_id = ...
    badState.crack_tip_diagnostics.node_id + 1;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.connected_right_boundary_diagnostics.hit = false;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.Umax_N = -0.12;
badState.cycle_index.Umax_N = -0.12;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.f_alpha_elem(1) = 1.01;
verifyPersistedStateRejected(testCase, outputPath, badState);

badState = validState;
badState.psi_raw_elem(1) = NaN;
verifyPersistedStateRejected(testCase, outputPath, badState);
end

function testValidatorRejectsGpDamageThatIsNotNativeQ4Interpolation(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.d_gp(:) = 0.25;
state.d_elem = mean(state.d_gp, 2);
state.g_gp = (1 - state.d_gp) .^ 2;
state.g_elem = mean(state.g_gp, 2);
state.psi_active_gp = state.g_gp .* state.psi_raw_gp;
state.psi_active_elem = mean(state.psi_active_gp, 2);
state.crack_mask_elem = state.d_elem >= state.crack_thresholds;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRejectsDegradationThatIsNotDerivedFromDamage(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
state.g_gp(:) = 0.5;
state.g_elem = mean(state.g_gp, 2);
state.psi_active_gp = state.g_gp .* state.psi_raw_gp;
state.psi_active_elem = mean(state.psi_active_gp, 2);

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorEnforcesRawStepMappingAndConsecutiveMetadata(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputRoot);
previous = struct('cycle', 1, 'raw_step_1_based', 4, ...
    'mesh_sha256', state.mesh_sha256, 'n_substeps', 5);

metrics = validate_toy_road_state(state, previous);
verifyTrue(testCase, metrics.is_valid);

badRawStep = state;
badRawStep.raw_step_1_based = 10;
verifyError(testCase, @() validate_toy_road_state(badRawStep, previous), ...
    "toyRoad:StateValidationFailed");

missingCycle = state;
missingCycle.cycle = 3;
missingCycle.raw_step_1_based = 14;
verifyError(testCase, @() validate_toy_road_state(missingCycle, previous), ...
    "toyRoad:StateValidationFailed");
end

function input = syntheticInput(gpG, gpRaw)
nodeCoords = [0 0; 1 0; 1 1; 0 1; 2 0; 3 0; 3 1; 2 1];
connectivity = [1 2 3 4; 5 6 7 8];
quadraturePoints = [-1 -1; 1 -1; 1 1; -1 1];
damageGp = 1 - sqrt(gpG);

u = 2 * nodeCoords(:, 1) + 3 * nodeCoords(:, 2);
v = -nodeCoords(:, 1) + 4 * nodeCoords(:, 2);
historyVars = zeros(2, 4, 4);
historyVars(:, :, 2) = [0.1 0.2 0.3 0.4; 0.2 0.3 0.4 0.5];
historyVars(:, :, 4) = [0.9 0.8 0.7 0.6; 0.8 0.7 0.6 0.5];

input = struct();
input.displ = [u; v];
input.p_field = reshape(damageGp.', [], 1);
input.history_vars = historyVars;
input.psi_raw_gp = gpRaw;
input.node_coords = nodeCoords;
input.connectivity = connectivity;
input.quadrature_points = quadraturePoints;
input.quadrature_weights = ones(4, 1);
input.reaction_vector = [(1:8)'; (11:18)'];
input.top_node_ids = [3 4 7 8];
input.bottom_node_ids = [1 2 5 6];
input.metadata = struct( ...
    'cycle', 2, ...
    'Umax_N', 0.12, ...
    'peak_substep_ordinal', 4, ...
    'n_substeps', 5, ...
    'raw_step_1_based', 9, ...
    'branch', "loading_peak", ...
    'phase', "cycle_peak", ...
    'state_semantics_id', "cycle_peak_coherent_v1", ...
    'mesh_ordering_id', "q4_node_connectivity_1_based_v1", ...
    'state_ordering_id', "component_blocked_u_then_v_v1");
input.validation_tolerances = struct( ...
    'range', 1e-12, ...
    'active_identity', 1e-12, ...
    'irreversibility', 1e-12);
end

function state = exportCrackedState(outputRoot)
damageGp = [0.60 * ones(1, 4); 0.96 * ones(1, 4)];
state = export_toy_road_peak_state( ...
    syntheticInput((1 - damageGp) .^ 2, ones(2, 4)), outputRoot);
end

function verifyPersistedStateRejected(testCase, outputPath, state)
save(outputPath, '-struct', 'state', '-v7.3');
hdf5Info = h5info(outputPath);
verifyNotEmpty(testCase, hdf5Info);
reloadedState = load(outputPath);
verifyError(testCase, @() validate_toy_road_state(reloadedState), ...
    "toyRoad:StateValidationFailed");
end

function createRacingTargetThenLink(tempPath, targetPath, sentinelBytes)
writeBytes(targetPath, sentinelBytes);
java.nio.file.Files.createLink(java.io.File(targetPath).toPath(), ...
    java.io.File(tempPath).toPath());
end

function failUnsupportedHardLink(~, ~)
error('toyRoadTest:UnsupportedOperationException', ...
    'java.lang.UnsupportedOperationException: injected hard-link failure');
end

function failHardLinkIo(~, ~)
error('toyRoadTest:FileSystemException', ...
    'java.nio.file.FileSystemException: injected hard-link I/O failure');
end

function value = allFiniteNumericFields(state)
value = true;
names = fieldnames(state);
for index = 1:numel(names)
    fieldValue = state.(names{index});
    if isnumeric(fieldValue)
        value = value && all(isfinite(fieldValue), 'all');
    end
end
end

function [outputRoot, cleanup, outputPath] = freshOutputRoot()
outputRoot = tempname;
mkdir(outputRoot);
cleanup = onCleanup(@() rmdir(outputRoot, 's'));
outputPath = fullfile(outputRoot, 'states', 'cycle_0002.mat');
end

function writeText(path, value)
fileId = fopen(path, 'w');
if fileId < 0
    error('toyRoadTest:FixtureWriteFailed', 'Cannot write fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, value, 'char');
end

function writeBytes(path, value)
fileId = fopen(path, 'wb');
if fileId < 0
    error('toyRoadTest:FixtureWriteFailed', 'Cannot write fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, value, 'uint8');
end

function value = readBytes(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadTest:FixtureReadFailed', 'Cannot read fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
value = fread(fileId, Inf, '*uint8').';
end

function verifyNoTemporaryPublicationArtifacts(testCase, outputPath)
statesDir = fileparts(outputPath);
verifyEmpty(testCase, dir(fullfile(statesDir, '*.tmp.mat')));
verifyFalse(testCase, isfile([outputPath '.publish.lock']));
end

function names = stateDirectoryNames(path)
files = dir(path);
files = files(~[files.isdir]);
names = sort(string({files.name}));
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
