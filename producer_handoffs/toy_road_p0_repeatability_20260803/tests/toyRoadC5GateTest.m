function tests = toyRoadC5GateTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
testCase.addTeardown(@() rmpath(handoffDir()));
end

function setup(testCase)
root = tempname;
mkdir(root);
testCase.TestData.root = root;
testCase.addTeardown(@() removeRoot(root));
end

function testBeginCreatesOnlyExclusiveCanonicalHeader(testCase)
input = gateFixture();

trace = begin_toy_road_c5_trace(input, testCase.TestData.root);

expected = ['authorization_scope,case_id,cycle,substep_ordinal,' ...
    'stagger_iteration,reassembly_ordinal,displacement_residual,' ...
    'raw_phase_residual,projected_phase_kkt,' ...
    'consecutive_stagger_delta,primal_feasibility' newline];
verifyEqual(testCase, fileread(trace.trace_path), expected);
verifyEqual(testCase, trace.trace_row_count, 0);
verifyEqual(testCase, trace.same_process_reassembly_count, 0);
verifyFalse(testCase, isfile(receiptPath(testCase.TestData.root)));
end

function testAppendUsesImmutableEntrySnapshotAndFreshReassembly(testCase)
input = gateFixture();
input = withResiduals(input, [3e-5;4e-5;9], [6e-5;8e-5], ...
    reshape(1:4, 1, 4));
trace = begin_toy_road_c5_trace(input, testCase.TestData.root);
input.d_lb(:) = 0;
input.history_pre(:) = 99;
input.traction(:) = 77;

trace = append_toy_road_c5_stagger_row(trace, rowFixture(true));

rows = readtable(trace.trace_path, 'TextType', 'string', ...
    'VariableNamingRule', 'preserve');
verifyEqual(testCase, height(rows), 1);
verifyEqual(testCase, rows.displacement_residual, 5e-5, 'AbsTol', 1e-15);
verifyEqual(testCase, rows.raw_phase_residual, 1e-4, 'AbsTol', 1e-15);
verifyEqual(testCase, trace.trace_row_count, 1);
verifyEqual(testCase, trace.same_process_reassembly_count, 1);
verifyEqual(testCase, trace.stagger_ordinals, 1);
end

function testProjectedKktUsesIrreversibilityBox(testCase)
input = gateFixture();
input.d_lb = [0.4;0.2];
input.d_prev_stag = input.d_lb;
input = withResiduals(input, zeros(3,1), [1e-4;-1e-4], ones(1,4));
row = rowFixture(true);
row.d = [0.4;0.2];
trace = begin_toy_road_c5_trace(input, testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, row);

receipt = finalize_toy_road_c5_gate(trace);

expected = norm(row.d - max(input.d_lb, min(1, row.d - [1e-4;-1e-4])), inf);
verifyEqual(testCase, receipt.final_projected_phase_kkt, expected, ...
    'AbsTol', 1e-15);
verifyEqual(testCase, receipt.final_primal_feasibility, 0, 'AbsTol', 0);
end

function testRawResidualIsRecordedButDoesNotReplaceProjectedKkt(testCase)
input = gateFixture();
input.d_lb = [0.4;0.2];
input.d_prev_stag = input.d_lb;
input = withResiduals(input, zeros(3,1), [2;-1e-5], ones(1,4));
row = rowFixture(true);
row.d = [0.4;0.2];
trace = begin_toy_road_c5_trace(input, testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, row);

receipt = finalize_toy_road_c5_gate(trace);

verifyGreaterThan(testCase, receipt.final_raw_phase_residual, 1);
verifyEqual(testCase, receipt.final_projected_phase_kkt, 1e-5, ...
    'AbsTol', 1e-15);
verifyTrue(testCase, receipt.passed);
end

function testEveryMandatoryMetricIsBelowAtAndAboveItsThreshold(testCase)
thresholds = [4e-4 4e-4 1e-3 1e-12];
for metric = 1:4
    for position = 1:3
        root = fullfile(testCase.TestData.root, ...
            sprintf('metric_%d_position_%d', metric, position));
        mkdir(root);
        positions = [0.5 1 2];
        value = thresholds(metric) * positions(position);
        [input, row] = isolatedMetricFixture(metric, value);
        trace = begin_toy_road_c5_trace(input, root);
        trace = append_toy_road_c5_stagger_row(trace, row);
        if position <= 2
            receipt = finalize_toy_road_c5_gate(trace);
            verifyTrue(testCase, receipt.passed, ...
                sprintf('metric %d position %d must pass', metric, position));
        else
            verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
                'toyRoadP0:C5GateFailed');
            verifyFalse(testCase, isfile(receiptPath(root)));
        end
    end
