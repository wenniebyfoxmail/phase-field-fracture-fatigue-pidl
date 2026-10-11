function [conn_tract, flag_tract, tract_face, elem_tract] = neumann_prelim(...
    elem, node_tract_unique...
)
%NEUMANN_SETTING Preliminary computations to apply Neumann boundary condition.
%   ...

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

conn_tract = zeros(size(elem));

for i=1:length(node_tract_unique)
    idx             = (elem==node_tract_unique(i));
    conn_tract(idx) = conn_tract(idx) + 1;
    clear idx
end

flag_tract = sum(conn_tract,2);

tract_face = zeros(size(elem));
for i=1:size(elem,2)-1
    idx               = ((conn_tract(:,i)+conn_tract(:,i+1))==2);
    tract_face(idx,i) = 1;
    clear idx
end
idx                          = ((conn_tract(:,1)+conn_tract(:,size(elem,2)))==2);
tract_face(idx,size(elem,2)) = 1;

clear idx

elem_tract = find(flag_tract>=2);

end
