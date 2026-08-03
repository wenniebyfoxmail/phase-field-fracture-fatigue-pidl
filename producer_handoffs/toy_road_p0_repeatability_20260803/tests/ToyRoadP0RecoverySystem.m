classdef (Sealed) ToyRoadP0RecoverySystem < handle
    properties (SetAccess = immutable)
        DOFS
        STIFFNESS_MATRIX
        PhaseFieldInput
    end

    methods
        function obj = ToyRoadP0RecoverySystem(phaseFieldInput)
            obj.DOFS = struct('active',1:numel(phaseFieldInput));
            obj.STIFFNESS_MATRIX = speye(numel(phaseFieldInput));
            obj.PhaseFieldInput = phaseFieldInput;
        end
    end
end
