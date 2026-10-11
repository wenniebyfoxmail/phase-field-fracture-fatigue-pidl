function [NODE_BOUNDARIES] = set_boundaries(args)
%SET_BOUNDARIES Definition of the boundaries based on defined node sets
%   ...
%
%
%   The following output structure fields are computed from the input arguments:
%
%       fix_X                                      % Nodes coord vector fixed in X direction
%       fix_Y                                      % Nodes coord vector fixed in Y direction
%       disp_X                                     % Nodes coord vector displaced in X direction
%       disp_Y                                     % Nodes coord vector displaced in Y direction
%       tract_X                                    % Nodes coord vector where tractions are applied in X direction
%       tract_Y                                    % Nodes coord vector where tractions are applied in Y direction
%       tract_unique = unique([tract_Y; tract_X]); % Unique nodes coord vector where tractions are applied
%

% Copyright (C) 2021 ETH Zurich, SIS ID and CompMech D-MAVT
%
% Licensed under the Apache License, Version 2.0 (the "License");
% you may not use this file except in compliance with the License.
% You may obtain a copy of the License at
%
%    http://www.apache.org/licenses/LICENSE-2.0
%
% Unless required by applicable law or agreed to in writing, software
% distributed under the License is distributed on an "AS IS" BASIS,
% WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
% See the License for the specific language governing permissions and
% limitations under the License.

arguments
    args.fix_X (:,1) double = [];
    args.fix_Y (:,1) double = [];
    args.disp_X (:,1) double = [];
    args.disp_Y (:,1) double = [];
    args.tract_X (:,1) double = [];
    args.tract_Y (:,1) double = [];
    args.hom_pf (:,1) double = [];
    args.non_hom_pf (:,1) double = [];
end

NODE_BOUNDARIES.fix_X = args.fix_X;
NODE_BOUNDARIES.fix_Y = args.fix_Y;

NODE_BOUNDARIES.disp_X = args.disp_X;
NODE_BOUNDARIES.disp_Y = args.disp_Y;

NODE_BOUNDARIES.tract_X = args.tract_X;
NODE_BOUNDARIES.tract_Y = args.tract_Y;

NODE_BOUNDARIES.tract_unique = unique(...
    [NODE_BOUNDARIES.tract_X; NODE_BOUNDARIES.tract_Y]...
);

NODE_BOUNDARIES.hom_pf = args.hom_pf;
NODE_BOUNDARIES.non_hom_pf = args.non_hom_pf;

end
