classdef (Sealed) ToyRoadP0ForgedSealedAdapter < handle
    properties (Constant)
        CONTROLLED_IDENTITY = 'toy_road_p0_controlled_driver_adapter_v1'
    end

    methods
        function dependencies = sealedDependencies(~)
            dependencies = struct( ...
                'load_parent_mesh',@forgedOperator, ...
                'build_recovery_input',@forgedOperator, ...
                'build_solver_context',@forgedOperator, ...
                'runtime_receipt',@forgedOperator, ...
                'solve_family_case',@forgedOperator);
        end
    end
end

function varargout = forgedOperator(varargin)
localTouchMarker(getenv('TOY_ROAD_FORGED_OPERATOR_MARKER'));
varargout = cell(1,nargout); %#ok<NASGU>
error('toyRoadP0Test:ForgedOperatorReached', ...
    'A forged controlled identity reached an arbitrary operator.');
end

function localTouchMarker(path)
if ~isempty(path)
    java.io.File(path).createNewFile();
end
end
