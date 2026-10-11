function [CRACK_VAR] = crack_discretized(n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name)
%CRACK_DISCRETIZED interpolate and track crack tip
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
    n_cycle (1, 1) double   %current cycle number
    sys (1, 1) handle       %system handle
    CRACK_PAR (1, 1) struct   %Parameters of the crack growth rate tracking
    CRACK_VAR (1, 1) struct   %Variables of the crack growth rate tracking
    p_field (:, 1) double   %phase-field variable
    example_name {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
end

%get cycle increment
dn = n_cycle-CRACK_VAR.crack_discretized(end,1);


% =========================================================================
%find all DOFs above the phase-field threshold for full crack development
crack_DOFs=find(p_field >= CRACK_PAR.crack_thres);
if ~isempty(crack_DOFs)
    
    %find broken node furthest towards the given crack direction
    crack_coords = sys.MESH.node(crack_DOFs,:);
    [~,idx]  = max(crack_coords(:,CRACK_PAR.crack_dir));
    crack_coord = crack_coords(idx,:);

    %compute crack growth
    a = crack_coord(1,CRACK_PAR.crack_dir) - CRACK_PAR.a_offset;
    da = a - CRACK_VAR.crack_discretized(end,3);
else

    %inherit values from last cycle
    a = CRACK_VAR.crack_discretized(end,3);
    da = 0.0;
    crack_coord = CRACK_VAR.crack_discretized(end,5:6);

end


% =========================================================================
%save data
CRACK_VAR.crack_discretized(end+1,:) = [n_cycle dn a da/dn crack_coord(1,:)];

%output data
phase_field.mex.output.dat_output(...
    [n_cycle dn], {'n' 'dn'}, ...
    CRACK_VAR.crack_discretized(end,3:end), {'a', 'da/dn', 'crack_x', 'crack_y'}, ...
    [example_name filesep 'crack_discretized.dat']);


end %function
