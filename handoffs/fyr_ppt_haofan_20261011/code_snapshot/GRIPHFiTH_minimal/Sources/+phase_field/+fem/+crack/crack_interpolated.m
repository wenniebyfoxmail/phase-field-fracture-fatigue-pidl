function [CRACK_VAR] = crack_interpolated(n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name)
%CRACK_INTERPOLATED interpolate and track crack tip
% 
% see description of the input arguments below


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
    n_cycle (1, 1) double     %current cycle number
    sys (1, 1) handle         %system handle
    CRACK_PAR (1, 1) struct   %Parameters of the crack growth rate tracking
    CRACK_VAR (1, 1) struct   %Variables of the crack growth rate tracking
    p_field (:, 1) double     %phase-field variable
    example_name {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
end

%get cycle increment
dn = n_cycle-CRACK_VAR.crack_interpolated(end,1);

%already inherit values from last step
a = CRACK_VAR.crack_interpolated(end,3);
da = 0.0;
crack_coord = CRACK_VAR.crack_interpolated(end,5:6);


% ============================PHASE-FIELD INTERPOLATION====================
if ~isempty(CRACK_PAR.crack_elems)
    %get shape function for interpolation point
    Nxi = shape_fun_2D(CRACK_PAR.crack_dir);
    
    %prepare results
    interp = zeros(size(CRACK_PAR.crack_elems,2)*4,3);
    
    %loop through all crack tip elements
    for i = 1:size(CRACK_PAR.crack_elems,2)
        
        %get preliminary information
        crack_elem = CRACK_PAR.crack_elems(1,i);
        elem_nodes = sys.MESH.elem(crack_elem,:);
        elem_coords = sys.MESH.node(elem_nodes,:);
        p_field_elem = p_field(elem_nodes,1);
            
        %interpolate coordinates and phase-field to the coordinates
        coords_interp = Nxi'*elem_coords;
        pf_interp = Nxi'*p_field_elem;
            
        %save results
        interp((1:4)+(i-1)*4,1:2) = coords_interp;
        interp((1:4)+(i-1)*4,3) = pf_interp;
        
    end

elseif ~isempty(CRACK_PAR.crack_nodes)
    
    %get discrete values and directly use them for the interpolation (for linear element ansatz functions, this makes no difference)
    interp = [sys.MESH.node(CRACK_PAR.crack_nodes,1), sys.MESH.node(CRACK_PAR.crack_nodes,2), p_field(CRACK_PAR.crack_nodes,1)];
    
else
    error('for the crack tip interpolation, either crack_elems or crack_nodes must be given (also not both)')
end

%sort interpolated results by x-coordinates
interp = sortrows(interp,CRACK_PAR.crack_dir,'ascend');

% ============================CRACK TIP APPROXIMATION====================

%find point with largest coordinate in crack direction above threshold
broken_max = find(interp(:,3)>=CRACK_PAR.crack_thres,1,'last');

if ~isempty(broken_max)
    
    %get point values surrounding threshold (relies on the ordering of the points in the crack direction)
    try
        x_1 = interp(broken_max,CRACK_PAR.crack_dir);
        x_2 = interp(broken_max+1,CRACK_PAR.crack_dir);
        
        d_1 = interp(broken_max,3);
        d_2 = interp(broken_max+1,3);
        
        %interpolate linearly
        crack_coord_interp = (CRACK_PAR.crack_thres-d_1)/(d_2-d_1) * (x_2-x_1) + x_1;
    catch
        crack_coord_interp = x_1; %for the case that the crack has reached the boundary (broken_max+1 is out of range since there is no neighboring point any more)
    end
    
    %compute crack growth
    if crack_coord_interp > CRACK_VAR.crack_interpolated(end,4+CRACK_PAR.crack_dir)
        a = crack_coord_interp - CRACK_PAR.a_offset;
        da = a - CRACK_VAR.crack_interpolated(end,3);
        crack_coord(1,CRACK_PAR.crack_dir) = crack_coord_interp;
    end
end


% =========================================================================
%save data
CRACK_VAR.crack_interpolated(end+1,:) = [n_cycle dn a da/dn crack_coord(1,:)];

%output data
phase_field.mex.output.dat_output(...
    [n_cycle dn], {'n' 'dn'}, ...
    CRACK_VAR.crack_interpolated(end,3:end), {'a', 'da/dn', 'crack_x', 'crack_y'}, ...
    [example_name filesep 'crack_interpolated.dat']);


%export the phase-field interpolation curve
if CRACK_PAR.export_pf_interp
    if (CRACK_VAR.crack_interpolated(end,4+CRACK_PAR.crack_dir)>=0.5) && (CRACK_VAR.crack_interpolated(end,4+CRACK_PAR.crack_dir)<0.525)

        phase_field.mex.output.dat_output(...
            [n_cycle dn], {'n' 'dn'}, ...
            interp(:,[CRACK_PAR.crack_dir, 3]), {'a', 'd'}, ...
            [example_name filesep 'phasefield_interpolated_' sprintf('%07.0f',n_cycle) '.dat']);
    end
end


end %function

% ============================SHAPE FUNCTIONS, QUAD4 ELEMENT=============================
function Nxi = shape_fun_2D(dir)
    gauss_pts = zeros(4,2);
    gauss_pts(:,3-dir) = -3/4:1/2:3/4;
    for G_pts = length(gauss_pts):-1:1
        xi  = gauss_pts(G_pts, 1);
        eta = gauss_pts(G_pts, 2);
        
        Nxi(:, G_pts) = 0.25 * [(1 - xi) * (1 - eta);
            (1 + xi) * (1 - eta);
            (1 + xi) * (1 + eta);
            (1 - xi) * (1 + eta)];
    end
end
