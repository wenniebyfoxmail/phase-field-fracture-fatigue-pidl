function receipt = finalize_toy_road_c5_gate(trace)
%FINALIZE_TOY_ROAD_C5_GATE Bind the converged final row into a PASS receipt.

if ~(builtin('isa', trace, 'ToyRoadC5Trace') && isscalar(trace))
    error('toyRoadP0:InvalidC5Lifecycle', ...
        'trace is not an active same-process c5 lifecycle.');
end
receipt = trace.finalizeGate();
end