end
end

function testFinalizeRequiresLastCompletedStaggerToBeDeclaredConverged(testCase)
input = gateFixture();
trace = begin_toy_road_c5_trace(input, testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, rowFixture(false));

verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
    'toyRoadP0:InvalidC5Lifecycle');
verifyFalse(testCase, isfile(receiptPath(testCase.TestData.root)));
end

function testFinalizeRequiresAtLeastOneCompletedStagger(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);

verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
    'toyRoadP0:InvalidC5Lifecycle');
end

function testNonSolverEvidenceMethodsAreRejected(testCase)
methods = {'post_process','fixed_count','teacher','replay'};
for index = 1:numel(methods)
    input = gateFixture();
    input.evidence_method = methods{index};
    root = fullfile(testCase.TestData.root, methods{index});
    mkdir(root);
    verifyError(testCase, @() begin_toy_road_c5_trace(input, root), ...
        'toyRoadP0:InvalidC5Input');
end
end

function testMutatedLifecycleCannotBeFinalizedAsSameProcessEvidence(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, rowFixture(true));

verifyTrue(testCase, assignmentRejected( ...
    @() assignTraceProperty(trace, 'evidence_method', 'replay')));
verifyFalse(testCase, isfile(receiptPath(testCase.TestData.root)));
end

function testReturnedTraceRejectsLifecycleCriticalStateMutations(testCase)
attacks = { ...
    'authorization_scope', 'forged_scope'; ...
    'snapshot', struct(); ...
    'active_u_dofs', 99; ...
    'active_d_dofs', 99; ...
    'd_prev_stag', zeros(2,1); ...
    'reassemble_equilibrium', @throwReassemblyFailure; ...
    'reassemble_phase', @throwReassemblyFailure; ...
    'last_row_converged', true; ...
    'trace_path', 'forged-trace.csv'; ...
    'receipt_path', 'forged-receipt.json'; ...
    'trace_row_count', 99; ...
    'same_process_reassembly_count', 99; ...
    'stagger_ordinals', 99; ...
    'trace_sha256', repmat('0', 1, 64); ...
    'lifecycle_state', []; ...
    'AuthorizationScope', 'forged_scope'; ...
    'Snapshot', struct(); ...
    'ReassembleEquilibrium', @throwReassemblyFailure; ...
    'ReassemblePhase', @throwReassemblyFailure; ...
    'TracePath', 'forged-trace.csv'; ...
    'ReceiptPath', 'forged-receipt.json'; ...
    'TraceSha256', repmat('0', 1, 64); ...
    'TraceRowCount', 99; ...
    'ReassemblyCount', 99; ...
    'StaggerOrdinals', 99; ...
    'DPreviousStagger', zeros(2,1); ...
    'LastRowConverged', true; ...
    'LifecycleState', []};

for index = 1:size(attacks, 1)
    root = fullfile(testCase.TestData.root, sprintf('attack_%02d', index));
    mkdir(root);
    trace = begin_toy_road_c5_trace(gateFixture(), root);
    trace = append_toy_road_c5_stagger_row(trace, rowFixture(false));

    verifyTrue(testCase, assignmentRejected(@() assignTraceProperty( ...
        trace, attacks{index,1}, attacks{index,2})), attacks{index,1});
    verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
        'toyRoadP0:InvalidC5Lifecycle', attacks{index,1});
    verifyFalse(testCase, isfile(receiptPath(root)), attacks{index,1});
end
end

function testConvergenceCannotBeMutatedToAuthorizeReceipt(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, rowFixture(false));

verifyTrue(testCase, assignmentRejected( ...
    @() assignTraceProperty(trace, 'last_row_converged', true)));
verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
    'toyRoadP0:InvalidC5Lifecycle');
verifyFalse(testCase, isfile(receiptPath(testCase.TestData.root)));
end

function testEditedCsvHashCannotBeInjectedToAuthorizeReceipt(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, rowFixture(true));
path = trace.trace_path;
writeBytes(path, [readBytes(path); uint8('# tampered')'; uint8(newline)']);

verifyTrue(testCase, assignmentRejected( ...
    @() assignTraceProperty(trace, 'trace_sha256', fileSha256(path))));
verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
    'toyRoadP0:InvalidC5Lifecycle');
verifyFalse(testCase, isfile(receiptPath(testCase.TestData.root)));
end

function testMultipleCompletedStaggersHaveExactRowsReassembliesAndOrdinals(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
row = rowFixture(false);
for ordinal = 1:4
    row.d = row.d + [2e-4;0];
    row.stagger_converged = ordinal == 4;
    trace = append_toy_road_c5_stagger_row(trace, row);
end

receipt = finalize_toy_road_c5_gate(trace);
rows = readtable(trace.trace_path, 'TextType', 'string', ...
    'VariableNamingRule', 'preserve');
verifyEqual(testCase, rows.stagger_iteration, (1:4).');
verifyEqual(testCase, rows.reassembly_ordinal, (1:4).');
verifyEqual(testCase, receipt.trace_row_count, 4);
verifyEqual(testCase, receipt.reassembly_count, 4);
verifyEqual(testCase, trace.stagger_ordinals, 1:4);
end

function testStaleTraceCopyCannotAppendDuplicateOrdinal(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
stale = trace;
trace = append_toy_road_c5_stagger_row(trace, rowFixture(false)); %#ok<NASGU>

verifyError(testCase, @() append_toy_road_c5_stagger_row( ...
    stale, rowFixture(true)), 'toyRoadP0:InvalidC5Lifecycle');
end

function testReassemblyFailurePoisonsLifecycleBeforeAnyMetricRow(testCase)
input = gateFixture();
input.reassemble_equilibrium = @throwReassemblyFailure;
trace = begin_toy_road_c5_trace(input, testCase.TestData.root);

verifyError(testCase, @() append_toy_road_c5_stagger_row( ...
    trace, rowFixture(true)), 'toyRoadP0:InjectedReassemblyFailure');
rows = readtable(trace.trace_path, 'TextType', 'string', ...
    'VariableNamingRule', 'preserve');
verifyEqual(testCase, height(rows), 0);
verifyError(testCase, @() append_toy_road_c5_stagger_row( ...
    trace, rowFixture(true)), 'toyRoadP0:InvalidC5Lifecycle');
end

function testExistingTraceIsNeverClobbered(testCase)
qualification = fullfile(testCase.TestData.root, 'qualification');
mkdir(qualification);
path = fullfile(qualification, 'C5_STAGGER_TRACE.csv');
original = uint8('existing trace bytes');
writeBytes(path, original);

verifyError(testCase, @() begin_toy_road_c5_trace( ...
    gateFixture(), testCase.TestData.root), 'toyRoadP0:PublicationClobber');
verifyEqual(testCase, readBytes(path), original(:));
end

function testExistingReceiptIsNeverClobbered(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, rowFixture(true));
path = receiptPath(testCase.TestData.root);
original = uint8('{"existing":true}');
writeBytes(path, original);

verifyError(testCase, @() finalize_toy_road_c5_gate(trace), ...
    'toyRoadP0:PublicationClobber');
verifyEqual(testCase, readBytes(path), original(:));
end

function testReceiptAndTraceUseExactTask2SchemaAndBindings(testCase)
trace = begin_toy_road_c5_trace(gateFixture(), testCase.TestData.root);
trace = append_toy_road_c5_stagger_row(trace, rowFixture(true));

receipt = finalize_toy_road_c5_gate(trace);
fromDisk = jsondecode(fileread(receiptPath(testCase.TestData.root)));
expectedFields = {'authorization_scope','case_id','cycle', ...
    'substep_ordinal','status','passed','trace_sha256','trace_row_count', ...
    'reassembly_count','final_stagger_iteration','final_reassembly_ordinal', ...
    'final_displacement_residual','final_raw_phase_residual', ...
    'final_projected_phase_kkt','final_consecutive_stagger_delta', ...
    'final_primal_feasibility','displacement_residual_threshold', ...
    'projected_phase_kkt_threshold','consecutive_stagger_delta_threshold', ...
    'primal_feasibility_threshold'};
verifyEqual(testCase, sort(fieldnames(fromDisk)), sort(expectedFields(:)));
verifyEqual(testCase, fromDisk, receipt);
verifyEqual(testCase, fromDisk.trace_sha256, fileSha256(trace.trace_path));
verifyEqual(testCase, fromDisk.trace_row_count, 1);
verifyEqual(testCase, fromDisk.reassembly_count, 1);
verifyEqual(testCase, fromDisk.final_stagger_iteration, 1);
verifyEqual(testCase, fromDisk.final_reassembly_ordinal, 1);
verifyEqual(testCase, fromDisk.displacement_residual_threshold, 4e-4);
verifyEqual(testCase, fromDisk.projected_phase_kkt_threshold, 4e-4);
verifyEqual(testCase, fromDisk.consecutive_stagger_delta_threshold, 1e-3);
verifyEqual(testCase, fromDisk.primal_feasibility_threshold, 1e-12);
end

function [input, row] = isolatedMetricFixture(metric, value)
input = gateFixture();
row = rowFixture(true);
row.d = [0.5;0.6];
input.d_lb = row.d;
input.d_prev_stag = row.d;
rU = zeros(3,1);
rD = zeros(2,1);
switch metric
    case 1
        rU(1) = value;
    case 2
        input.d_lb(1) = 0;
        input.d_prev_stag(1) = 0;
        row.d(1) = 0;
        rD(1) = -value;
    case 3
        input.d_lb(1) = 0;
        input.d_prev_stag(1) = 0;
        row.d(1) = value;
    case 4
        input.d_lb(1) = value;
        input.d_prev_stag(1) = value;
        row.d(1) = 0;
end
input = withResiduals(input, rU, rD, ones(1,4));
end

function input = gateFixture()
input = struct( ...
    'authorization_scope', 'TEST_ONLY_NON_AUTHORIZING_SCOPE', ...
    'case_id', 'T1_initial_defect', ...
    'cycle', 5, ...
    'substep_ordinal', 4, ...
    'evidence_method', 'same_process_post_update_reassembly_v1', ...
    'd_lb', [0.5;0.6], ...
    'd_prev_stag', [0.5;0.6], ...
    'history_pre', reshape(1:4, 1, 4) / 100, ...
    'active_u_dofs', [1;2], ...
    'active_d_dofs', [1;2], ...
    'traction', [0.3;0.4;0.5], ...
    'reassemble_equilibrium', [], ...
    'reassemble_phase', []);
input = withResiduals(input, zeros(3,1), zeros(2,1), ones(1,4));
end

function row = rowFixture(converged)
row = struct( ...
    'u', [0.01;0.02;0.03], ...
    'd', [0.5;0.6], ...
    'stagger_converged', converged);
end

function input = withResiduals(input, rU, rD, rawDriver)
snapshotExpected = struct('d_lb', input.d_lb, 'd_entry', input.d_prev_stag, ...
    'history_pre', input.history_pre, 'traction', input.traction);
input.reassemble_equilibrium = @(snapshot,u,d) equilibriumResult( ...
    snapshot, u, d, snapshotExpected, rU, rawDriver);
input.reassemble_phase = @(snapshot,u,d,raw) phaseResult( ...
    snapshot, u, d, raw, snapshotExpected, rD, rawDriver);
end

function [rU, rawDriver] = equilibriumResult(snapshot, u, d, expected, rU, rawDriver)
assertSnapshot(snapshot, expected);
assert(isequal(size(u), [3 1]) && isequal(size(d), [2 1]));
end

function rD = phaseResult(snapshot, u, d, raw, expected, rD, expectedRaw)
assertSnapshot(snapshot, expected);
assert(isequal(size(u), [3 1]) && isequal(size(d), [2 1]));
assert(isequal(raw, expectedRaw));
end

function assertSnapshot(snapshot, expected)
assert(isequal(snapshot.d_lb, expected.d_lb));
assert(isequal(snapshot.d_entry, expected.d_entry));
assert(isequal(snapshot.history_pre, expected.history_pre));
assert(isequal(snapshot.traction, expected.traction));
end

function varargout = throwReassemblyFailure(varargin) %#ok<STOUT>
error('toyRoadP0:InjectedReassemblyFailure', 'Injected reassembly failure.');
end

function path = receiptPath(root)
path = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
end

function digest = fileSha256(path)
bytes = readBytes(path);
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function writeBytes(path, bytes)
fileId = fopen(path, 'wb');
assert(fileId >= 0);
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, bytes, 'uint8');
end

function bytes = readBytes(path)
fileId = fopen(path, 'rb');
assert(fileId >= 0);
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
end

function rejected = assignmentRejected(callback)
rejected = false;
try
    callback();
catch
    rejected = true;
end
end

function assignTraceProperty(trace, name, value)
trace.(name) = value;
end

function removeRoot(root)
if isfolder(root)
    rmdir(root, 's');
end
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
