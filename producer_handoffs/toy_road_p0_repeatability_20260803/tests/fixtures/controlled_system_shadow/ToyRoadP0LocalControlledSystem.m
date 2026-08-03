classdef ToyRoadP0LocalControlledSystem < handle
    properties
        DOFS
        STIFFNESS_MATRIX
        PhaseFieldInput
    end

    methods
        function obj = ToyRoadP0LocalControlledSystem(phaseFieldInput)
            marker = getenv('TOY_ROAD_SHADOW_SYSTEM_MARKER');
            if ~isempty(marker)
                java.io.File(marker).createNewFile();
            end
            obj.DOFS = struct('active',1:numel(phaseFieldInput));
            obj.STIFFNESS_MATRIX = speye(numel(phaseFieldInput));
            obj.PhaseFieldInput = phaseFieldInput;
        end
    end
end
