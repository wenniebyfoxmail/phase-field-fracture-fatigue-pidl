function [] = mustBeNonzeroLengthText(x)
%MUSTBENONZEROLENGTHTEXT Validate that value is text with nonzero length
%
%   Backward compatibility implementation for MATLAB version >=R2019b.
%
%   To be removed in favour of built-in funciton with the same name, when minimal
%   required MATLAB version is >=R2020b.
%

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

    if isNonzeroLengthChar(x)
        return
    elseif iscell(x) && all(cellfun(@isNonzeroLengthChar, x))
        return
    elseif isstring(x) && all(strlength(x) > 0)
        return
    end

    error("Value must be text with one or more characters.")

end


function [bool] = isNonzeroLengthChar(x)
    if ischar(x)
        s = size(x);
        bool = (s(1) == 1 && length(s) < 3 && numel(x) > 0);
    else
        bool = false;
    end
end
