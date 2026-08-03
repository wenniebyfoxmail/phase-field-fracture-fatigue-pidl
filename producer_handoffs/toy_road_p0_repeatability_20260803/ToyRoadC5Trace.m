classdef (Sealed) ToyRoadC5Trace < handle
    %TOYROADC5TRACE Non-mutable single-use handle for one c5 lifecycle lease.

    properties (SetAccess=private, GetAccess=private)
        AuthorizationScope
        CaseId
        EvidenceMethod
        Snapshot
        ReassembleEquilibrium
        ReassemblePhase
        TracePath
        ReceiptPath
        TraceSha256
        TraceRowCount
        ReassemblyCount
        StaggerOrdinals
        DPreviousStagger
        LastRowConverged
        LifecycleState (1,1) double = NaN
    end

    properties (Dependent, SetAccess=private)
        authorization_scope
        case_id
        cycle
        substep_ordinal
        evidence_method
        trace_path
        receipt_path
        trace_sha256
        trace_row_count
        same_process_reassembly_count
        stagger_ordinals
        last_row_converged
    end

    methods
        function self = ToyRoadC5Trace(entryInput, outputRoot)
            if nargin == 0
                return;
            end
            localInputRequire(nargin == 2, ...
                'the c5 lifecycle requires entry_input and outputRoot.');
            required = {'authorization_scope','case_id','cycle', ...
                'substep_ordinal','evidence_method','d_lb','d_prev_stag', ...
                'history_pre','active_u_dofs','active_d_dofs','traction', ...
                'reassemble_equilibrium','reassemble_phase'};
            localInputRequire(isstruct(entryInput) && isscalar(entryInput) && ...
                isequal(sort(fieldnames(entryInput)), sort(required(:))), ...
                'entry_input must contain exactly the c5 gate fields.');

            authorizationScope = localCsvText( ...
                entryInput.authorization_scope, 'authorization_scope');
            caseId = localCaseId(entryInput.case_id);
            localInputRequire(localIntegerEquals(entryInput.cycle, 5) && ...
                localIntegerEquals(entryInput.substep_ordinal, 4), ...
                'the numerical gate is restricted to physical c5/substep 4.');
            evidenceMethod = localText(entryInput.evidence_method, ...
                'evidence_method');
            localInputRequire(strcmp(evidenceMethod, ...
                'same_process_post_update_reassembly_v1'), ...
                'the c5 gate must use same-process post-update reassembly.');

            dLb = entryInput.d_lb;
            dPrevious = entryInput.d_prev_stag;
            localInputRequire(localFiniteDoubleColumn(dLb) && ...
                localFiniteDoubleColumn(dPrevious) && ...
                isequal(size(dLb), size(dPrevious)), ...
                'd_lb and d_prev_stag must be matching finite double columns.');
            localInputRequire(all(dLb >= 0) && all(dLb <= 1) && ...
                max(abs(dPrevious - dLb), [], 'all') <= 1e-12, ...
                'the accepted entry damage must equal the bounded lower-bound state.');
            historyPre = entryInput.history_pre;
            localInputRequire(isa(historyPre, 'double') && isreal(historyPre) && ...
                ~isempty(historyPre) && all(isfinite(historyPre), 'all'), ...
                'history_pre must be a nonempty finite double array.');
            activeU = localActiveDofs(entryInput.active_u_dofs, Inf, ...
                'active_u_dofs');
            activeD = localActiveDofs(entryInput.active_d_dofs, numel(dLb), ...
                'active_d_dofs');
            traction = entryInput.traction;
            localInputRequire(localFiniteDoubleColumn(traction), ...
                'traction must be a nonempty finite double column.');
            localInputRequire(isa(entryInput.reassemble_equilibrium, ...
                'function_handle') && isa(entryInput.reassemble_phase, ...
                'function_handle'), ...
                'both same-process reassembly operators must be callable.');
            localRequireText(outputRoot, ...
                'outputRoot must be nonempty scalar text.');
            root = char(outputRoot);
            localInputRequire(isfolder(root), ...
                'outputRoot must already exist.');

            qualification = fullfile(root, 'qualification');
            localCreateDirectory(qualification);
            tracePath = fullfile(qualification, 'C5_STAGGER_TRACE.csv');
            receiptPath = fullfile(qualification, ...
                'C5_NUMERICAL_GATE_RECEIPT.json');
            header = ['authorization_scope,case_id,cycle,substep_ordinal,' ...
                'stagger_iteration,reassembly_ordinal,displacement_residual,' ...
                'raw_phase_residual,projected_phase_kkt,' ...
                'consecutive_stagger_delta,primal_feasibility' newline];
            localCreateExclusiveText(tracePath, header);

            self.AuthorizationScope = authorizationScope;
            self.CaseId = caseId;
            self.EvidenceMethod = evidenceMethod;
            self.Snapshot = struct( ...
                'd_lb', dLb, ...
                'd_entry', dPrevious, ...
                'history_pre', historyPre, ...
                'active_u_dofs', activeU, ...
                'active_d_dofs', activeD, ...
                'traction', traction);
            self.ReassembleEquilibrium = entryInput.reassemble_equilibrium;
            self.ReassemblePhase = entryInput.reassemble_phase;
            self.TracePath = tracePath;
            self.ReceiptPath = receiptPath;
            self.TraceSha256 = localFileSha256(tracePath);
            self.TraceRowCount = 0;
            self.ReassemblyCount = 0;
            self.StaggerOrdinals = zeros(1,0);
            self.DPreviousStagger = dPrevious;
            self.LastRowConverged = false;
            self.LifecycleState = 0;
        end
    end

    methods (Sealed)
        function next = appendCompletedStagger(self, rowInput)
            self.validateActiveLifecycle();
            required = {'u','d','stagger_converged'};
            localLifecycleRequire(isstruct(rowInput) && isscalar(rowInput) && ...
                isequal(sort(fieldnames(rowInput)), sort(required(:))), ...
                'row_input must contain exactly u, d and stagger_converged.');
            u = rowInput.u;
            d = rowInput.d;
            localLifecycleRequire(localFiniteDoubleColumn(u) && ...
                localFiniteDoubleColumn(d) && ...
                isequal(size(d), size(self.Snapshot.d_lb)), ...
                ['completed stagger u and d must be finite double columns ' ...
                'of locked size.']);
            localLifecycleRequire(islogical(rowInput.stagger_converged) && ...
                isscalar(rowInput.stagger_converged), ...
                ['stagger_converged must be a scalar logical from the ' ...
                'normal solver.']);
            localLifecycleRequire(max(self.Snapshot.active_u_dofs) <= numel(u), ...
                'active_u_dofs exceed the completed displacement state.');
            localLifecycleRequire(strcmp(localFileSha256(self.TracePath), ...
                self.TraceSha256), ...
                'the c5 trace bytes changed outside the active lifecycle.');

            count = self.TraceRowCount;
            localLifecycleRequire(self.LifecycleState == count, ...
                'the c5 lifecycle was consumed by another append or finalize call.');
            self.LifecycleState = -(count + 1);
            [rU, rawDriver] = self.ReassembleEquilibrium( ...
                self.Snapshot, u, d);
            rD = self.ReassemblePhase(self.Snapshot, u, d, rawDriver);
            localLifecycleRequire(localFiniteDoubleColumn(rU) && ...
                isequal(size(rU), size(u)), ...
                ['equilibrium reassembly must return one finite residual ' ...
                'per displacement DOF.']);
            localLifecycleRequire(localFiniteDoubleColumn(rD) && ...
                isequal(size(rD), size(d)), ...
                ['phase reassembly must return one finite residual per ' ...
                'damage DOF.']);

            activeU = self.Snapshot.active_u_dofs;
            activeD = self.Snapshot.active_d_dofs;
            dActive = d(activeD);
            dLbActive = self.Snapshot.d_lb(activeD);
            rDActive = rD(activeD);
            displacementResidual = norm(rU(activeU), 2);
            rawPhaseResidual = norm(rDActive, 2);
            projectedPhaseKkt = norm(dActive - ...
                max(dLbActive, min(1, dActive - rDActive)), inf);
            consecutiveDelta = norm(d - self.DPreviousStagger, inf);
            primalFeasibility = max([0; self.Snapshot.d_lb(:) - d(:); ...
                d(:) - 1]);
            metrics = [displacementResidual rawPhaseResidual ...
                projectedPhaseKkt consecutiveDelta primalFeasibility];
            localLifecycleRequire(all(isfinite(metrics)) && all(metrics >= 0), ...
                'fresh c5 metrics must be finite and nonnegative.');

            ordinal = count + 1;
            line = sprintf( ...
                '%s,%s,5,4,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g\n', ...
                self.AuthorizationScope, self.CaseId, ordinal, ordinal, metrics);
            localAppendDurably(self.TracePath, line);
            next = self.createSuccessor( ...
                ordinal, d, rowInput.stagger_converged);
        end

        function receipt = finalizeGate(self)
            self.validateActiveLifecycle();
            count = self.TraceRowCount;
            localLifecycleRequire(count > 0, ...
                'at least one completed stagger row is required.');
            localLifecycleRequire(self.LastRowConverged, ...
                ['the final appended row was not declared converged by ' ...
                'the normal solver.']);
            traceSha256 = localFileSha256(self.TracePath);
            localLifecycleRequire(strcmp(traceSha256, self.TraceSha256), ...
                'the c5 trace bytes changed outside the active lifecycle.');
            localLifecycleRequire(self.LifecycleState == count, ...
                'the c5 lifecycle was already finalized, copied or poisoned.');
            self.LifecycleState = -(1000000 + count);

            rows = self.readValidatedRows(count);
            last = count;
            thresholds = struct( ...
                'displacement_residual_threshold', 4e-4, ...
                'projected_phase_kkt_threshold', 4e-4, ...
                'consecutive_stagger_delta_threshold', 1e-3, ...
                'primal_feasibility_threshold', 1e-12);
            passed = rows.displacement_residual(last) <= ...
                thresholds.displacement_residual_threshold && ...
                rows.projected_phase_kkt(last) <= ...
                thresholds.projected_phase_kkt_threshold && ...
                rows.consecutive_stagger_delta(last) <= ...
                thresholds.consecutive_stagger_delta_threshold && ...
                rows.primal_feasibility(last) <= ...
                thresholds.primal_feasibility_threshold;
            if ~passed
                error('toyRoadP0:C5GateFailed', ...
                    ['The converged c5/s4 row failed a mandatory ' ...
                    'numerical gate.']);
            end

            receipt = struct( ...
                'authorization_scope', self.AuthorizationScope, ...
                'case_id', self.CaseId, ...
                'cycle', 5, ...
                'substep_ordinal', 4, ...
                'status', 'PASS', ...
                'passed', true, ...
                'trace_sha256', traceSha256, ...
                'trace_row_count', count, ...
                'reassembly_count', count, ...
                'final_stagger_iteration', rows.stagger_iteration(last), ...
                'final_reassembly_ordinal', rows.reassembly_ordinal(last), ...
                'final_displacement_residual', ...
                    rows.displacement_residual(last), ...
                'final_raw_phase_residual', rows.raw_phase_residual(last), ...
                'final_projected_phase_kkt', ...
                    rows.projected_phase_kkt(last), ...
                'final_consecutive_stagger_delta', ...
                    rows.consecutive_stagger_delta(last), ...
                'final_primal_feasibility', rows.primal_feasibility(last), ...
                'displacement_residual_threshold', ...
                    thresholds.displacement_residual_threshold, ...
                'projected_phase_kkt_threshold', ...
                    thresholds.projected_phase_kkt_threshold, ...
                'consecutive_stagger_delta_threshold', ...
                    thresholds.consecutive_stagger_delta_threshold, ...
                'primal_feasibility_threshold', ...
                    thresholds.primal_feasibility_threshold);
            localPublishJsonExclusive(self.ReceiptPath, receipt);
        end

        function value = struct(~) %#ok<STOUT>
            error('toyRoadP0:C5StructConversionBlocked', ...
                ['Direct struct conversion is blocked; copied values are ' ...
                'not lifecycle authority.']);
        end
    end

    methods
        function value = get.authorization_scope(self)
            value = self.AuthorizationScope;
        end

        function value = get.case_id(self)
            value = self.CaseId;
        end

        function value = get.cycle(~)
            value = 5;
        end

        function value = get.substep_ordinal(~)
            value = 4;
        end

        function value = get.evidence_method(self)
            value = self.EvidenceMethod;
        end

        function value = get.trace_path(self)
            value = self.TracePath;
        end

        function value = get.receipt_path(self)
            value = self.ReceiptPath;
        end

        function value = get.trace_sha256(self)
            value = self.TraceSha256;
        end

        function value = get.trace_row_count(self)
            value = self.TraceRowCount;
        end

        function value = get.same_process_reassembly_count(self)
            value = self.ReassemblyCount;
        end

        function value = get.stagger_ordinals(self)
            value = self.StaggerOrdinals;
        end

        function value = get.last_row_converged(self)
            value = self.LastRowConverged;
        end
    end

    methods (Access=private)
        function validateActiveLifecycle(self)
            count = self.TraceRowCount;
            valid = localNonnegativeInteger(count) && ...
                isfile(self.TracePath) && ~isfolder(self.ReceiptPath) && ...
                self.ReassemblyCount == count && ...
                isequal(self.StaggerOrdinals, 1:count) && ...
                localFiniteDoubleColumn(self.DPreviousStagger) && ...
                islogical(self.LastRowConverged) && ...
                isscalar(self.LastRowConverged) && ...
                self.LifecycleState == count;
            localLifecycleRequire(valid, ...
                'the c5 lifecycle is stale, reordered, finalized or poisoned.');
        end

        function next = createSuccessor(self, ordinal, d, converged)
            next = ToyRoadC5Trace();
            next.AuthorizationScope = self.AuthorizationScope;
            next.CaseId = self.CaseId;
            next.EvidenceMethod = self.EvidenceMethod;
            next.Snapshot = self.Snapshot;
            next.ReassembleEquilibrium = self.ReassembleEquilibrium;
            next.ReassemblePhase = self.ReassemblePhase;
            next.TracePath = self.TracePath;
            next.ReceiptPath = self.ReceiptPath;
            next.TraceSha256 = localFileSha256(self.TracePath);
            next.TraceRowCount = ordinal;
            next.ReassemblyCount = ordinal;
            next.StaggerOrdinals = 1:ordinal;
            next.DPreviousStagger = d;
            next.LastRowConverged = converged;
            next.LifecycleState = ordinal;
        end

        function rows = readValidatedRows(self, count)
            rows = readtable(self.TracePath, 'TextType', 'string', ...
                'VariableNamingRule', 'preserve');
            columns = {'authorization_scope','case_id','cycle', ...
                'substep_ordinal','stagger_iteration','reassembly_ordinal', ...
                'displacement_residual','raw_phase_residual', ...
                'projected_phase_kkt','consecutive_stagger_delta', ...
                'primal_feasibility'};
            localLifecycleRequire(isequal( ...
                rows.Properties.VariableNames, columns) && ...
                height(rows) == count, ...
                'the c5 trace schema or row count is invalid.');
            localLifecycleRequire(all(rows.authorization_scope == ...
                string(self.AuthorizationScope)) && ...
                all(rows.case_id == string(self.CaseId)) && ...
                all(rows.cycle == 5) && all(rows.substep_ordinal == 4) && ...
                isequal(rows.stagger_iteration, (1:count).') && ...
                isequal(rows.reassembly_ordinal, (1:count).'), ...
                'the c5 trace identity or ordinal sequence is invalid.');
            metrics = rows{:,7:end};
            localLifecycleRequire(isa(metrics, 'double') && isreal(metrics) && ...
                all(isfinite(metrics), 'all') && all(metrics >= 0, 'all'), ...
                'the c5 trace metrics must be finite nonnegative doubles.');
        end
    end
end

function dofs = localActiveDofs(dofs, maximum, label)
localInputRequire(isa(dofs, 'double') && iscolumn(dofs) && ~isempty(dofs) && ...
    all(isfinite(dofs)) && all(dofs == floor(dofs)) && all(dofs >= 1) && ...
    all(dofs <= maximum) && numel(unique(dofs)) == numel(dofs), ...
    '%s must be unique positive double integer indices.', label);
end

function value = localCaseId(value)
value = localCsvText(value, 'case_id');
roles = {'P0_parent','P0R_parent_repeat','T1_initial_defect', ...
    'T2_material_state','T3_loading_history'};
localInputRequire(any(strcmp(value, roles)), ...
    'case_id is not a locked family role.');
end

function value = localCsvText(value, label)
value = localText(value, label);
localInputRequire(~isempty(value) && ...
    ~any(contains(value, {',', newline, char(13)})), ...
    '%s cannot be empty or contain CSV delimiters.', label);
end

function value = localText(value, label)
valid = (ischar(value) && isrow(value)) || ...
    (isstring(value) && isscalar(value) && ~ismissing(value));
localInputRequire(valid, '%s must be scalar text.', label);
value = char(value);
end

function localRequireText(value, message)
valid = (ischar(value) && isrow(value) && ~isempty(value)) || ...
    (isstring(value) && isscalar(value) && strlength(value) > 0);
localInputRequire(valid, message);
end

function value = localFiniteDoubleColumn(value)
value = isa(value, 'double') && isreal(value) && iscolumn(value) && ...
    ~isempty(value) && all(isfinite(value));
end

function value = localNonnegativeInteger(value)
value = isa(value, 'double') && isscalar(value) && isfinite(value) && ...
    value >= 0 && value == floor(value);
end

function value = localIntegerEquals(actual, expected)
value = isa(actual, 'double') && isscalar(actual) && isfinite(actual) && ...
    actual == expected;
end

function localCreateDirectory(path)
if isfolder(path)
    return;
end
localInputRequire(~isfile(path), ...
    'qualification path is not a directory.');
[created, message] = mkdir(path);
if ~created
    error('toyRoadP0:PublicationFailed', ...
        'Cannot create qualification directory: %s', message);
end
end

function localCreateExclusiveText(path, content)
if isfile(path) || isfolder(path)
    error('toyRoadP0:PublicationClobber', ...
        'Refusing to overwrite c5 trace destination: %s', path);
end
try
    created = java.io.File(path).createNewFile();
catch exception
    error('toyRoadP0:PublicationFailed', ...
        'Cannot reserve c5 trace destination: %s', exception.message);
end
if ~created
    error('toyRoadP0:PublicationClobber', ...
        'Refusing to overwrite c5 trace destination: %s', path);
end
committed = java.util.concurrent.atomic.AtomicBoolean(false);
cleanup = onCleanup(@() localDeleteUncommitted(path, committed));
fileId = fopen(path, 'wb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot open c5 trace: %s', path);
end
bytes = unicode2native(content, 'US-ASCII');
count = fwrite(fileId, bytes, 'uint8');
closeStatus = fclose(fileId);
if count ~= numel(bytes) || closeStatus ~= 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot write c5 trace header: %s', path);
end
committed.set(true);
clear cleanup
end

function localDeleteUncommitted(path, committed)
if ~committed.get() && isfile(path)
    delete(path);
end
end

function localAppendDurably(path, line)
fileId = fopen(path, 'ab');
if fileId < 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot open c5 trace for append: %s', path);
end
bytes = unicode2native(line, 'US-ASCII');
count = fwrite(fileId, bytes, 'uint8');
closeStatus = fclose(fileId);
if count ~= numel(bytes) || closeStatus ~= 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot append c5 trace row: %s', path);
end
end

function localPublishJsonExclusive(path, payload)
if isfile(path) || isfolder(path)
    error('toyRoadP0:PublicationClobber', ...
        'Refusing to overwrite c5 receipt destination: %s', path);
end
directory = fileparts(path);
temporaryPath = localCreateReservedTemporary(directory);
cleanup = onCleanup(@() localDeleteIfPresent(temporaryPath));
fileId = fopen(temporaryPath, 'wb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot open temporary c5 receipt: %s', temporaryPath);
end
content = [jsonencode(payload) newline];
bytes = unicode2native(content, 'UTF-8');
count = fwrite(fileId, bytes, 'uint8');
closeStatus = fclose(fileId);
if count ~= numel(bytes) || closeStatus ~= 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot write temporary c5 receipt: %s', temporaryPath);
end
try
    java.nio.file.Files.createLink(java.io.File(path).toPath(), ...
        java.io.File(temporaryPath).toPath());
catch exception
    if isfile(path) || isfolder(path)
        error('toyRoadP0:PublicationClobber', ...
            'Refusing to overwrite c5 receipt destination: %s', path);
    end
    error('toyRoadP0:PublicationFailed', ...
        'Cannot exclusively publish c5 receipt: %s', exception.message);
end
localDeleteIfPresent(temporaryPath);
clear cleanup
end

function path = localCreateReservedTemporary(directory)
try
    attributes = javaArray('java.nio.file.attribute.FileAttribute', 0);
    temporary = java.nio.file.Files.createTempFile( ...
        java.io.File(directory).toPath(), '.c5_receipt_', '.json', attributes);
    path = char(temporary.toString());
catch exception
    error('toyRoadP0:PublicationFailed', ...
        'Cannot reserve temporary c5 receipt: %s', exception.message);
end
end

function localDeleteIfPresent(path)
if isfile(path)
    delete(path);
end
end

function digest = localFileSha256(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', ...
        'Cannot hash c5 trace: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function localInputRequire(condition, message, varargin)
if ~condition
    error('toyRoadP0:InvalidC5Input', message, varargin{:});
end
end

function localLifecycleRequire(condition, message)
if ~condition
    error('toyRoadP0:InvalidC5Lifecycle', message);
end
end
