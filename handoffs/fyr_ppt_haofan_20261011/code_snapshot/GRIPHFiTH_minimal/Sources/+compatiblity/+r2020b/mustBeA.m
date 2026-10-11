function [] = mustBeA(value,classNames)
%MUSTBEA Validate that value is of specified type
%
%   Backward compatibility implementation for MATLAB version >=R2019b.
%
%   To be removed in favour of built-in funciton with the same name, when minimal
%   required MATLAB version is >=R2020b.
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

    if isa(value, classNames)
        return
    end
    error(strcat('Value must be of the following types: ''', join(classNames, ''', '''), '''.'))

end
