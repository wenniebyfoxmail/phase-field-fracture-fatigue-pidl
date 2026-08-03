function tests = toyRoadCaseBuilderTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
testCase.addTeardown(@() rmpath(handoffDir()));
end

function testP0AndP0RAreByteIdenticalPhysics(testCase)
mesh = parentMeshFixture();
p0 = build_toy_road_family_case('P0_parent', mesh);
p0r = build_toy_road_family_case('P0R_parent_repeat', mesh);

verifyEqual(testCase, jsonencode(p0.case_physics), jsonencode(p0r.case_physics));
verifyEqual(testCase, p0.changed_axes, cell(1,0));
verifyEqual(testCase, p0r.changed_axes, cell(1,0));
verifyNotEqual(testCase, p0.case_id, p0r.case_id);
end

function testT1ChangesOnlyDeclaredMappedMesh(testCase)
mesh = parentMeshFixture();
p0 = build_toy_road_family_case('P0_parent', mesh);
t1 = build_toy_road_family_case('T1_initial_defect', mesh);

verifyEqual(testCase, t1.changed_axes, {'mesh.node_coords'});
verifyEqual(testCase, t1.case_physics.material, p0.case_physics.material);
verifyEqual(testCase, t1.case_physics.loading, p0.case_physics.loading);
verifyEqual(testCase, t1.case_physics.numerics, p0.case_physics.numerics);
verifyEqual(testCase, t1.case_physics.recovery, p0.case_physics.recovery);
verifyEqual(testCase, t1.case_physics.event, p0.case_physics.event);
verifyEqual(testCase, t1.mesh.connectivity, p0.mesh.connectivity);
verifyNotEqual(testCase, t1.mesh.node_coords, p0.mesh.node_coords);
verifyNotEqual(testCase, t1.mesh.mesh_sha256, p0.mesh.mesh_sha256);

tip = find(all(abs(mesh.node_coords) <= 1e-12, 2));
verifyEqual(testCase, numel(tip), 1);
verifyEqual(testCase, t1.mesh.node_coords(tip,:), [0.125 0], 'AbsTol', 1e-12);
verifyEqual(testCase, min(t1.mesh.node_coords(:,1)), -0.5, 'AbsTol', 1e-12);
verifyEqual(testCase, max(t1.mesh.node_coords(:,1)), 0.5, 'AbsTol', 1e-12);
verifyGreaterThanOrEqual(testCase, ...
    t1.mesh.transfer_audit.mapped_over_parent_edge_ratio_min, 0.75-1e-12);
verifyLessThanOrEqual(testCase, ...
    t1.mesh.transfer_audit.mapped_over_parent_edge_ratio_max, 1.25+1e-12);
end

function testT2ChangesOnlyGc(testCase)
mesh = parentMeshFixture();
p0 = build_toy_road_family_case('P0_parent', mesh);
t2 = build_toy_road_family_case('T2_material_state', mesh);

verifyEqual(testCase, t2.changed_axes, {'material.Gc'});
verifyEqual(testCase, t2.case_physics.mesh, p0.case_physics.mesh);
verifyEqual(testCase, t2.case_physics.loading, p0.case_physics.loading);
verifyEqual(testCase, t2.case_physics.numerics, p0.case_physics.numerics);
verifyEqual(testCase, t2.case_physics.recovery, p0.case_physics.recovery);
verifyEqual(testCase, t2.case_physics.event, p0.case_physics.event);
verifyEqual(testCase, p0.case_physics.material.Gc, 0.01);
verifyEqual(testCase, t2.case_physics.material.Gc, 0.008);
verifyEqual(testCase, rmfield(t2.case_physics.material, 'Gc'), ...
    rmfield(p0.case_physics.material, 'Gc'));
end

function testT3ChangesOnlyLoadingBlocks(testCase)
mesh = parentMeshFixture();
p0 = build_toy_road_family_case('P0_parent', mesh);
t3 = build_toy_road_family_case('T3_loading_history', mesh);

