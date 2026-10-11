function [MESH, GEOM, NODESET, ELEMSET] = sens(args)
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
    args.notch_type {mustBeMember(args.notch_type, {'phase_field', 'sharp_notch'})} = 'no_notch'
end

% get the mesh
[MESH, GEOM] = specimen.external.gmsh_import('../../Dependencies/meshes/sens_mesh.m', 't', args.t);

% create the notch
idx_notch = find(abs(MESH.node(:,2))<=1e-12 & MESH.node(:,1)<=1e-12);

if strcmp(args.notch_type, 'sharp_notch')

    % reorder element connectivity for the following steps
    for e=1:size(MESH.elem,1)
        if any(ismember(MESH.elem(e,:), idx_notch))
            elem_coords = [MESH.elem(e,:)' MESH.node(MESH.elem(e,:),1) MESH.node(MESH.elem(e,:),2)];
            MESH.elem(e,:);
            sort_x = sortrows(elem_coords, 2);
            sort_y = sortrows(elem_coords, 3);
            lower_edge = sort_y(1:2,1);
            upper_edge = sort_y(3:4,1);
            left_edge  = sort_x(1:2,1);
            right_edge = sort_x(3:4,1);

            n1 = intersect(lower_edge,right_edge);
            n2 = intersect(lower_edge,left_edge);
            n3 = intersect(upper_edge,left_edge);
            n4 = intersect(upper_edge,right_edge);

            MESH.elem(e,:) = [n4 n3 n2 n1];
        end
    end


    % duplicating nodes for the notch in x direction
    MESH.node = [MESH.node; MESH.node(idx_notch,:)];
    for i = 1:length(idx_notch)
        subst_x = (MESH.elem(:,1) == idx_notch(i,1));
        %subst_x = find(subst_x,1,'first');
        MESH.elem(subst_x,1) = MESH.num_node + i;

        subst_x = (MESH.elem(:,2) == idx_notch(i,1));
        %subst_x = find(subst_x,1,'first');
        MESH.elem(subst_x,2) = MESH.num_node + i;
    end

    % update the node count
    MESH.num_node = length(MESH.node);
    
    %set empty crack nodeset
    NODESET.crack = [];
else
    NODESET.crack = idx_notch;
end

% prepare the node- and element sets
NODESET.top_edge = find(MESH.node(:,2)==0.5);
NODESET.bot_edge = find(MESH.node(:,2)==-0.5);

ELEMSET.all = linspace(1,MESH.num_elem,MESH.num_elem)';

end
