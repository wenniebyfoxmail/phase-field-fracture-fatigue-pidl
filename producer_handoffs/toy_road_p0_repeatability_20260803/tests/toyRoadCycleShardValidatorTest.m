function tests = toyRoadCycleShardValidatorTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
validatorDir = fileparts(fileparts(mfilename('fullpath')));
addpath(validatorDir);
testCase.addTeardown(@() rmpath(validatorDir));
end

function testAcceptsValidFirstCycleShard(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
metrics = validate_toy_road_cycle_shard(shard, previous, state0, contract);
verifyTrue(testCase, metrics.is_valid);
verifyTrue(testCase, metrics.chronology_ok);
verifyEqual(testCase, metrics.damage_min, 0.10, 'AbsTol', 1e-12);
verifyEqual(testCase, metrics.damage_max, 0.14, 'AbsTol', 1e-12);
end

function testAcceptsValidSuccessorCycleShard(testCase)
[previous, ~, state0, contract] = toyRoadShardFixture(1);
[shard, ~, ~, ~] = toyRoadShardFixture(2);
metrics = validate_toy_road_cycle_shard(shard, previous, state0, contract);
verifyTrue(testCase, metrics.is_valid);
verifyTrue(testCase, metrics.chronology_ok);
end

function testRejectsWrongElementGpSubstepShape(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.d_gp = zeros(1, 4, 4);
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsNonFiniteValue(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.psi_raw_gp(1,1,1) = NaN;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsDamageBelowLowerBound(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.d_node(1,1) = state0.d_node(1) - 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsDamageAboveOne(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.d_node(1,3) = 1 + 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsNegativeHistory(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.alpha_bar_gp(1,1,1) = -2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsDecreasingHistoryWithinCycle(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.alpha_bar_gp(1,1,3) = shard.alpha_bar_gp(1,1,2) - 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsCarraraMismatch(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.f_alpha_gp(1,1,3) = shard.f_alpha_gp(1,1,3) + 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsFatigueValueOutsideUnitRange(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.f_alpha_gp(1,1,1) = 1 + 2e-10;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsNegativeRawDriver(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.psi_raw_gp(1,1,1) = -2e-10;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsNegativeActiveDriver(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.psi_active_gp(1,1,1) = -2e-10;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsIncorrectDegradation(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.g_gp(1,1,2) = shard.g_gp(1,1,2) + 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsIncorrectActiveDriver(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.psi_active_gp(1,1,2) = shard.psi_active_gp(1,1,2) + 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsIncorrectCycleMaximum(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.psi_raw_cyclemax_gp(1,1) = shard.psi_raw_cyclemax_gp(1,1) - 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongSubstepOrder(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.substep_ordinal = [1 2 4 3 5];
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongRawStepMapping(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.raw_step_zero_based(4) = 9;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongMeshId(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.mesh_sha256(1) = '0';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongElementOrderingId(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.element_ordering_id = 'wrong_element_order';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongGpOrderingId(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.gp_ordering_id = 'wrong_gp_order';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongStateSemanticsId(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.state_semantics_id = 'wrong_state_semantics';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongRuntimeLockDigest(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.runtime_lock_sha256(1) = '0';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongFamilyContractDigest(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.family_contract_sha256(1) = '0';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongCasePhysicsContractDigest(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.case_physics_contract_sha256(1) = '0';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsWrongExecutionInputLockDigest(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(1);
shard.execution_input_lock_sha256(1) = '0';
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsCrossCycleHistoryDecrease(testCase)
[previous, ~, state0, contract] = toyRoadShardFixture(1);
[shard, ~, ~, ~] = toyRoadShardFixture(2);
shard.alpha_bar_gp(:,:,1) = previous.alpha_bar_gp(:,:,5) - 2e-12;
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsPreviousForFirstCycle(testCase)
[shard, ~, state0, contract] = toyRoadShardFixture(1);
[previous, ~, ~, ~] = toyRoadShardFixture(1);
verifyInvalid(testCase, shard, previous, state0, contract);
end

function testRejectsMissingPreviousForSuccessorCycle(testCase)
[shard, previous, state0, contract] = toyRoadShardFixture(2);
verifyInvalid(testCase, shard, previous, state0, contract);
end

function verifyInvalid(testCase, shard, previous, state0, contract)
verifyError(testCase, ...
    @() validate_toy_road_cycle_shard(shard, previous, state0, contract), ...
    'toyRoadP0:InvalidCycleShard');
end
