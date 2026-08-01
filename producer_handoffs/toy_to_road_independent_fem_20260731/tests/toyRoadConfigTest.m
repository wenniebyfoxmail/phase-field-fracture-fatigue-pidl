function tests = toyRoadConfigTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(lockDir());
testCase.addTeardown(@() rmpath(lockDir()));
end

function testT3AmplitudeChangesOnlyAtLockedBoundaries(testCase)
cfg = build_toy_road_case_config("T3_loading_history", lockDir());
verifyEqual(testCase, cfg.umax_for_cycle([1 30 31 60 61 150]), ...
    [0.108 0.108 0.126 0.126 0.120 0.120], 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.n_step, 5);
verifyEqual(testCase, cfg.censor_cap, 150);
end

function testT1UsesTheLockedInitialDefect(testCase)
cfg = build_toy_road_case_config("T1_initial_defect", lockDir());
verifyEqual(testCase, cfg.initial_defect.tip, [0.125 0.0], 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.initial_defect.a0_over_L, 0.625, 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.physics.Gc, 0.01, 'AbsTol', 1e-14);
end

function testT2UsesTheLockedMaterialState(testCase)
cfg = build_toy_road_case_config("T2_material_state", lockDir());
verifyEqual(testCase, cfg.physics.Gc, 0.008, 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.Pi_ratio, 0.8, 'AbsTol', 1e-14);
end

function testUnknownCaseIdIsRejected(testCase)
verifyError(testCase, ...
    @() build_toy_road_case_config("unknown", lockDir()), ...
    "toyRoad:InvalidInputLock");
end

function testASecondChangedAxisIsRejected(testCase)
tempDir = tempname;
mkdir(tempDir);
cleanup = onCleanup(@() rmdir(tempDir, 's'));
copyRequiredLocks(lockDir(), tempDir);

