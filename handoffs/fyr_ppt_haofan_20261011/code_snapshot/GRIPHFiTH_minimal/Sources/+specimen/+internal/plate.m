function [MESH, GEOM, NODESETS, ELEMSETS] = plate(args)
% PLATE internal generation of plate specimen, i.e. mesh and geometry definition
%
% `notch_type` possible values:
%
%
%  The following keyword arguments can be set, otherwise, are set with default values:
%
%       notch_type = 'no_notch';  % Notch type; possible values:
%                                 %   'no_notch'    -> Simple plate with no notch
%                                 %   'phase_field' -> Imposed with Dirichlet BC on phase field
%                                 %   'sharp_notch' -> Duplication of the nodes across the notch
%
%       Lref_x = 0;  % Refinment length in x direction (in center)
%       Lref_y = 0;  % Refinment length in y direction (in center)
%
%       Nx = 10;  % Elements in x direction
%       Ny = 10;  % Elements in y direction
%
%       Nref_x = 0;  % Elements in the refined zone (x dir.)
%       Nref_y = 0;  % Elements in refined zone (y dir.)
%
%       x_notch  = 0.5;   % x coord. of the notch
%       Lnotch_y = 0.00;  % Length of the notch (y dir.) -> notch (x_notch, 0) --> (x_notch, Lnotch_y)
%
%       y_notch  = 0;  % y coord. of the notch
%       Lnotch_x = 0;  % Length of the notch (x dir.) -> notch (y_notch, 0) --> (y_notch, Lnotch_x)
%
%   The following output structure fields can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       nel_tract = 2;  % number of nodes with tractions per element (max. `nel`)
%
%   The following output structure fields are additionaly computed from the input
%   arguments:
%
%       idx_notch   % Notch indices in `node` for the `notch_type='phase_field'`
%       node        % nodes coord vector [x y]
%       num_node    % total number of nodes
%       elem        % nodes connectivity matrix
%       num_elem    % total number of elements
%       nel         % number of nodes per element
%       nel_tract   % number of nodes with tractions per element
%       dim         % dimension of the problem
%       tensors     % size of the tensors in Voigt notation
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
    args.L (1, 1) double {mustBePositive} = 1
    args.B (1, 1) double {mustBePositive} = 1
    args.t (1, 1) double {mustBePositive} = 1
    args.notch_type {mustBeMember(args.notch_type, {'no_notch', 'phase_field', 'sharp_notch'})} = 'no_notch'
    args.Lref_x (1, 1) double {mustBeNonnegative} = 0
    args.Lref_y (1, 1) double {mustBeNonnegative} = 0
    args.Nx (1, 1) double {mustBeInteger, mustBePositive} = 10
    args.Ny (1, 1) double {mustBeInteger, mustBePositive} = 10
    args.Nref_x (1, 1) double {mustBeInteger, mustBeNonnegative} = 0
    args.Nref_y (1, 1) double {mustBeInteger, mustBeNonnegative} = 0
    args.x_notch (1, 1) double {mustBeNonnegative} = 0.5
    args.Lnotch_y (1, 1) double {mustBeNonnegative} = 0.0
    args.y_notch (1, 1) double {mustBeNonnegative} = 0.0
    args.Lnotch_x (1, 1) double {mustBeNonnegative} = 0.0
    args.nel_tract (1, 1) double {mustBeInteger, mustBePositive} = 2
end

GEOM.L = args.L;
GEOM.B = args.B;
GEOM.t = args.t;

notch_type = args.notch_type;
Lref_x     = args.Lref_x;
Lref_y     = args.Lref_y;
Nx         = args.Nx;
Ny         = args.Ny;
Nref_x     = args.Nref_x;
Nref_y     = args.Nref_y;
x_notch    = args.x_notch;
Lnotch_y   = args.Lnotch_y;
y_notch    = args.y_notch;
Lnotch_x   = args.Lnotch_x;


if strcmp(notch_type, 'no_notch')

    % Create rectangular mesh
    [node, elem, num_elem, nel, num_node] = MeshRectanglularPlate(args.L, args.B, Nx, Ny);
    idx_notch = [];

else  % strcmp(notch_type, 'phase_field') || strcmp(notch_type, 'sharp_notch')

    % Create rectangular mesh with a notch
    [node, elem, num_elem, nel, num_node] = MeshRectanglularPlate_notch(...
        args.L, args.B, Nx, Ny, Lref_x, Lref_y, Nref_x, Nref_y...
        );
    % Nodes along the notch in x direction
    if Lnotch_y == 0
        idx_notch_y = [];
    else
        idx_notch_y = find(abs(node(:,1)-x_notch)<=1e-12 & node(:,2)-Lnotch_y<=1e-12);
    end
    % Nodes along the notch in y direction
    if Lnotch_x == 0
        idx_notch_x = [];
    else
        idx_notch_x = find(abs(node(:,2)-y_notch)<=1e-12 & node(:,1)-Lnotch_x<=1e-12);
    end

    idx_notch = [idx_notch_y; idx_notch_x];

    if strcmp(notch_type, 'sharp_notch') %FOR A SHARP NOTCH
        % Duplicating nodes for the notch in y direction---------------------
        node = [node; node(idx_notch_y,:)];
        for i = 1:length(idx_notch_y)
            subst_y = (elem(:,2) == idx_notch_y(i,1));
            elem(subst_y,2) = num_node + i;

            subst_y = (elem(:,3) == idx_notch_y(i,1));
            elem(subst_y,3) = num_node + i;
        end
        num_node = length(node);
        %--------------------------------------------------------------------

        % Duplicating nodes for the notch in x direction---------------------
        node = [node; node(idx_notch_x,:)];
        for i = 1:length(idx_notch_x)
            subst_x = (elem(:,3) == idx_notch_x(i,1));
            elem(subst_x,3) = num_node + i;

            subst_x = (elem(:,4) == idx_notch_x(i,1));
            elem(subst_x,4) = num_node + i;
        end
        num_node = length(node);
        %--------------------------------------------------------------------
        idx_notch =[];
    end

end

% Size of the problem
dim       = size(node, 2);
tensors   = dim*(1+(dim-1)/2);
nel_tract = min(args.nel_tract, nel);

MESH.tensors = dim*(1+(dim-1)/2);
MESH.node = node;
MESH.num_node = num_node;
MESH.elem = elem;
MESH.num_elem = num_elem;
MESH.nel = nel;
MESH.nel_tract = nel_tract;
MESH.dim = dim;
MESH.tensors = tensors;
MESH.elem_material_id = ones(num_elem, 1);

%create node sets
NODESETS = containers.Map('KeyType', 'char', 'ValueType', 'any');

left_mask   = node(:,1)==0;
right_mask  = node(:,1)==GEOM.L;
bottom_mask = node(:,2)==0;
top_mask    = node(:,2)==GEOM.B;

NODESETS('left')   = find(left_mask);
NODESETS('right')  = find(right_mask);
NODESETS('bottom') = find(bottom_mask);
NODESETS('top')    = find(top_mask);

NODESETS('bottom_left')  = find(bottom_mask & left_mask);
NODESETS('bottom_right') = find(bottom_mask & right_mask);
NODESETS('top_left')     = find(top_mask    & left_mask);
NODESETS('top_right')    = find(top_mask    & right_mask);

NODESETS('crack') = idx_notch;

NODESETS('none') = [];

%create element sets
ELEMSETS = containers.Map('KeyType', 'char', 'ValueType', 'any');

ELEMSETS('all') = transpose(1:num_elem);
ELEMSETS('none') = [];


end
