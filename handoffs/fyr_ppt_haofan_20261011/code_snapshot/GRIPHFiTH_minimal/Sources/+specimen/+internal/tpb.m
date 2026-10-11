function [MESH, GEOM, NODESET, ELEMSET] = tpb(args)
%TPB generate the mesh for the three-point-bending specimen

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
    args.refinement {mustBeMember(args.refinement, {'rough', 'medium', 'fine'})} = 'rough'
    args.t (1, 1) double {mustBePositive} = 1
    args.r_reinforced (1, 1) double {mustBePositive} = 2.5
end

GEOM.L = 200;
GEOM.B = 40;
GEOM.t = args.t;

% get the mesh
[node, elem, support_left,support_right,top_loading,crack_elems, crack_openingnodes] = tpb_mesh;


%find the reinforced nodes and elements based on user-given radius
dist = sqrt((node(:,1)-node(top_loading,1)).^2 + (node(:,2)-node(top_loading,2)).^2);
nodes_reinforced = find(dist<args.r_reinforced);
elems_reinforced = [];
for el = 1:size(elem,1)
    if sum(ismember(elem(el,:),nodes_reinforced))>2
        elems_reinforced = [elems_reinforced el];
    end
end

%prepare the node- and element sets
NODESET.support_left = support_left;
NODESET.support_right = support_right;
NODESET.top_loading = top_loading;
NODESET.crack_openingnodes = crack_openingnodes;
ELEMSET.reinforced = elems_reinforced;
ELEMSET.crack_elems = crack_elems;

%prepare the mesh struct
num_elem    = size(elem,1);
num_node    = size(node,1);
nel         = 4;
dim       = size(node, 2);
tensors   = dim*(1+(dim-1)/2);

MESH.tensors = dim*(1+(dim-1)/2);
MESH.idx_notch = [];%nodes_reinforced;
MESH.node = node;
MESH.num_node = num_node;
MESH.elem = elem;
MESH.num_elem = num_elem;
MESH.nel = nel;
MESH.nel_tract = 2;
MESH.dim = dim;
MESH.tensors = tensors;
MESH.elem_material_id = ones(num_elem, 1);
MESH.elem_material_id(ELEMSET.reinforced) = 2;

end
