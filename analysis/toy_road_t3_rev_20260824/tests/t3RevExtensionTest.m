function tests = t3RevExtensionTest
%T3REVEXTENSIONTEST Qualify the non-authorizing generated T3-rev overlay.
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
repositoryRoot = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
baseRoot = fullfile(repositoryRoot, 'producer_handoffs', ...
    'toy_road_p0_repeatability_20260803');
extensionRoot = tempname;
buildGeneratedExtension(repositoryRoot, baseRoot, extensionRoot);
testCase.TestData.baseRoot = baseRoot;
testCase.TestData.extensionRoot = extensionRoot;
testCase.TestData.mesh = canonicalMesh();
testCase.addTeardown(@() removeRoot(extensionRoot));
end

function testLegacyRolesAreBehaviorallyIdentical(testCase)
legacy = {'P0_parent','P0R_parent_repeat','T1_initial_defect', ...
    'T2_material_state','T3_loading_history'};
for index = 1:numel(legacy)
    baseCfg = buildFromRoot(testCase.TestData.baseRoot, legacy{index}, ...
        testCase.TestData.mesh);
    extensionCfg = buildFromRoot(testCase.TestData.extensionRoot, legacy{index}, ...
        testCase.TestData.mesh);
    verifyEqual(testCase, stripHandles(extensionCfg), stripHandles(baseCfg), ...
        legacy{index});
end
end

function testT3RevHasOnlyTheApprovedReversedLoadingBlocks(testCase)
rev = buildFromRoot(testCase.TestData.extensionRoot, ...
    'T3_rev_loading_order', testCase.TestData.mesh);

verifyEqual(testCase, rev.case_physics.loading.blocks, ...
    [1 30 0.126; 31 60 0.108; 61 150 0.120]);
verifyEqual(testCase, rev.changed_axes, {'loading.blocks'});
end

function testC5ThresholdsAndMetricFormulasMatchBaseT3(testCase)
baseReceipt = c5Receipt(testCase.TestData.baseRoot, testCase.TestData.baseRoot, ...
    'T3_loading_history', tempname, c5Fixture());
extensionReceipt = c5Receipt(testCase.TestData.extensionRoot, ...
    testCase.TestData.baseRoot, 'T3_rev_loading_order', tempname, c5Fixture());

thresholds = {'displacement_residual_threshold', ...
    'projected_phase_kkt_threshold', ...
    'consecutive_stagger_delta_threshold', ...
    'primal_feasibility_threshold'};
metrics = {'final_displacement_residual', 'final_projected_phase_kkt', ...
    'final_consecutive_stagger_delta', 'final_primal_feasibility'};
for index = 1:numel(thresholds)
    verifyEqual(testCase, extensionReceipt.(thresholds{index}), ...
        baseReceipt.(thresholds{index}), thresholds{index});
    verifyEqual(testCase, extensionReceipt.(metrics{index}), ...
        baseReceipt.(metrics{index}), metrics{index});
end
verifyEqual(testCase, ...
    [extensionReceipt.displacement_residual_threshold, ...
     extensionReceipt.projected_phase_kkt_threshold, ...
     extensionReceipt.consecutive_stagger_delta_threshold, ...
     extensionReceipt.primal_feasibility_threshold], [4e-4 4e-4 1e-3 1e-12]);
verifyEqual(testCase, extensionReceipt.final_displacement_residual, 3e-4, ...
    'AbsTol', 1e-15);
verifyEqual(testCase, extensionReceipt.final_projected_phase_kkt, 2e-4, ...
    'AbsTol', 1e-15);
verifyEqual(testCase, extensionReceipt.final_consecutive_stagger_delta, 5e-4, ...
    'AbsTol', 1e-15);
verifyEqual(testCase, extensionReceipt.final_primal_feasibility, 0, ...
    'AbsTol', 0);
end

function cfg = buildFromRoot(root, caseId, mesh)
clear build_toy_road_family_case
addpath(root, '-begin');
cfg = build_toy_road_family_case(caseId, mesh);
rmpath(root);
clear build_toy_road_family_case
end

