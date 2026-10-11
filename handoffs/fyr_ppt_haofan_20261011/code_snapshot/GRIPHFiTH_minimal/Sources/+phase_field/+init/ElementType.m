% Copyright (C) 2022 ETH Zurich, SIS ID and CompMech D-MAVT
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

classdef ElementType
    %ElementType = Type of finite elements 
    % Supported element types: name is composed by a prefix with the element type (related to the dimension) followed by the number
    %                          of nodes of the element 

    enumeration
        LINE2  % linear 1D element
        LINE3  % quadratic 1D element
        QUAD4  % linear 2D quadrilateral element with 4 nodes
        QUAD8  % quadratc 2D element with 8 nodes (serendipity)
        QUAD9  % quadratc 2D element with 9 nodes (lagrangian)
        TRIA3  % linear 2D triangular element with 3 nodes
        TRIA6  % quadratic 2D triangular element with 6 nodes
        HEXA8  % linear 3D prismatic element with 8 nodes
        HEXA20 % quadratic 3D prismatic element with 20 nodes (serendipity)
        HEXA27 % quadratic 3D prismatic element with 27 nodes (lagrangian)
        TETR4  % linear 3D tetrahedral element with 4 nodes
        TETR10 % quadratic 3D tetrahedral element with 10 nodes
    end
end
