classdef StressState < uint8
    %STRESSSTATE Type of a material stress or strain
    %   ...
    %

    % Copyright (C) 2022 ETH Zurich, SIS ID and CompMech D-MAVT
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

    enumeration
        PlaneStrain (1)
        PlaneStress  (2)
    end
    methods
        function value = as_number(obj)
            value = double(obj);
        end
    end
end
