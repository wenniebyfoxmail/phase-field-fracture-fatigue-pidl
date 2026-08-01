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
outputPath = tempname;
cleanup = onCleanup(@() deleteIfPresent(outputPath));

state = export_toy_road_peak_state(syntheticInput(gpG, gpRaw), outputPath);

verifyEqual(testCase, state.psi_active_elem, mean(gpG .* gpRaw, 2), ...
    'AbsTol', 1e-14);
verifyNotEqual(testCase, state.psi_active_elem, ...
    mean(gpG, 2) .* mean(gpRaw, 2));
end

function testExportDeclaresNodalElementAndLatentSemantics(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputPath);

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
verifyEqual(testCase, state.state_semantics_id, "cycle_peak_coherent_v1");
verifyTrue(testCase, allFiniteNumericFields(state));
end

function testNativeQ4StrainAndReactionResultantsAreExported(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputPath);

verifyEqual(testCase, state.strain_elem, repmat([2 4 2], 2, 1), ...
    'AbsTol', 1e-13);
verifyEqual(testCase, state.reaction_top_xy, [22 62]);
verifyEqual(testCase, state.reaction_bottom_xy, [14 54]);
verifyEqual(testCase, state.reaction_top_resultant, hypot(22, 62), ...
    'AbsTol', 1e-14);
verifyEqual(testCase, state.reaction_bottom_resultant, hypot(14, 54), ...
    'AbsTol', 1e-14);
end

function testCrackMasksUseDeclaredElementThresholds(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
damageGp = [0.60 * ones(1, 4); 0.96 * ones(1, 4)];
input = syntheticInput((1 - damageGp) .^ 2, ones(2, 4));

state = export_toy_road_peak_state(input, outputPath);

verifyEqual(testCase, state.crack_thresholds, [0.50 0.75 0.90 0.95]);
verifyEqual(testCase, state.crack_mask_elem, ...
    logical([1 0 0 0; 1 1 1 1]));
end

function testCycleMetadataAndMeshIdentityAreCoherent(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputPath);

verifyEqual(testCase, state.cycle, 2);
verifyEqual(testCase, state.Umax_N, 0.12, 'AbsTol', 1e-14);
verifyEqual(testCase, state.peak_substep_ordinal, 4);
verifyEqual(testCase, state.raw_step_1_based, 9);
verifyEqual(testCase, state.branch, "loading_peak");
verifyEqual(testCase, state.cycle_index_row.state_file, "cycle_0002.mat");
verifyEqual(testCase, strlength(state.mesh_sha256), 64);
verifyEqual(testCase, state.cycle_index_row.mesh_sha256, state.mesh_sha256);
verifyEqual(testCase, state.mesh_ordering_id, "q4_node_connectivity_1_based_v1");
verifyEqual(testCase, state.state_ordering_id, "component_blocked_u_then_v_v1");
end

function testExporterWritesAtomicMatV73Shard(testCase)
[outputPath, cleanup, outputDir] = freshOutputPath(); %#ok<ASGLU>
input = syntheticInput(0.25 * ones(2, 4), ones(2, 4));

state = export_toy_road_peak_state(input, outputPath);

verifyTrue(testCase, isfile(outputPath));
hdf5Info = h5info(outputPath);
verifyNotEmpty(testCase, hdf5Info);
saved = load(outputPath, 'psi_active_elem', 'cycle', 'mesh_sha256');
verifyEqual(testCase, saved.psi_active_elem, state.psi_active_elem);
verifyEqual(testCase, saved.cycle, state.cycle);
verifyEqual(testCase, string(saved.mesh_sha256), state.mesh_sha256);
files = dir(outputDir);
files = files(~[files.isdir]);
verifyEqual(testCase, string({files.name}), "cycle_0002.mat");
end

function testValidatorReportsRangesAndActiveIdentity(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputPath);

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
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputPath);
state.d_node(1) = -0.01;
state.f_alpha_elem(1) = 1.01;
before = state;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
verifyEqual(testCase, state, before);
end

function testValidatorRejectsChangedActiveDriver(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputPath);
state.psi_active_elem(1) = state.psi_active_elem(1) + 0.1;

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorRejectsGpDamageThatIsNotNativeQ4Interpolation(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputPath);
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
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputPath);
state.g_gp(:) = 0.5;
state.g_elem = mean(state.g_gp, 2);
state.psi_active_gp = state.g_gp .* state.psi_raw_gp;
state.psi_active_elem = mean(state.psi_active_gp, 2);

verifyError(testCase, @() validate_toy_road_state(state), ...
    "toyRoad:StateValidationFailed");
end

function testValidatorEnforcesRawStepMappingAndConsecutiveMetadata(testCase)
[outputPath, cleanup] = freshOutputPath(); %#ok<ASGLU>
state = export_toy_road_peak_state( ...
    syntheticInput(0.25 * ones(2, 4), ones(2, 4)), outputPath);
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

function [outputPath, cleanup, outputDir] = freshOutputPath()
outputDir = tempname;
mkdir(outputDir);
cleanup = onCleanup(@() rmdir(outputDir, 's'));
outputPath = fullfile(outputDir, 'cycle_0002.mat');
end

function deleteIfPresent(path)
if isfile(path)
    delete(path);
end
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
