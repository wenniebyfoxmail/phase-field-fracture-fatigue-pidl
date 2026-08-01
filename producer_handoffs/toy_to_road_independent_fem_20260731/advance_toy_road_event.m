function state = advance_toy_road_event(state, node_coords, connectivity, cycle, peak_damage)
%ADVANCE_TOY_ROAD_EVENT Advance the locked right-boundary event state.

state = localNormaliseState(state);
localValidateInputs(node_coords, connectivity, cycle, peak_damage);

candidateMask = node_coords(:, 1) >= 0.48 & peak_damage >= 0.95;
hitNodeIds = find(candidateMask);
[componentNodeIds, componentSize] = localLargestConnectedComponent( ...
    candidateMask, connectivity, size(node_coords, 1));
isHit = componentSize >= 3;

state.hit_node_ids = hitNodeIds;
state.connected_component_node_ids = componentNodeIds;
state.connected_component_size = componentSize;
state.hit = isHit;

if isHit
    if isnan(state.first_hit)
        state.first_hit = cycle;
        state.consecutive_post_hit = 0;
    elseif isnan(state.confirmed)
        state.consecutive_post_hit = state.consecutive_post_hit + 1;
        if state.consecutive_post_hit >= 3
            state.confirmed = cycle;
        end
    end
else
    state.consecutive_post_hit = 0;
end
end

function state = localNormaliseState(state)
if isempty(state)
    state = struct();
end
if ~isstruct(state) || ~isscalar(state)
    error('toyRoad:InvalidEventInput', 'state must be a scalar struct.');
end
state = localSetDefault(state, 'first_hit', NaN);
state = localSetDefault(state, 'confirmed', NaN);
state = localSetDefault(state, 'consecutive_post_hit', 0);
state = localSetDefault(state, 'hit_node_ids', zeros(0, 1));
state = localSetDefault(state, 'connected_component_node_ids', zeros(0, 1));
state = localSetDefault(state, 'connected_component_size', 0);
state = localSetDefault(state, 'hit', false);
end

function state = localSetDefault(state, fieldName, value)
if ~isfield(state, fieldName)
    state.(fieldName) = value;
end
end

function localValidateInputs(nodeCoords, connectivity, cycle, peakDamage)
isValidCoords = isnumeric(nodeCoords) && isreal(nodeCoords) && size(nodeCoords, 2) == 2 && ...
    ~isempty(nodeCoords) && all(isfinite(nodeCoords), 'all');
isValidConnectivity = isnumeric(connectivity) && isreal(connectivity) && ...
    size(connectivity, 2) == 4 && ~isempty(connectivity) && ...
    all(isfinite(connectivity), 'all') && all(connectivity == floor(connectivity), 'all') && ...
    all(connectivity >= 1, 'all') && all(connectivity <= size(nodeCoords, 1), 'all');
isValidCycle = isnumeric(cycle) && isreal(cycle) && isscalar(cycle) && ...
    isfinite(cycle) && cycle >= 1 && cycle == floor(cycle);
isValidDamage = isnumeric(peakDamage) && isreal(peakDamage) && isvector(peakDamage) && ...
    numel(peakDamage) == size(nodeCoords, 1) && all(isfinite(peakDamage), 'all');
if ~(isValidCoords && isValidConnectivity && isValidCycle && isValidDamage)
    error('toyRoad:InvalidEventInput', ...
        'Inputs must contain finite coordinates, Q4 connectivity, a positive integer cycle, and nodal peak damage.');
end
end

function [largestComponent, largestSize] = localLargestConnectedComponent(candidateMask, connectivity, nodeCount)
edges = [connectivity(:, [1 2]); connectivity(:, [2 3]); ...
    connectivity(:, [3 4]); connectivity(:, [4 1])];
edges = unique(sort(edges, 2), 'rows');
edges = edges(candidateMask(edges(:, 1)) & candidateMask(edges(:, 2)), :);
adjacency = sparse([edges(:, 1); edges(:, 2)], [edges(:, 2); edges(:, 1)], ...
    true, nodeCount, nodeCount);

unvisited = find(candidateMask)';
largestComponent = zeros(0, 1);
largestSize = 0;
while ~isempty(unvisited)
    component = localConnectedComponent(unvisited(1), adjacency);
    component = sort(component(:));
    unvisited = setdiff(unvisited, component');
    if numel(component) > largestSize
        largestComponent = component;
        largestSize = numel(component);
    end
end
end

function component = localConnectedComponent(seed, adjacency)
visited = false(size(adjacency, 1), 1);
queue = seed;
visited(seed) = true;
head = 1;
while head <= numel(queue)
    nodeId = queue(head);
    head = head + 1;
    neighbours = find(adjacency(nodeId, :));
    newNodes = neighbours(~visited(neighbours));
    visited(newNodes) = true;
    queue = [queue newNodes]; %#ok<AGROW>
end
component = queue;
end