verifyEqual(testCase, t3.changed_axes, {'loading.blocks'});
verifyEqual(testCase, t3.case_physics.mesh, p0.case_physics.mesh);
verifyEqual(testCase, t3.case_physics.material, p0.case_physics.material);
verifyEqual(testCase, t3.case_physics.numerics, p0.case_physics.numerics);
verifyEqual(testCase, t3.case_physics.recovery, p0.case_physics.recovery);
verifyEqual(testCase, t3.case_physics.event, p0.case_physics.event);
verifyEqual(testCase, p0.case_physics.loading.blocks, [1 150 0.12]);
verifyEqual(testCase, t3.case_physics.loading.blocks, ...
    [1 30 0.108; 31 60 0.126; 61 150 0.120]);
verifyEqual(testCase, t3.umax_for_cycle([1 30 31 60 61 150]), ...
    [0.108 0.108 0.126 0.126 0.120 0.120]);
end

function testLockedHardFiveStepNumerics(testCase)
cfg = build_toy_road_family_case('P0_parent', parentMeshFixture());

verifyEqual(testCase, cfg.case_physics.material, struct( ...
    'E',1,'nu',0.3,'Gc',0.01,'ell',0.01,'alpha_T',0.5,'p',2, ...
    'eta',0,'plane_state','plane_strain','energy_split','AMOR', ...
    'phase_field_model','AT1_history_fatigue'));
verifyEqual(testCase, cfg.case_physics.loading.load_factors, [.25 .5 .75 1 0]);
verifyEqual(testCase, cfg.sol_step_par.n_step, 5);
verifyFalse(testCase, cfg.sol_step_par.line_search);
verifyFalse(testCase, cfg.sol_jump_par.cycle_jump);
verifyFalse(testCase, cfg.resume_allowed);
verifyEqual(testCase, cfg.case_physics.loading.R, 0);
verifyEqual(testCase, cfg.case_physics.numerics.tol_displacement, 1e-6);
verifyEqual(testCase, cfg.case_physics.numerics.tol_phase_field, 4e-4);
verifyEqual(testCase, cfg.case_physics.numerics.tol_staggered, 4e-4);
verifyEqual(testCase, cfg.censor_cap, 150);
end

function testCanonicalMeshHashUsesReviewedNativeBytes(testCase)
mesh = parentMeshFixture();
cfg = build_toy_road_family_case('P0_parent', mesh);

hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(typecast(double(mesh.node_coords(:)), 'uint8'));
hasher.update(typecast(int64(mesh.connectivity(:)), 'uint8'));
bytes = typecast(hasher.digest(), 'uint8');
expected = lower(reshape(dec2hex(bytes,2).',1,[]));

verifyEqual(testCase, cfg.mesh.mesh_sha256, expected);
verifyEqual(testCase, cfg.mesh.mesh_sha256_semantics, ...
    'sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1');
end

function testCopiedEventStateMachineRequiresThreePostHitCycles(testCase)
cfg = build_toy_road_family_case('P0_parent', parentMeshFixture());
damage = zeros(size(cfg.mesh.node_coords,1),1);
damage(cfg.mesh.node_coords(:,1) >= 0.48) = 0.95;
state = [];
for cycle = 1:4
    state = cfg.advance_event(state, cycle, damage);
end

verifyEqual(testCase, state.first_hit, 1);
verifyEqual(testCase, state.confirmed, 4);
verifyEqual(testCase, state.connected_component_size, 3);
verifyTrue(testCase, state.hit);
details = functions(cfg.advance_event);
verifyEqual(testCase, details.file, ...
    fullfile(handoffDir(), 'build_toy_road_family_case.m'));
end

function testUnknownRoleFailsClosed(testCase)
verifyError(testCase, @() build_toy_road_family_case( ...
    'T4_undeclared', parentMeshFixture()), 'toyRoadP0:InvalidCaseContract');
end

function mesh = parentMeshFixture()
[x,y] = meshgrid([-0.5 0 0.5], [-0.5 0 0.5]);
mesh.node_coords = [x(:) y(:)];
mesh.connectivity = [1 4 5 2; 4 7 8 5; 2 5 6 3; 5 8 9 6];
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
