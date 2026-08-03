function trace = append_toy_road_c5_stagger_row(trace, rowInput)
%APPEND_TOY_ROAD_C5_STAGGER_ROW Reassemble and append one completed stagger.

localValidateTrace(trace);
requiredRow = {'u','d','stagger_converged'};
localRequire(isstruct(rowInput) && isscalar(rowInput) && ...
    isequal(sort(fieldnames(rowInput)), sort(requiredRow(:))), ...
    'row_input must contain exactly u, d and stagger_converged.');
u = rowInput.u;
d = rowInput.d;
localRequire(localFiniteDoubleColumn(u) && localFiniteDoubleColumn(d) && ...
    isequal(size(d), size(trace.snapshot.d_lb)), ...
    'completed stagger u and d must be finite double columns of locked size.');
localRequire(islogical(rowInput.stagger_converged) && ...
    isscalar(rowInput.stagger_converged), ...
    'stagger_converged must be a scalar logical from the normal solver.');
localRequire(max(trace.snapshot.active_u_dofs) <= numel(u), ...
    'active_u_dofs exceed the completed displacement state.');

count = trace.trace_row_count;
localRequire(trace.lifecycle_state.get() == count && ...
    trace.same_process_reassembly_count == count && ...
    isequal(trace.stagger_ordinals, 1:count), ...
    'the c5 lifecycle is stale, reordered, finalized or poisoned.');
localRequire(strcmp(localFileSha256(trace.trace_path), trace.trace_sha256), ...
    'the c5 trace bytes changed outside the active lifecycle.');
localRequire(trace.lifecycle_state.compareAndSet(count, -(count + 1)), ...
    'the c5 lifecycle was consumed by another append or finalize call.');

[rU, rawDriver] = trace.reassemble_equilibrium(trace.snapshot, u, d);
rD = trace.reassemble_phase(trace.snapshot, u, d, rawDriver);
localRequire(localFiniteDoubleColumn(rU) && isequal(size(rU), size(u)), ...
    'equilibrium reassembly must return one finite residual per displacement DOF.');
localRequire(localFiniteDoubleColumn(rD) && isequal(size(rD), size(d)), ...
    'phase reassembly must return one finite residual per damage DOF.');

activeU = trace.snapshot.active_u_dofs;
activeD = trace.snapshot.active_d_dofs;
dActive = d(activeD);
dLbActive = trace.snapshot.d_lb(activeD);
rDActive = rD(activeD);
displacementResidual = norm(rU(activeU), 2);
rawPhaseResidual = norm(rDActive, 2);
projectedPhaseKkt = norm(dActive - ...
    max(dLbActive, min(1, dActive - rDActive)), inf);
consecutiveDelta = norm(d - trace.d_prev_stag, inf);
primalFeasibility = max([0; trace.snapshot.d_lb(:) - d(:); d(:) - 1]);
metrics = [displacementResidual rawPhaseResidual projectedPhaseKkt ...
    consecutiveDelta primalFeasibility];
localRequire(all(isfinite(metrics)) && all(metrics >= 0), ...
    'fresh c5 metrics must be finite and nonnegative.');

ordinal = count + 1;
line = sprintf('%s,%s,5,4,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g\n', ...
    trace.authorization_scope, trace.case_id, ordinal, ordinal, metrics);
localAppendDurably(trace.trace_path, line);

trace.trace_sha256 = localFileSha256(trace.trace_path);
trace.trace_row_count = ordinal;
trace.same_process_reassembly_count = ordinal;
trace.stagger_ordinals = 1:ordinal;
trace.d_prev_stag = d;
trace.last_row_converged = rowInput.stagger_converged;
trace.lifecycle_state.set(ordinal);
end

function localValidateTrace(trace)
required = {'authorization_scope','case_id','cycle','substep_ordinal', ...
    'evidence_method','snapshot','reassemble_equilibrium','reassemble_phase', ...
    'trace_path','receipt_path','trace_sha256','trace_row_count', ...
    'same_process_reassembly_count','stagger_ordinals','d_prev_stag', ...
    'last_row_converged','lifecycle_state'};
valid = isstruct(trace) && isscalar(trace) && all(isfield(trace, required));
if valid
    valid = strcmp(trace.evidence_method, ...
        'same_process_post_update_reassembly_v1') && trace.cycle == 5 && ...
        trace.substep_ordinal == 4 && isa(trace.lifecycle_state, ...
        'java.util.concurrent.atomic.AtomicInteger') && ...
        isa(trace.reassemble_equilibrium, 'function_handle') && ...
        isa(trace.reassemble_phase, 'function_handle') && ...
        isfile(trace.trace_path) && ~isfolder(trace.receipt_path) && ...
        localNonnegativeInteger(trace.trace_row_count) && ...
        localNonnegativeInteger(trace.same_process_reassembly_count) && ...
        localFiniteDoubleColumn(trace.d_prev_stag) && ...
        islogical(trace.last_row_converged) && isscalar(trace.last_row_converged);
end
localRequire(valid, 'trace is not an active same-process c5 lifecycle.');
end

function localAppendDurably(path, line)
fileId = fopen(path, 'ab');
if fileId < 0
    error('toyRoadP0:PublicationFailed', 'Cannot open c5 trace for append: %s', path);
end
bytes = unicode2native(line, 'US-ASCII');
count = fwrite(fileId, bytes, 'uint8');
closeStatus = fclose(fileId);
if count ~= numel(bytes) || closeStatus ~= 0
    error('toyRoadP0:PublicationFailed', 'Cannot append c5 trace row: %s', path);
end
end

function value = localFiniteDoubleColumn(value)
value = isa(value, 'double') && isreal(value) && iscolumn(value) && ...
    ~isempty(value) && all(isfinite(value));
end

function value = localNonnegativeInteger(value)
value = isa(value, 'double') && isscalar(value) && isfinite(value) && ...
    value >= 0 && value == floor(value);
end

function digest = localFileSha256(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', 'Cannot hash c5 trace: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function localRequire(condition, message)
if ~condition
    error('toyRoadP0:InvalidC5Lifecycle', message);
end
end
