function trace = append_toy_road_c5_stagger_row(trace, rowInput)
% Diagnostic observer: first delegate the sealed append, then persist state.

trace = trace.appendCompletedStagger(rowInput);
iteratePath = getenv('TOY_ROAD_DT2_ITERATE_PATH');
localRequire(isfile(iteratePath), 'D-T2 iterate file is absent.');
ordinal = trace.trace_row_count;
localRequire(ordinal >= 1 && ordinal <= 1000, 'D-T2 row ordinal is invalid.');

store = matfile(iteratePath, 'Writable', true);
if ordinal == 1
    store.u_iterates(numel(rowInput.u), 1000) = 0;
end
store.u_iterates(:,ordinal) = rowInput.u;
store.d_iterates(:,ordinal+1) = rowInput.d;
store.completed_rows(1,ordinal) = uint8(1);
if trace.last_row_converged
    error('toyRoadDT2:StopAfterC5', ...
        'D-T2 diagnostic stops immediately after the completed c5/s4 iterate.');
end
end

function localRequire(condition, message)
if ~condition
    error('toyRoadDT2:ObserverFailure', '%s', message);
end
end
