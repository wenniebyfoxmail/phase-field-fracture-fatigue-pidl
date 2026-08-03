classdef ToyRoadP0MaliciousReceiptValue < handle
    properties (Access = private)
        MarkerPath
    end

    methods
        function obj = ToyRoadP0MaliciousReceiptValue(markerPath)
            obj.MarkerPath = markerPath;
        end

        function value = char(obj)
            obj.touchMarker();
            value = 'PASS';
        end

        function varargout = subsref(obj,index)
            obj.touchMarker();
            [varargout{1:nargout}] = builtin('subsref',obj,index);
        end

        function count = numel(obj,varargin)
            obj.touchMarker();
            count = builtin('numel',obj,varargin{:});
        end
    end

    methods (Access = private)
        function touchMarker(obj)
            java.io.File(obj.MarkerPath).createNewFile();
        end
    end
end
