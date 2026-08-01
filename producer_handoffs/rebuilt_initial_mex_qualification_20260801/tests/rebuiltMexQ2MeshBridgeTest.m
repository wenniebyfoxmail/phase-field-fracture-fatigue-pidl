function tests = rebuiltMexQ2MeshBridgeTest
tests = functiontests(localfunctions);
end

function testCanonicalLockPinsDistinctSourceAndParentVtkIdentities(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
lockPath = fullfile(handoff, 'Q2_INPUT_LOCK.json');
lock = jsondecode(fileread(lockPath));

verifyTrue(testCase, isfield(lock, 'mesh_bridge'));
verifyEqual(testCase, fileHash(lockPath), ...
    '563bc0b5090ad62cc84c9f642adc7a474cfffa6872253b267498b3ee21c49193');
bridge = lock.mesh_bridge;
verifyEqual(testCase, bridge.semantics_id, ...
    'q2_source_to_parent_vtk_mesh_bridge_v1');
verifyEqual(testCase, bridge.replay_source_mesh_sha256, ...
    'd9ad5545e42e4d700600a69f18b625f90456253295095fdf644c55b7968b068b');
verifyEqual(testCase, bridge.parent_vtk_mesh_sha256, ...
    '4d01985bfe2e80afe7140ab1ead905ddce5843f8495a3558d2d4da3b237df5af');
verifyNotEqual(testCase, bridge.replay_source_mesh_sha256, ...
    bridge.parent_vtk_mesh_sha256);
verifyEqual(testCase, bridge.coordinate_max_abs_tolerance, 1e-14, ...
    'AbsTol', 0);
verifyEqual(testCase, bridge.reference_coordinate_max_abs_error, ...
    4.9960036108132044e-16, 'RelTol', 1e-15);
verifyEqual(testCase, bridge.reference_coordinate_rms_error, ...
    2.4425164635939659e-16, 'RelTol', 1e-15);
end

function testRealSourceMeshBridgesToLockedParentVtkWithoutSolver(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
lock = jsondecode(fileread(fullfile(handoff, 'Q2_INPUT_LOCK.json')));
sourceRoot = 'C:/q4diag/griphfith-f1b-355d4c83';
parentRoot = 'C:/q4diag/toy-road-parent-20260729';
oldPath = path;
cleanup = onCleanup(@() path(oldPath));
addpath(fullfile(sourceRoot, 'Sources'));
[mesh, ~] = specimen.external.gmsh_import( ...
    fullfile(sourceRoot, 'Dependencies', 'meshes', 'sens_mesh.m'), 't', 1);

receipt = validate_q2_mesh_bridge(mesh.node(:, 1:2), ...
    mesh.elem(:, 1:4), parentRoot, lock.mesh_bridge);

verifyTrue(testCase, receipt.passed);
verifyTrue(testCase, receipt.connectivity_exact);
verifyEqual(testCase, receipt.replay_source_mesh_sha256, ...
    lock.mesh_bridge.replay_source_mesh_sha256);
verifyEqual(testCase, receipt.parent_vtk_mesh_sha256, ...
    lock.mesh_bridge.parent_vtk_mesh_sha256);
verifyLessThanOrEqual(testCase, receipt.coordinate_max_abs_error, ...
    lock.mesh_bridge.coordinate_max_abs_tolerance);
verifyEqual(testCase, receipt.coordinate_max_abs_error, ...
    lock.mesh_bridge.reference_coordinate_max_abs_error, 'RelTol', 1e-15);
verifyEqual(testCase, receipt.coordinate_rms_error, ...
    lock.mesh_bridge.reference_coordinate_rms_error, 'RelTol', 1e-15);
end

function testBridgeRejectsMappedSourceMesh(testCase)
[coords, connectivity, parentRoot, contract] = fixture(testCase);
coords(1, 1) = coords(1, 1) + 0.01;

verifyError(testCase, @() validate_q2_mesh_bridge( ...
    coords, connectivity, parentRoot, contract), ...
    'rebuiltMexQ2:ReplaySourceMeshMismatch');
end

function testBridgeRejectsReorderedElements(testCase)
[coords, connectivity, parentRoot, contract] = fixture(testCase);
connectivity = connectivity([2 1], :);
contract.replay_source_mesh_sha256 = meshHash(coords, connectivity);

verifyError(testCase, @() validate_q2_mesh_bridge( ...
    coords, connectivity, parentRoot, contract), ...
    'rebuiltMexQ2:MeshBridgeConnectivityMismatch');
end

function testBridgeRejectsCoordinatesOverPredeclaredTolerance(testCase)
[coords, connectivity, parentRoot, contract] = fixture(testCase);
coords(2, 2) = coords(2, 2) + 2e-6;
contract.replay_source_mesh_sha256 = meshHash(coords, connectivity);

verifyError(testCase, @() validate_q2_mesh_bridge( ...
    coords, connectivity, parentRoot, contract), ...
    'rebuiltMexQ2:MeshBridgeCoordinateMismatch');
end

function [coords, connectivity, parentRoot, contract] = fixture(testCase)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
parentRoot = folder.Folder;
coords = [0 0; 1 0; 2 0; 0 1; 1 1; 2 1];
connectivity = [1 2 5 4; 2 3 6 5];
vtkCoords = coords;
vtkCoords(1, 1) = vtkCoords(1, 1) + 5e-16;
vtkPath = fullfile(parentRoot, 'parent.vtk');
writeLegacyQ4Vtk(vtkPath, vtkCoords, connectivity);
contract = struct( ...
    'semantics_id', 'q2_source_to_parent_vtk_mesh_bridge_v1', ...
    'replay_source_mesh_sha256', meshHash(coords, connectivity), ...
    'replay_source_mesh_sha256_semantics', ...
    'sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1', ...
    'parent_vtk_relative_path', 'parent.vtk', ...
    'parent_vtk_sha256', fileHash(vtkPath), ...
    'parent_vtk_mesh_sha256', meshHash(vtkCoords, connectivity), ...
    'parent_vtk_mesh_sha256_semantics', ...
    'sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1', ...
    'connectivity_requirement', 'exact_q4_row_and_local_node_order', ...
    'num_node', 6, 'num_elem', 2, ...
    'coordinate_max_abs_tolerance', 1e-12, ...
    'reference_coordinate_max_abs_error', 5e-16, ...
    'reference_coordinate_rms_error', sqrt((5e-16)^2 / 12));
end

function writeLegacyQ4Vtk(filePath, coords, connectivity)
fileId = fopen(filePath, 'w');
cleanup = onCleanup(@() fclose(fileId));
fprintf(fileId, '# vtk DataFile Version 3.0\nfixture\nASCII\n');
fprintf(fileId, 'DATASET UNSTRUCTURED_GRID\n');
fprintf(fileId, 'POINTS %d double\n', size(coords, 1));
fprintf(fileId, '%.17g %.17g 0\n', coords.');
fprintf(fileId, 'CELLS %d %d\n', size(connectivity, 1), ...
    5 * size(connectivity, 1));
zeroBased = connectivity - 1;
fprintf(fileId, '4 %d %d %d %d\n', zeroBased.');
fprintf(fileId, 'CELL_TYPES %d\n', size(connectivity, 1));
fprintf(fileId, '%d\n', 9 * ones(size(connectivity, 1), 1));
end

function digest = meshHash(coords, connectivity)
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(typecast(double(coords(:)), 'uint8'));
md.update(typecast(int64(connectivity(:)), 'uint8'));
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function digest = fileHash(filePath)
fileId = fopen(filePath, 'rb');
cleanup = onCleanup(@() fclose(fileId));
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(fread(fileId, Inf, '*uint8'));
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end