function receipt = c5Receipt(root, baseRoot, caseId, outputRoot, fixture)
mkdir(outputRoot);
clear ToyRoadC5Trace begin_toy_road_c5_trace append_toy_road_c5_stagger_row finalize_toy_road_c5_gate
addpath(baseRoot, '-begin');
addpath(root, '-begin');
trace = begin_toy_road_c5_trace(c5Entry(caseId, fixture), outputRoot);
trace = append_toy_road_c5_stagger_row(trace, c5Row(fixture));
receipt = finalize_toy_road_c5_gate(trace);
clear trace
rmpath(root);
if ~strcmp(root, baseRoot)
    rmpath(baseRoot);
end
clear ToyRoadC5Trace begin_toy_road_c5_trace append_toy_road_c5_stagger_row finalize_toy_road_c5_gate
removeRoot(outputRoot);
end

function input = c5Entry(caseId, fixture)
input = struct( ...
    'authorization_scope', 'TEST_ONLY_NON_AUTHORIZING_SCOPE', ...
    'case_id', caseId, ...
    'cycle', 5, ...
    'substep_ordinal', 4, ...
    'evidence_method', 'same_process_post_update_reassembly_v1', ...
    'd_lb', [0.5;0.6], ...
    'd_prev_stag', [0.5;0.6], ...
    'history_pre', reshape(1:4, 1, 4) / 100, ...
    'active_u_dofs', [1;2;3], ...
    'active_d_dofs', [1;2], ...
    'traction', [0.3;0.4;0.5], ...
    'reassemble_equilibrium', @(snapshot,u,d) equilibriumResidual( ...
        snapshot, u, d, fixture), ...
    'reassemble_phase', @(snapshot,u,d,raw) phaseResidual( ...
        snapshot, u, d, raw, fixture));
end

function row = c5Row(fixture)
row = struct('u', zeros(3,1), 'd', [0.5005;0.6], ...
    'stagger_converged', true);
if ~isequal(fixture, c5Fixture())
    error('toyRoadT3Rev:InvalidFixture', 'The C5 fixture must remain exact.');
end
end

function [residual, raw] = equilibriumResidual(~, ~, ~, fixture)
residual = fixture.displacement_residual;
raw = fixture.raw;
end

function residual = phaseResidual(~, ~, ~, raw, fixture)
if ~isequal(raw, fixture.raw)
    error('toyRoadT3Rev:InvalidFixture', 'The C5 raw reassembly value changed.');
end
residual = fixture.phase_residual;
end

function fixture = c5Fixture()
fixture = struct('displacement_residual', [3e-4;0;0], ...
    'phase_residual', [-2e-4;0], 'raw', ones(1,4));
end

function mesh = canonicalMesh()
[x,y] = meshgrid([-0.5 0 0.5], [-0.5 0 0.5]);
mesh = struct('node_coords', [x(:) y(:)], ...
    'connectivity', [1 4 5 2; 4 7 8 5; 2 5 6 3; 5 8 9 6]);
end

function output = stripHandles(input)
output = input;
if ~isstruct(output)
    return;
end
names = fieldnames(output);
for index = 1:numel(names)
    name = names{index};
    value = output.(name);
    if isa(value, 'function_handle')
        output = rmfield(output, name);
    elseif isstruct(value)
        output.(name) = stripHandles(value);
    end
end
end

function buildGeneratedExtension(repositoryRoot, baseRoot, extensionRoot)
builderPath = fullfile(repositoryRoot, 'analysis', ...
    'toy_road_t3_rev_20260824', 'build_t3_rev_extension.py');
command = sprintf([ ...
    'py -3 -c "import importlib.util; from pathlib import Path; ' ...
    'p=Path(r''%s''); s=importlib.util.spec_from_file_location(''t3'',p); ' ...
    'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); ' ...
    'm.build_extension(Path(r''%s''),Path(r''%s''),''aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'')"'], ...
    slashPath(builderPath), slashPath(baseRoot), slashPath(extensionRoot));
[status, message] = system(command);
if status ~= 0
    error('toyRoadT3Rev:ExtensionGenerationFailed', '%s', message);
end
end

function removeRoot(root)
if isfolder(root)
    rmdir(root, 's');
end
end

function value = slashPath(value)
value = strrep(value, '\', '/');
end