caseLockPath = fullfile(tempDir, 'T1_INPUT_LOCK.json');
caseLock = jsondecode(fileread(caseLockPath));
caseLock.changed_parent_fields = {'initial_defect', 'material_state'};
writeJson(caseLockPath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testMismatchedParentHashIsRejected(testCase)
tempDir = tempname;
mkdir(tempDir);
cleanup = onCleanup(@() rmdir(tempDir, 's'));
copyRequiredLocks(lockDir(), tempDir);

caseLockPath = fullfile(tempDir, 'T1_INPUT_LOCK.json');
caseLock = jsondecode(fileread(caseLockPath));
caseLock.parent_lock_sha256 = repmat('0', 1, 64);
writeJson(caseLockPath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testInvalidCyclesAreRejected(testCase)
cfg = build_toy_road_case_config("T3_loading_history", lockDir());
verifyError(testCase, @() cfg.umax_for_cycle(0), "toyRoad:InvalidCycle");
verifyError(testCase, @() cfg.umax_for_cycle(1.5), "toyRoad:InvalidCycle");
verifyError(testCase, @() cfg.umax_for_cycle(151), "toyRoad:InvalidCycle");
end

function testFamilyGeometryBaselineIsValidated(testCase)
[tempDir, cleanup] = copiedLockDir();
familyPath = fullfile(tempDir, 'FAMILY_INPUT_LOCK.json');
family = jsondecode(fileread(familyPath));
family.axis_baselines.initial_defect.tip = [0.1; 0.0];
writeJson(familyPath, family);

casePath = fullfile(tempDir, 'T1_INPUT_LOCK.json');
caseLock = jsondecode(fileread(casePath));
caseLock.parent_candidate_diff.parent.initial_defect.tip = [0.1; 0.0];
writeJson(casePath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testFamilyMaterialGcBaselineIsValidated(testCase)
[tempDir, cleanup] = copiedLockDir();
familyPath = fullfile(tempDir, 'FAMILY_INPUT_LOCK.json');
family = jsondecode(fileread(familyPath));
family.axis_baselines.material_state.Gc = 0.009;
writeJson(familyPath, family);

casePath = fullfile(tempDir, 'T2_INPUT_LOCK.json');
caseLock = jsondecode(fileread(casePath));
caseLock.parent_candidate_diff.parent.material_state.Gc = 0.009;
writeJson(casePath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T2_material_state", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testFamilyPiBaselineIsValidated(testCase)
[tempDir, cleanup] = copiedLockDir();
familyPath = fullfile(tempDir, 'FAMILY_INPUT_LOCK.json');
family = jsondecode(fileread(familyPath));
family.axis_baselines.material_state.Pi_ratio = 0.9;
writeJson(familyPath, family);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testFamilyLoadingBaselineIsValidated(testCase)
[tempDir, cleanup] = copiedLockDir();
familyPath = fullfile(tempDir, 'FAMILY_INPUT_LOCK.json');
family = jsondecode(fileread(familyPath));
family.axis_baselines.loading_history.blocks = [1 150 0.11];
writeJson(familyPath, family);

casePath = fullfile(tempDir, 'T3_INPUT_LOCK.json');
caseLock = jsondecode(fileread(casePath));
caseLock.parent_candidate_diff.parent.loading_history.blocks = [1 150 0.11];
writeJson(casePath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T3_loading_history", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testAdditionalCandidateAxisIsRejected(testCase)
[tempDir, cleanup] = copiedLockDir();
casePath = fullfile(tempDir, 'T1_INPUT_LOCK.json');
caseLock = jsondecode(fileread(casePath));
caseLock.candidate.material_state = struct('Gc', 0.008, 'Pi_ratio', 0.8);
caseLock.parent_candidate_diff.candidate = caseLock.candidate;
writeJson(casePath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testT1MapMovesTipFixesBoundariesAndAuditsLocalMesh(testCase)
[mapped, audit] = apply_t1_mesh_transfer(parentCoords(), parentConn(), 0.01);

verifyEqual(testCase, min(mapped(:, 1)), -0.5, 'AbsTol', 1e-14);
verifyEqual(testCase, max(mapped(:, 1)), 0.5, 'AbsTol', 1e-14);
verifyEqual(testCase, mapped(parentTipNode(), :), [0.125 0], 'AbsTol', 1e-14);
verifyTrue(testCase, audit.all_positive_jacobians);
verifyTrue(testCase, audit.boundaries_fixed);
verifyTrue(testCase, audit.notch_tip_identity_preserved);
verifyGreaterThanOrEqual(testCase, audit.mapped_over_parent_edge_ratio_min, 0.75);
verifyLessThanOrEqual(testCase, audit.mapped_over_parent_edge_ratio_max, 1.25);
verifyNotEqual(testCase, audit.parent_mesh_sha256, audit.candidate_mesh_sha256);
end

function testT1MapAcceptsFineAbsoluteHOverEllWhenRelativeDistortionIsWithinBounds(testCase)
[~, audit] = apply_t1_mesh_transfer(fineParentCoords(), parentConn(), 0.01);

verifyEqual(testCase, audit.parent_h_over_ell_min, 0.2, 'AbsTol', 1e-12);
verifyEqual(testCase, audit.parent_h_over_ell_max, 0.2, 'AbsTol', 1e-12);
verifyEqual(testCase, audit.mapped_h_over_ell_min, 0.15, 'AbsTol', 1e-12);
verifyEqual(testCase, audit.mapped_h_over_ell_max, 0.25, 'AbsTol', 1e-12);
verifyEqual(testCase, audit.mapped_over_parent_edge_ratio_min, 0.75, ...
    'AbsTol', 1e-12);
verifyEqual(testCase, audit.mapped_over_parent_edge_ratio_max, 1.25, ...
    'AbsTol', 1e-12);
verifyEqual(testCase, audit.local_h_over_ell_ratio_min, ...
    audit.mapped_h_over_ell_min, 'AbsTol', 0);
verifyEqual(testCase, audit.local_h_over_ell_ratio_max, ...
    audit.mapped_h_over_ell_max, 'AbsTol', 0);
verifyEqual(testCase, string(audit.local_h_over_ell_ratio_semantics), ...
    "mapped_incident_edge_h_over_ell_absolute_v1");
end

function testT1EdgeRatioGateRejectsRelativeDistortionOutsideBounds(testCase)
parent = fineParentCoords();
[mapped, audit] = apply_t1_mesh_transfer(parent, parentConn(), 0.01);
tipNodeId = parentTipNode();
parentEdgeLength = 0.002;

aboveUpper = mapped;
aboveUpper(tipNodeId - 1, 1) = mapped(tipNodeId, 1) - ...
    (audit.mapped_over_parent_edge_ratio_limit_max + 2 * ...
    audit.mapped_over_parent_edge_ratio_tolerance) * parentEdgeLength;
verifyError(testCase, ...
    @() audit_t1_mesh_transfer_edges( ...
    parent, aboveUpper, parentConn(), tipNodeId, 0.01), ...
    "toyRoad:MeshTransferGateFailed");

belowLower = mapped;
belowLower(tipNodeId + 1, 1) = mapped(tipNodeId, 1) + ...
    (audit.mapped_over_parent_edge_ratio_limit_min - 2 * ...
    audit.mapped_over_parent_edge_ratio_tolerance) * parentEdgeLength;
verifyError(testCase, ...
    @() audit_t1_mesh_transfer_edges( ...
    parent, belowLower, parentConn(), tipNodeId, 0.01), ...
    "toyRoad:MeshTransferGateFailed");
end

function testT1EdgeRatioGateLocksApprovedAffineFactorsAndTolerance(testCase)
parent = fineParentCoords();
[mapped, audit] = apply_t1_mesh_transfer(parent, parentConn(), 0.01);
caseLock = jsondecode(fileread(fullfile(lockDir(), 'T1_INPUT_LOCK.json')));
transferLock = caseLock.mesh_transfer;
gateLock = transferLock.quality_gate;

verifyEqual(testCase, transferLock.left_affine_x_factor, 1.25, 'AbsTol', 0);
verifyEqual(testCase, transferLock.right_affine_x_factor, 0.75, 'AbsTol', 0);
verifyEqual(testCase, audit.left_affine_x_factor, ...
    transferLock.left_affine_x_factor, 'AbsTol', 0);
verifyEqual(testCase, audit.right_affine_x_factor, ...
    transferLock.right_affine_x_factor, 'AbsTol', 0);
verifyEqual(testCase, gateLock.mapped_over_parent_edge_ratio_min, 0.75, ...
    'AbsTol', 0);
verifyEqual(testCase, gateLock.mapped_over_parent_edge_ratio_max, 1.25, ...
    'AbsTol', 0);
verifyEqual(testCase, gateLock.tolerance, 1e-12, 'AbsTol', 0);
verifyEqual(testCase, audit.mapped_over_parent_edge_ratio_limit_min, ...
    gateLock.mapped_over_parent_edge_ratio_min, 'AbsTol', 0);
verifyEqual(testCase, audit.mapped_over_parent_edge_ratio_limit_max, ...
    gateLock.mapped_over_parent_edge_ratio_max, 'AbsTol', 0);
verifyEqual(testCase, audit.mapped_over_parent_edge_ratio_tolerance, ...
    gateLock.tolerance, 'AbsTol', 0);
verifyEqual(testCase, string(gateLock.semantics), ...
    "mapped_incident_edge_length_over_corresponding_parent_incident_edge_length_v1");
verifyTrue(testCase, gateLock.absolute_h_over_ell_is_audit_only);

tipNodeId = parentTipNode();
parentEdgeLength = 0.002;
withinTolerance = mapped;
withinTolerance(tipNodeId - 1, 1) = mapped(tipNodeId, 1) - ...
    (1.25 + 0.5e-12) * parentEdgeLength;
withinTolerance(tipNodeId + 1, 1) = mapped(tipNodeId, 1) + ...
    (0.75 - 0.5e-12) * parentEdgeLength;
edgeAudit = audit_t1_mesh_transfer_edges( ...
    parent, withinTolerance, parentConn(), tipNodeId, 0.01);
verifyGreaterThanOrEqual(testCase, edgeAudit.mapped_over_parent_edge_ratio_min, ...
    0.75 - 1e-12);
verifyLessThanOrEqual(testCase, edgeAudit.mapped_over_parent_edge_ratio_max, ...
    1.25 + 1e-12);
end

function testT1IncidentEdgeCorrespondenceIsDeterministic(testCase)
parent = fineParentCoords();
[mapped, ~] = apply_t1_mesh_transfer(parent, parentConn(), 0.01);

forward = audit_t1_mesh_transfer_edges( ...
    parent, mapped, parentConn(), parentTipNode(), 0.01);
reordered = audit_t1_mesh_transfer_edges( ...
    parent, mapped, flipud(parentConn()), parentTipNode(), 0.01);

verifyEqual(testCase, forward.incident_edge_node_ids, ...
    reordered.incident_edge_node_ids);
verifyEqual(testCase, forward.parent_incident_edge_lengths, ...
    reordered.parent_incident_edge_lengths, 'AbsTol', 0);
verifyEqual(testCase, forward.mapped_incident_edge_lengths, ...
    reordered.mapped_incident_edge_lengths, 'AbsTol', 0);
verifyEqual(testCase, forward.mapped_over_parent_edge_ratios, ...
    reordered.mapped_over_parent_edge_ratios, 'AbsTol', 0);
end

function testT1EdgeRatioGateRejectsZeroLengthParentEdgeBeforeDivision(testCase)
parent = fineParentCoords();
parent(parentTipNode() + 1, :) = parent(parentTipNode(), :);

verifyError(testCase, ...
    @() audit_t1_mesh_transfer_edges( ...
    parent, parent, parentConn(), parentTipNode(), 0.01), ...
    "toyRoad:MeshTransferGateFailed");
end

function testT1MapRejectsInvertedMesh(testCase)
inverted = parentConn();
inverted(1, :) = inverted(1, [1 4 3 2]);
verifyError(testCase, ...
    @() apply_t1_mesh_transfer(parentCoords(), inverted, 0.01), ...
    "toyRoad:MeshTransferGateFailed");
end

function testEventRequiresThreeConnectedRightBoundaryNodes(testCase)
state = emptyEventState();
[coords, conn, chainIds] = rightBoundaryChain();

state = advance_toy_road_event(state, coords, conn, 9, damageAt(coords, chainIds(1:2)));
verifyTrue(testCase, isnan(state.first_hit));
verifyEqual(testCase, state.consecutive_post_hit, 0);
verifyFalse(testCase, state.hit);

state = advance_toy_road_event(state, coords, conn, 10, damageAt(coords, chainIds(1:3)));
verifyEqual(testCase, state.first_hit, 10);
verifyTrue(testCase, isnan(state.confirmed));
verifyEqual(testCase, state.consecutive_post_hit, 0);
verifyEqual(testCase, state.connected_component_node_ids, sort(chainIds(1:3))');
end

function testEventConfirmsAfterThreePostHitCyclesAndPreservesFirstHit(testCase)
state = emptyEventState();
[coords, conn, chainIds] = rightBoundaryChain();
hitDamage = damageAt(coords, chainIds(1:3));

state = advance_toy_road_event(state, coords, conn, 10, hitDamage);
state = advance_toy_road_event(state, coords, conn, 11, hitDamage);
state = advance_toy_road_event(state, coords, conn, 12, hitDamage);
verifyTrue(testCase, isnan(state.confirmed));
verifyEqual(testCase, state.consecutive_post_hit, 2);

state = advance_toy_road_event(state, coords, conn, 13, hitDamage);
verifyEqual(testCase, state.first_hit, 10);
verifyEqual(testCase, state.confirmed, 13);
verifyEqual(testCase, state.consecutive_post_hit, 3);

state = advance_toy_road_event(state, coords, conn, 14, damageAt(coords, chainIds(1:2)));
verifyEqual(testCase, state.first_hit, 10);
verifyEqual(testCase, state.confirmed, 13);
verifyEqual(testCase, state.consecutive_post_hit, 0);

resetState = emptyEventState();
resetState = advance_toy_road_event(resetState, coords, conn, 10, hitDamage);
resetState = advance_toy_road_event(resetState, coords, conn, 11, damageAt(coords, chainIds(1:2)));
resetState = advance_toy_road_event(resetState, coords, conn, 12, hitDamage);
verifyEqual(testCase, resetState.first_hit, 10);
verifyTrue(testCase, isnan(resetState.confirmed));
verifyEqual(testCase, resetState.consecutive_post_hit, 1);
end

function testEventUsesSharedQ4EdgesRatherThanCoordinateProximity(testCase)
state = emptyEventState();
[coords, conn, hitIds] = disconnectedRightBoundaryNodes();

state = advance_toy_road_event(state, coords, conn, 10, damageAt(coords, hitIds));
verifyTrue(testCase, isnan(state.first_hit));
verifyFalse(testCase, state.hit);
verifyEqual(testCase, state.connected_component_size, 1);
end

function testEventRejectsMissingPhysicalCycle(testCase)
state = emptyEventState();
[coords, conn, chainIds] = rightBoundaryChain();
hitDamage = damageAt(coords, chainIds(1:3));

state = advance_toy_road_event(state, coords, conn, 10, hitDamage);
verifyError(testCase, ...
    @() advance_toy_road_event(state, coords, conn, 12, hitDamage), ...
    "toyRoad:InvalidEventSequence");
end

function testEventRejectsDuplicateAndOutOfOrderCycles(testCase)
state = emptyEventState();
[coords, conn, chainIds] = rightBoundaryChain();
hitDamage = damageAt(coords, chainIds(1:3));

state = advance_toy_road_event(state, coords, conn, 10, hitDamage);
verifyError(testCase, ...
    @() advance_toy_road_event(state, coords, conn, 10, hitDamage), ...
    "toyRoad:InvalidEventSequence");
verifyError(testCase, ...
    @() advance_toy_road_event(state, coords, conn, 9, hitDamage), ...
    "toyRoad:InvalidEventSequence");
end

function testEventRecordsLastProcessedCycle(testCase)
state = emptyEventState();
[coords, conn, chainIds] = rightBoundaryChain();
hitDamage = damageAt(coords, chainIds(1:3));

state = advance_toy_road_event(state, coords, conn, 10, hitDamage);
verifyEqual(testCase, state.last_processed_cycle, 10);
state = advance_toy_road_event(state, coords, conn, 11, hitDamage);
verifyEqual(testCase, state.last_processed_cycle, 11);
end

function copyRequiredLocks(sourceDir, targetDir)
copyfile(fullfile(sourceDir, 'PARENT_LOCK.json'), targetDir);
copyfile(fullfile(sourceDir, 'FAMILY_INPUT_LOCK.json'), targetDir);
copyfile(fullfile(sourceDir, 'T1_INPUT_LOCK.json'), targetDir);
copyfile(fullfile(sourceDir, 'T2_INPUT_LOCK.json'), targetDir);
copyfile(fullfile(sourceDir, 'T3_INPUT_LOCK.json'), targetDir);
end

function [tempDir, cleanup] = copiedLockDir()
tempDir = tempname;
mkdir(tempDir);
cleanup = onCleanup(@() rmdir(tempDir, 's'));
copyRequiredLocks(lockDir(), tempDir);
end

function writeJson(path, value)
fileId = fopen(path, 'w');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, jsonencode(value), 'char');
end

function value = lockDir()
value = fileparts(fileparts(mfilename('fullpath')));
end

function coords = parentCoords()
x = [-0.5 -0.01 0 0.01 0.5];
y = [-0.01 0 0.01];
[xGrid, yGrid] = meshgrid(x, y);
coords = [reshape(xGrid.', [], 1) reshape(yGrid.', [], 1)];
end

function coords = fineParentCoords()
x = [-0.5 -0.002 0 0.002 0.5];
y = [-0.002 0 0.002];
[xGrid, yGrid] = meshgrid(x, y);
coords = [reshape(xGrid.', [], 1) reshape(yGrid.', [], 1)];
end

function conn = parentConn()
conn = [1 2 7 6; 2 3 8 7; 3 4 9 8; 4 5 10 9; ...
        6 7 12 11; 7 8 13 12; 8 9 14 13; 9 10 15 14];
end

function nodeId = parentTipNode()
nodeId = 8;
end

function state = emptyEventState()
state = struct('first_hit', NaN, 'confirmed', NaN, ...
    'consecutive_post_hit', 0, 'hit_node_ids', zeros(0, 1), ...
    'connected_component_node_ids', zeros(0, 1), ...
    'connected_component_size', 0, 'hit', false);
end

function [coords, conn, chainIds] = rightBoundaryChain()
coords = [0.40 0.00; 0.50 0.02; 0.40 0.01; 0.40 0.02; ...
          0.40 0.03; 0.50 0.01; 0.50 0.03; 0.50 0.00];
conn = [1 8 6 3; 3 6 2 4; 4 2 7 5];
chainIds = [8 6 2 7];
end

function damage = damageAt(coords, nodeIds)
damage = zeros(size(coords, 1), 1);
damage(nodeIds) = 0.95;
end

function [coords, conn, hitIds] = disconnectedRightBoundaryNodes()
coords = [0.49 -0.01; 0.50 0.00; 0.49 0.01; 0.49 -0.02; ...
          0.49 0.00; 0.50 0.01; 0.49 0.02; 0.49 -0.01; ...
          0.49 0.01; 0.50 0.02; 0.49 0.03; 0.49 0.00];
conn = [4 1 3 2; 8 5 7 6; 12 9 11 10];
hitIds = [2 6 10];
end
