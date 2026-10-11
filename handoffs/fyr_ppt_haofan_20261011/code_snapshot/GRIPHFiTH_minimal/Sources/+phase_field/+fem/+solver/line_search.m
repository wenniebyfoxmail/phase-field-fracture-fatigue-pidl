function field_vars = line_search(sys,field_vars, field_vars_old, coupling_vars_in, history_vars_old, active_dof, delta_nr, assembly_fh, D_RHS_tract, tol)

%LINE_SEARCH bisection algorithm in line-search assist for Newton-Raphson routine
%  ...

% Copyright (C) 2021-2023 ETH Zurich, SIS ID aresidual_fhnd CompMech D-MAVT
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
    sys (1, 1) handle
    field_vars (:, :) double
    field_vars_old (:,:) double
    coupling_vars_in (:,:) double
    history_vars_old (:, :, :) double
    active_dof (:, :) double
    delta_nr (:,:) double
    assembly_fh (1, 1) function_handle
    D_RHS_tract (:, 1) double
    tol (1, 1) double {mustBePositive} = 1e-6
end

Delta = zeros(size(field_vars));
Delta(active_dof,1) = delta_nr;
left = 0;
right = 1;

%call assembly routine and subtract RHS from it
[~, R_left, ~, ~] = assembly_fh(...
    sys.MESH, sys.DOFS, sys.GEOM.t,...
    sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
    field_vars, field_vars_old, coupling_vars_in,...
    sys.stress_state.as_number,...
    history_vars_old...
);

if any(D_RHS_tract ~= 0.0)
    R_left = R_left - D_RHS_tract;
end
    
f_left = R_left(active_dof,1)'*delta_nr/norm(delta_nr);

%call assembly routine and subtract RHS from it
[~, R_right, ~, ~] = assembly_fh(...
    sys.MESH, sys.DOFS, sys.GEOM.t,...
    sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
    field_vars + Delta, field_vars_old, coupling_vars_in,...
    sys.stress_state.as_number,...
    history_vars_old...
);

if any(D_RHS_tract ~= 0.0)
    R_right = R_right - D_RHS_tract;
end
    
f_right = R_right(active_dof,1)'*delta_nr/norm(delta_nr);


%check for direction
if f_left*f_right > 0
    middle = 1;
    f_middle =0;
else
    middle = (left+right)/2;

    %call assembly routine and subtract RHS from it
    [~, R_middle, ~, ~] = assembly_fh(...
        sys.MESH, sys.DOFS, sys.GEOM.t,...
        sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
        field_vars + middle*Delta, field_vars_old, coupling_vars_in,...
        sys.stress_state.as_number,...
        history_vars_old...
    );

    if any(D_RHS_tract ~= 0.0)
        R_middle = R_middle - D_RHS_tract;
    end
    
    f_middle = R_middle(active_dof,1)'*delta_nr/norm(delta_nr);
end

%bisection algorithm
while  abs(f_middle) >= tol
    if f_middle*f_left <= 0
        right = middle;
    else 
        left = middle;
        R_left = R_middle;
        f_left = R_left(active_dof,1)'*delta_nr/norm(delta_nr);
    end
    middle = (left+right)/2;

    %call assembly routine and subtract RHS from it
    [~, R_middle, ~, ~] = assembly_fh(...
        sys.MESH, sys.DOFS, sys.GEOM.t,...
        sys.QUADRATURE, sys.MAT_CHAR, sys.CC,...
        field_vars + middle*Delta, field_vars_old, coupling_vars_in,...
        sys.stress_state.as_number,...
        history_vars_old...
    );

    if any(D_RHS_tract ~= 0.0)
        R_middle = R_middle - D_RHS_tract;
    end
        
    f_middle = R_middle(active_dof,1)'*delta_nr/norm(delta_nr);
end

%adjust the field variables
field_vars = field_vars + middle*Delta;
    
end