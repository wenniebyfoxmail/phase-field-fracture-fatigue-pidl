classdef ToyRoadC5TraceForgedClassAttack < handle
    %TOYROADC5TRACEFORGEDCLASSATTACK Unrelated forged-dispatch fixture.

    properties (SetAccess=private)
        ClassDispatchCount = 0
        AppendDispatchCount = 0
        FinalizeDispatchCount = 0
    end

    methods
        function value = class(self)
            self.ClassDispatchCount = self.ClassDispatchCount + 1;
            value = 'ToyRoadC5Trace';
        end

        function next = appendCompletedStagger(self, ~) %#ok<STOUT>
            self.AppendDispatchCount = self.AppendDispatchCount + 1;
            error('toyRoadP0:ForgedAppendDispatch', ...
                'The forged append method was dispatched.');
        end

        function receipt = finalizeGate(self) %#ok<STOUT>
            self.FinalizeDispatchCount = self.FinalizeDispatchCount + 1;
            error('toyRoadP0:ForgedFinalizeDispatch', ...
                'The forged finalize method was dispatched.');
        end
    end
end
