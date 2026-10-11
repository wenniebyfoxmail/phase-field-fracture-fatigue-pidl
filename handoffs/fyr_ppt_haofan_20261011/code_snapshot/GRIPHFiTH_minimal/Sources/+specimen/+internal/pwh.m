function [MESH, GEOM, NODESET, ELEMSET] = ct(args)
%CT generate the mesh for the compact-tension specimen

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
    args.t (1, 1) double {mustBePositive} = 1
end

GEOM.L = 2;
GEOM.B = 3;
GEOM.t = args.t;

% get the mesh
[node, elem] = pwh_mesh;

%prepare the node- and element sets
NODESET.bottom = find(node(:,2)==-GEOM.B/2);
NODESET.bottom_left = NODESET.bottom(1);
NODESET.top = find(node(:,2)==GEOM.B/2);

ELEMSET = struct();


%prepare the mesh struct
num_elem    = size(elem,1);
num_node    = size(node,1);
nel         = 4;
dim       = size(node, 2);
tensors   = dim*(1+(dim-1)/2);

MESH.tensors = dim*(1+(dim-1)/2);
MESH.idx_notch = [];
MESH.node = node;
MESH.num_node = num_node;
MESH.elem = elem;
MESH.num_elem = num_elem;
MESH.nel = nel;
MESH.nel_tract = 2;
MESH.dim = dim;
MESH.tensors = tensors;
MESH.elem_material_id = ones(num_elem, 1);

end
