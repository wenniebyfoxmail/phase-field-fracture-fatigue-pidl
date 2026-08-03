classdef ToyRoadC5TraceSubclassAttack < ToyRoadC5Trace
    %TOYROADC5TRACESUBCLASSATTACK Hostile dispatch fixture for sealing tests.

    methods
        function self = ToyRoadC5TraceSubclassAttack(entryInput, outputRoot)
            self@ToyRoadC5Trace(entryInput, outputRoot);
        end

        function next = appendCompletedStagger(self, ~)
            next = self;
        end

        function receipt = finalizeGate(~)
            receipt = struct('passed', true);
        end

        function value = struct(~)
            value = struct('forged', true);
        end
    end
end
