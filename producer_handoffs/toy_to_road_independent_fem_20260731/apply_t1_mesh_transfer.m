function [mapped_coords, audit] = apply_t1_mesh_transfer(node_coords, connectivity, ell)
%APPLY_T1_MESH_TRANSFER Transfer the approved T1 notch geometry and audit it.

localValidateInputs(node_coords, connectivity, ell);

mapped_coords = node_coords;
leftMask = node_coords(:, 1) <= 0;
mapped_coords(leftMask, 1) = -0.5 + 1.25 * (node_coords(leftMask, 1) + 0.5);
mapped_coords(~leftMask, 1) = 0.125 + 0.75 * node_coords(~leftMask, 1);

tolerance = 1e-12;
tipNodeIds = find(abs(node_coords(:, 1)) <= tolerance & ...
    abs(node_coords(:, 2)) <= tolerance);
localGate(numel(tipNodeIds) == 1, 'Expected exactly one parent notch-tip node at (0, 0).');
tipNodeId = tipNodeIds(1);

boundaryInputValid = abs(min(node_coords(:, 1)) + 0.5) <= tolerance && ...
    abs(max(node_coords(:, 1)) - 0.5) <= tolerance;
boundariesFixed = boundaryInputValid && ...
    abs(min(mapped_coords(:, 1)) + 0.5) <= tolerance && ...
    abs(max(mapped_coords(:, 1)) - 0.5) <= tolerance;
notchTipIdentityPreserved = norm(mapped_coords(tipNodeId, :) - [0.125 0]) <= tolerance;
localGate(boundariesFixed, 'External x boundaries are not fixed at -0.5 and 0.5.');
localGate(notchTipIdentityPreserved, 'The parent notch-tip node did not map to (0.125, 0).');

jacobians = localQ4CornerJacobians(mapped_coords, connectivity);
allPositiveJacobians = all(jacobians > tolerance, 'all');
localGate(allPositiveJacobians, 'Mapped Q4 elements have non-positive corner Jacobians.');

localEdgeRatios = localTipEdgeRatios(mapped_coords, connectivity, tipNodeId, ell);
localRatioMin = min(localEdgeRatios);
localRatioMax = max(localEdgeRatios);
localGate(localRatioMin >= 0.75 - tolerance && localRatioMax <= 1.25 + tolerance, ...
    'Mapped notch-tip edge h/ell ratios are outside [0.75, 1.25].');

audit = struct( ...
    'all_positive_jacobians', allPositiveJacobians, ...
    'q4_corner_jacobians', jacobians, ...
    'boundaries_fixed', boundariesFixed, ...
    'notch_tip_identity_preserved', notchTipIdentityPreserved, ...
    'notch_tip_node_id', tipNodeId, ...
    'node_count_unchanged', size(mapped_coords, 1) == size(node_coords, 1), ...
    'element_count_unchanged', size(connectivity, 1) == size(connectivity, 1), ...
    'connectivity_unchanged', true, ...
    'local_h_over_ell_ratio_min', localRatioMin, ...
    'local_h_over_ell_ratio_max', localRatioMax, ...
    'parent_mesh_sha256', localMeshSha256(node_coords, connectivity), ...
    'candidate_mesh_sha256', localMeshSha256(mapped_coords, connectivity));
end

function localValidateInputs(nodeCoords, connectivity, ell)
localGate(isnumeric(nodeCoords) && isreal(nodeCoords) && size(nodeCoords, 2) == 2 && ...
    ~isempty(nodeCoords) && all(isfinite(nodeCoords), 'all'), ...
    'node_coords must be a nonempty finite real N-by-2 array.');
localGate(isnumeric(connectivity) && isreal(connectivity) && size(connectivity, 2) == 4 && ...
    ~isempty(connectivity) && all(isfinite(connectivity), 'all') && ...
    all(connectivity == floor(connectivity), 'all') && ...
    all(connectivity >= 1, 'all') && all(connectivity <= size(nodeCoords, 1), 'all'), ...
    'connectivity must be a finite integer Q4 connectivity array.');
localGate(isnumeric(ell) && isreal(ell) && isscalar(ell) && isfinite(ell) && ell > 0, ...
    'ell must be a positive finite scalar.');
end

function jacobians = localQ4CornerJacobians(coords, connectivity)
naturalCorners = [-1 -1; 1 -1; 1 1; -1 1];
jacobians = zeros(size(connectivity, 1), 4);
for elementId = 1:size(connectivity, 1)
    elementCoords = coords(connectivity(elementId, :), :);
    for cornerId = 1:4
        xi = naturalCorners(cornerId, 1);
        eta = naturalCorners(cornerId, 2);
        dNdxi = 0.25 * [-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)];
        dNdeta = 0.25 * [-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)];
        jacobians(elementId, cornerId) = det([dNdxi; dNdeta] * elementCoords);
    end
end
end

function ratios = localTipEdgeRatios(coords, connectivity, tipNodeId, ell)
elementMask = any(connectivity == tipNodeId, 2);
localGate(any(elementMask), 'The parent notch-tip node is not referenced by Q4 connectivity.');
localConnectivity = connectivity(elementMask, :);
edges = [localConnectivity(:, [1 2]); localConnectivity(:, [2 3]); ...
    localConnectivity(:, [3 4]); localConnectivity(:, [4 1])];
edges = unique(sort(edges, 2), 'rows');
tipEdges = edges(any(edges == tipNodeId, 2), :);
localGate(~isempty(tipEdges), 'No Q4 edge is incident to the parent notch-tip node.');
edgeVectors = coords(tipEdges(:, 1), :) - coords(tipEdges(:, 2), :);
ratios = sqrt(sum(edgeVectors .^ 2, 2)) / ell;
end

function digest = localMeshSha256(coords, connectivity)
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(typecast(double(coords(:)), 'uint8'));
hasher.update(typecast(int64(connectivity(:)), 'uint8'));
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(string(reshape(dec2hex(digestBytes, 2).', 1, [])));
end

function localGate(condition, message)
if ~condition
    error('toyRoad:MeshTransferGateFailed', '%s', message);
end
end
