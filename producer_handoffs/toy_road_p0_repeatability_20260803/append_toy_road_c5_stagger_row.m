function trace = append_toy_road_c5_stagger_row(trace, rowInput)
%APPEND_TOY_ROAD_C5_STAGGER_ROW Reassemble and append one completed stagger.

if ~(isa(trace, 'ToyRoadC5Trace') && isscalar(trace))
    error('toyRoadP0:InvalidC5Lifecycle', ...
        'trace is not an active same-process c5 lifecycle.');
end
trace = trace.appendCompletedStagger(rowInput);
end
