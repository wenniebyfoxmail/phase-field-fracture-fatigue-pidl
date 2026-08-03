classdef (Sealed, Hidden) ToyRoadP0LocalControlledSystem < handle
    properties (SetAccess = immutable)
        DOFS
        STIFFNESS_MATRIX
        PhaseFieldInput
    end

    methods
        function obj = ToyRoadP0LocalControlledSystem(phaseFieldInput)
            obj.DOFS = struct('active',1:numel(phaseFieldInput));
            obj.STIFFNESS_MATRIX = speye(numel(phaseFieldInput));
            obj.PhaseFieldInput = phaseFieldInput;
        end
    end
end
