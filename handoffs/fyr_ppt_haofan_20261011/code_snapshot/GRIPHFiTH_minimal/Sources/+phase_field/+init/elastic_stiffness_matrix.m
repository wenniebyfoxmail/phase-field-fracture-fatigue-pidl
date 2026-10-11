function [C] = elastic_stiffness_matrix(E, ni, num_materials, stress_state)
%ELASTIC_STIFFNESS_MATRIX Construct an elastic stiffness matrix.
%   Construct an elastic stiffness 3x3 matrix `C` from Young's Modulus `E` (GPa) and
%   from Poisson's ratio `ni`.

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

C = zeros(3,3,num_materials);

%check for plane strain/ plane stress
if stress_state == phase_field.StressState.PlaneStrain

    %run through all of the materials
    for i=1:num_materials
        C(:,:,i) = E(i) / ((1 + ni(i)) * (1 - 2 * ni(i))) * [...
                        1-ni(i) ni(i)   0;
                        ni(i)   1-ni(i) 0;
                        0    0    (1 - 2 * ni(i)) / 2;
                    ];
    end

elseif stress_state == phase_field.StressState.PlaneStress

    %run through all of the materials
    for i=1:num_materials
        C(:,:,i) = E(i) / (1 - ni(i)^2) * [...
                        1       ni(i)   0;
                        ni(i)   1       0;
                        0       0       (1 - ni(i)) / 2;
                    ];
    end

end

end
