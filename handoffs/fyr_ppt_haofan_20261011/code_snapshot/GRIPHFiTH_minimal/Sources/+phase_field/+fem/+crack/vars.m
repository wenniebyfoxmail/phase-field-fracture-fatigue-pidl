function [CRACK_VAR] = vars(CRACK_PAR, args)
%VARS Create crack tip tracking table
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
    CRACK_PAR (1, 1) struct
    args.n_resolved (1,1) double  = 0; %number of explicitly computed cycles
    args.crack_discretized (:, 6) double = zeros(1, 6); %n, dn, a, dadn, x, y
    args.crack_regularized (:, 5) double = zeros(1, 5); %n, dn, a, dadn, int_d
    args.crack_interpolated (:, 6) double = zeros(1, 6); %n, dn, a, dadn, x, y
    args.cgr_discretized (:,2) double = zeros(1, 2); %n, a
    args.cgr_regularized (:,2) double = zeros(1, 2); %n, a
    args.cgr_interpolated (:,2) double = zeros(1, 2); %n, a
end

%copy all input args
CRACK_VAR = args;

%set initial crack coordinates/ length based on specimen
if (strcmp(CRACK_PAR.specimen,'other') || strcmp(CRACK_PAR.specimen,'bar'))
    crack_coords = [0 0];
    a_ini = 0;
elseif strcmp(CRACK_PAR.specimen,'ct')
    crack_coords = [23.5 30];
    a_ini = 11.0;
elseif strcmp(CRACK_PAR.specimen,'tpb')
    crack_coords = [100 18];
    a_ini = 18.0;
elseif strcmp(CRACK_PAR.specimen,'pulltest')
    crack_coords = [0.2 0.75];
    a_ini = 0.0;
end
CRACK_VAR.crack_discretized(1,5:6) = crack_coords;
CRACK_VAR.crack_discretized(1,3) = a_ini;
CRACK_VAR.crack_regularized(1,3) = a_ini-CRACK_PAR.crack_tips*CRACK_PAR.int_d_tip/CRACK_PAR.int_d_segment;
CRACK_VAR.crack_interpolated(1,5:6) = crack_coords;
CRACK_VAR.crack_interpolated(1,3) = a_ini;

%set initial crack length also for fatigue crack growth rate computation
CRACK_VAR.cgr_discretized(1,2) = a_ini;
CRACK_VAR.cgr_regularized(1,2) = a_ini;
CRACK_VAR.cgr_interpolated(1,2) = a_ini;

end

