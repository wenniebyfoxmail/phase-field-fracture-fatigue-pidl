function trace = begin_toy_road_c5_trace(entryInput, outputRoot)
% Diagnostic observer: delegate the sealed lifecycle, then capture c5 entry.

trace = ToyRoadC5Trace(entryInput, outputRoot);
iteratePath = getenv('TOY_ROAD_DT2_ITERATE_PATH');
localRequire(~isempty(strtrim(iteratePath)), 'D-T2 iterate path is absent.');
localRequire(~isfile(iteratePath), 'D-T2 iterate file already exists.');
parent = fileparts(iteratePath);
localRequire(isfolder(parent), 'D-T2 iterate parent must already exist.');

store = matfile(iteratePath, 'Writable', true);
store.schema_version = 'toy_road_dt2_iterates_v1';
store.d_iterates(numel(entryInput.d_prev_stag), 1001) = 0;
store.d_iterates(:,1) = entryInput.d_prev_stag;
store.d_lb = entryInput.d_lb;
store.history_pre = entryInput.history_pre;
store.active_u_dofs = entryInput.active_u_dofs;
store.active_d_dofs = entryInput.active_d_dofs;
store.traction = entryInput.traction;
store.completed_rows(1,1000) = uint8(0);
end

function localRequire(condition, message)
if ~condition
    error('toyRoadDT2:ObserverFailure', '%s', message);
end
end
