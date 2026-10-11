function [SOL_CYCL_VAR] = monitor(SOL_CYCL_VAR,displ,p_field,fat_new,example_name)
%MONITOR_CYCLE function to enable the monitoring of system variables
%
% SOL_CYCL_VAR      table containing the monitored variables
% displ             displacement field array
% p_field           phase field array
% fat_new           fatigue history variable array
% example_name      directory where to store the output file

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

% =======================================================================
%prepare cycle info
n = SOL_CYCL_VAR.n_cycle;
try
    dn = n - SOL_CYCL_VAR.MONITOR.n(end,1);
catch
    dn = 1; %for the very first cycle
end


% =======================================================================
%compute vector norms of numerical solution to be monitored
u_1 = norm(displ(:),1);
u_2 = norm(displ(:),2);
u_inf = max(displ(:));

d_1 = norm(p_field(:),1);
d_2 = norm(p_field(:),2);
d_inf = max(p_field(:));

fat_1 = norm(fat_new(:),1);
fat_2 = norm(fat_new(:),2);
fat_inf = max(fat_new(:));


% =======================================================================
%save results in struct
SOL_CYCL_VAR.MONITOR.n(end+1,:) = [n dn];
SOL_CYCL_VAR.MONITOR.u(end+1,:) = [u_1 u_2 u_inf];
SOL_CYCL_VAR.MONITOR.d(end+1,:) = [d_1 d_2 d_inf];
SOL_CYCL_VAR.MONITOR.fat(end+1,:) = [fat_1 fat_2 fat_inf];


% =======================================================================
%output results
phase_field.mex.output.dat_output(...
        [n dn], {'n' 'dn'}, ...
        [u_1 u_2 u_inf d_1 d_2 d_inf fat_1 fat_2 fat_inf], ...
        {'||u||_1' '||u||_2' '||u||_inf' '||d||_1' '||d||_2' '||d||_inf' '||fat||_1' '||fat||_2' '||fat||_inf'}, ...
        [example_name filesep 'monitorcycle.dat']);

end

