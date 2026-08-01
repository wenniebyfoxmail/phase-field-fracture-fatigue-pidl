function state = export_toy_road_peak_state(input, output_root)
%EXPORT_TOY_ROAD_PEAK_STATE Export one coherent native-Q4 cycle peak.

localValidateInput(input, output_root);
[outputPath, relativeStatePath] = localCanonicalOutputPath( ...
    output_root, input.metadata.cycle);

nodeCount = size(input.node_coords, 1);
elementCount = size(input.connectivity, 1);
u = input.displ(1:nodeCount);
v = input.displ(nodeCount + 1:end);

shapeFunctions = localQ4ShapeFunctions(input.quadrature_points);
dGp = input.p_field(input.connectivity) * shapeFunctions.';
gGp = (1 - dGp) .^ 2;
psiActiveGp = gGp .* input.psi_raw_gp;
alphaBarGp = input.history_vars(:, :, 2);
fAlphaGp = input.history_vars(:, :, 4);
strainGp = localQ4Strain(input.node_coords, input.connectivity, ...
    input.quadrature_points, u, v);

reactionX = input.reaction_vector(1:nodeCount);
reactionY = input.reaction_vector(nodeCount + 1:end);
reactionTopXy = [sum(reactionX(input.top_node_ids)) ...
    sum(reactionY(input.top_node_ids))];
reactionBottomXy = [sum(reactionX(input.bottom_node_ids)) ...
    sum(reactionY(input.bottom_node_ids))];

crackThresholds = [0.50 0.75 0.90 0.95];
dElem = mean(dGp, 2);
crackMaskElem = dElem >= crackThresholds;
meshSha256 = localMeshSha256(input.node_coords, input.connectivity);

state = struct();
state.node_coords = input.node_coords;
state.connectivity = input.connectivity;
state.quadrature_points = input.quadrature_points;
state.quadrature_weights = input.quadrature_weights(:);
state.u = u;
state.v = v;
state.d_node = input.p_field(:);
state.d_gp = dGp;
state.alpha_bar_gp = alphaBarGp;
state.f_alpha_gp = fAlphaGp;
state.psi_raw_gp = input.psi_raw_gp;
state.g_gp = gGp;
state.psi_active_gp = psiActiveGp;
state.strain_gp = strainGp;
state.d_elem = dElem;
state.alpha_bar_elem = mean(alphaBarGp, 2);
state.f_alpha_elem = mean(fAlphaGp, 2);
state.psi_raw_elem = mean(input.psi_raw_gp, 2);
state.g_elem = mean(gGp, 2);
state.psi_active_elem = mean(psiActiveGp, 2);
state.strain_elem = reshape(mean(strainGp, 2), elementCount, 3);
state.strain_energy_raw_elem = state.psi_raw_elem;
state.strain_energy_active_elem = state.psi_active_elem;
state.reaction_vector = input.reaction_vector(:);
state.top_node_ids = reshape(input.top_node_ids, 1, []);
state.bottom_node_ids = reshape(input.bottom_node_ids, 1, []);
state.reaction_top_xy = reactionTopXy;
state.reaction_bottom_xy = reactionBottomXy;
state.reaction_top_resultant = hypot(reactionTopXy(1), reactionTopXy(2));
state.reaction_bottom_resultant = hypot(reactionBottomXy(1), reactionBottomXy(2));
state.crack_thresholds = crackThresholds;
state.crack_mask_elem = crackMaskElem;
state.crack_tip_diagnostics = localCrackTipDiagnostics( ...
    input.node_coords, input.p_field, crackThresholds(end));
state.connected_right_boundary_diagnostics = localRightBoundaryDiagnostics( ...
    input.node_coords, input.connectivity, input.p_field, crackThresholds(end));
state.cycle = input.metadata.cycle;
state.Umax_N = input.metadata.Umax_N;
state.peak_substep_ordinal = input.metadata.peak_substep_ordinal;
state.n_substeps = input.metadata.n_substeps;
state.raw_step_1_based = input.metadata.raw_step_1_based;
state.branch = string(input.metadata.branch);
state.phase = string(input.metadata.phase);
state.state_semantics_id = string(input.metadata.state_semantics_id);
state.mesh_ordering_id = string(input.metadata.mesh_ordering_id);
state.state_ordering_id = string(input.metadata.state_ordering_id);
state.mesh_sha256 = meshSha256;
state.validation_tolerances = input.validation_tolerances;
state.field_semantics = localFieldSemantics();
state.cycle_index = struct( ...
    'cycle', state.cycle, ...
    'Umax_N', state.Umax_N, ...
    'peak_substep_ordinal', state.peak_substep_ordinal, ...
    'raw_step_1_based', state.raw_step_1_based, ...
    'branch', state.branch, ...
    'phase', state.phase, ...
    'file', relativeStatePath, ...
    'mesh_sha256', state.mesh_sha256, ...
    'state_semantics_id', state.state_semantics_id, ...
    'mesh_ordering_id', state.mesh_ordering_id, ...
    'state_ordering_id', state.state_ordering_id);

validate_toy_road_state(state);
publish_toy_road_state_no_clobber(state, outputPath);
end

function localValidateInput(input, outputPath)
if ~isstruct(input) || ~isscalar(input)
    localInputError('input must be a scalar struct.');
end
requiredFields = {'displ', 'p_field', 'history_vars', 'psi_raw_gp', ...
    'node_coords', 'connectivity', 'quadrature_points', 'quadrature_weights', ...
    'reaction_vector', 'top_node_ids', 'bottom_node_ids', 'metadata', ...
    'validation_tolerances'};
for index = 1:numel(requiredFields)
    if ~isfield(input, requiredFields{index})
        localInputError('Missing input field %s.', requiredFields{index});
    end
end
if ~(ischar(outputPath) || (isstring(outputPath) && isscalar(outputPath))) || ...
        strlength(string(outputPath)) == 0 || ~isfolder(outputPath)
    error('toyRoad:InvalidPeakStateOutput', ...
        'output_root must name an existing directory; the exporter derives states/cycle_NNNN.mat.');
end

nodeCoords = input.node_coords;
connectivity = input.connectivity;
if ~localIsFiniteReal(nodeCoords) || size(nodeCoords, 2) ~= 2 || isempty(nodeCoords)
    localInputError('node_coords must be a nonempty finite real N-by-2 array.');
end
if ~localIsFiniteReal(connectivity) || size(connectivity, 2) ~= 4 || ...
        isempty(connectivity) || any(connectivity ~= floor(connectivity), 'all') || ...
        any(connectivity < 1, 'all') || any(connectivity > size(nodeCoords, 1), 'all')
    localInputError('connectivity must be finite one-based Q4 connectivity.');
end

nodeCount = size(nodeCoords, 1);
elementCount = size(connectivity, 1);
gpCount = size(input.quadrature_points, 1);
if ~localIsFiniteReal(input.quadrature_points) || ...
        size(input.quadrature_points, 2) ~= 2 || gpCount < 1
    localInputError('quadrature_points must be a nonempty finite G-by-2 array.');
end
if ~localIsFiniteReal(input.quadrature_weights) || ...
        numel(input.quadrature_weights) ~= gpCount || any(input.quadrature_weights <= 0, 'all')
    localInputError('quadrature_weights must contain one positive finite value per GP.');
end
if ~localIsFiniteReal(input.displ) || ~isvector(input.displ) || ...
        numel(input.displ) ~= 2 * nodeCount
    localInputError('displ must be a finite component-blocked 2N vector.');
end
if ~localIsFiniteReal(input.p_field) || ~isvector(input.p_field) || ...
        numel(input.p_field) ~= nodeCount
    localInputError('p_field must be a finite N-vector.');
end
if ~localIsFiniteReal(input.reaction_vector) || ~isvector(input.reaction_vector) || ...
        numel(input.reaction_vector) ~= 2 * nodeCount
    localInputError('reaction_vector must be a finite component-blocked 2N vector.');
end
if ~localIsFiniteReal(input.psi_raw_gp) || ...
        ~isequal(size(input.psi_raw_gp), [elementCount gpCount])
    localInputError('psi_raw_gp must be a finite element-by-GP array.');
end
if ~localIsFiniteReal(input.history_vars) || ndims(input.history_vars) ~= 3 || ...
        size(input.history_vars, 1) ~= elementCount || ...
        size(input.history_vars, 2) ~= gpCount || size(input.history_vars, 3) < 4
    localInputError('history_vars must be a finite element-by-GP-by-history array with fields 2 and 4.');
end
localValidateNodeIds(input.top_node_ids, nodeCount, 'top_node_ids');
localValidateNodeIds(input.bottom_node_ids, nodeCount, 'bottom_node_ids');
localValidateMetadata(input.metadata);
localValidateTolerances(input.validation_tolerances);
end

function localValidateNodeIds(nodeIds, nodeCount, name)
if ~isnumeric(nodeIds) || ~isreal(nodeIds) || ~isvector(nodeIds) || ...
        isempty(nodeIds) || any(~isfinite(nodeIds), 'all') || ...
        any(nodeIds ~= floor(nodeIds), 'all') || any(nodeIds < 1, 'all') || ...
        any(nodeIds > nodeCount, 'all') || numel(unique(nodeIds)) ~= numel(nodeIds)
    localInputError('%s must contain unique valid one-based node IDs.', name);
end
end

function localValidateMetadata(metadata)
required = {'cycle', 'Umax_N', 'peak_substep_ordinal', 'n_substeps', ...
    'raw_step_1_based', 'branch', 'phase', 'state_semantics_id', ...
    'mesh_ordering_id', 'state_ordering_id'};
if ~isstruct(metadata) || ~isscalar(metadata)
    localInputError('metadata must be a scalar struct.');
end
for index = 1:numel(required)
    if ~isfield(metadata, required{index})
        localInputError('Missing metadata field %s.', required{index});
    end
end
integerFields = {'cycle', 'peak_substep_ordinal', 'n_substeps', 'raw_step_1_based'};
for index = 1:numel(integerFields)
    value = metadata.(integerFields{index});
    if ~isnumeric(value) || ~isreal(value) || ~isscalar(value) || ...
            ~isfinite(value) || value < 1 || value ~= floor(value)
        localInputError('metadata.%s must be a positive integer.', integerFields{index});
    end
end
if metadata.peak_substep_ordinal > metadata.n_substeps
    localInputError('peak_substep_ordinal cannot exceed n_substeps.');
end
if ~isnumeric(metadata.Umax_N) || ~isreal(metadata.Umax_N) || ...
        ~isscalar(metadata.Umax_N) || ~isfinite(metadata.Umax_N) || metadata.Umax_N < 0
    localInputError('metadata.Umax_N must be a nonnegative finite scalar.');
end
textFields = {'branch', 'phase', 'state_semantics_id', ...
    'mesh_ordering_id', 'state_ordering_id'};
for index = 1:numel(textFields)
    value = metadata.(textFields{index});
    if ~(ischar(value) || (isstring(value) && isscalar(value))) || ...
            strlength(string(value)) == 0
        localInputError('metadata.%s must be nonempty text.', textFields{index});
    end
end
end

function localValidateTolerances(tolerances)
required = {'range', 'active_identity', 'irreversibility'};
if ~isstruct(tolerances) || ~isscalar(tolerances)
    localInputError('validation_tolerances must be a scalar struct.');
end
for index = 1:numel(required)
    if ~isfield(tolerances, required{index})
        localInputError('Missing validation tolerance %s.', required{index});
    end
    value = tolerances.(required{index});
    if ~isnumeric(value) || ~isreal(value) || ~isscalar(value) || ...
            ~isfinite(value) || value < 0
        localInputError('validation tolerance %s must be nonnegative and finite.', required{index});
    end
end
end

function shapeFunctions = localQ4ShapeFunctions(points)
xi = points(:, 1);
eta = points(:, 2);
shapeFunctions = 0.25 * [(1 - xi) .* (1 - eta), ...
    (1 + xi) .* (1 - eta), (1 + xi) .* (1 + eta), ...
    (1 - xi) .* (1 + eta)];
end

function strainGp = localQ4Strain(coords, connectivity, points, u, v)
elementCount = size(connectivity, 1);
gpCount = size(points, 1);
strainGp = zeros(elementCount, gpCount, 3);
for elementId = 1:elementCount
    nodeIds = connectivity(elementId, :);
    elementCoords = coords(nodeIds, :);
    elementDispl = [u(nodeIds); v(nodeIds)];
    for gpId = 1:gpCount
        xi = points(gpId, 1);
        eta = points(gpId, 2);
        naturalGradients = 0.25 * [ ...
            -(1 - eta), (1 - eta), (1 + eta), -(1 + eta); ...
            -(1 - xi), -(1 + xi), (1 + xi), (1 - xi)];
        jacobian = naturalGradients * elementCoords;
        if ~all(isfinite(jacobian), 'all') || det(jacobian) <= 0
            localInputError('Q4 element %d has a non-positive GP Jacobian.', elementId);
        end
        spatialGradients = jacobian \ naturalGradients;
        bMatrix = zeros(3, 8);
        bMatrix(1, 1:4) = spatialGradients(1, :);
        bMatrix(2, 5:8) = spatialGradients(2, :);
        bMatrix(3, 1:4) = spatialGradients(2, :);
        bMatrix(3, 5:8) = spatialGradients(1, :);
        strainGp(elementId, gpId, :) = bMatrix * elementDispl;
    end
end
end

function diagnostics = localCrackTipDiagnostics(coords, damage, threshold)
candidateNodeIds = find(damage >= threshold);
if isempty(candidateNodeIds)
    tipNodeId = 0;
    tipCoordinates = zeros(0, 2);
else
    candidates = [coords(candidateNodeIds, 1), ...
        abs(coords(candidateNodeIds, 2)), candidateNodeIds];
    candidates = sortrows(candidates, [-1 2 3]);
    tipNodeId = candidates(1, 3);
    tipCoordinates = coords(tipNodeId, :);
end
diagnostics = struct('threshold', threshold, 'found', tipNodeId > 0, ...
    'node_id', tipNodeId, 'coordinates', tipCoordinates);
end

function diagnostics = localRightBoundaryDiagnostics(coords, connectivity, damage, threshold)
candidateMask = coords(:, 1) >= 0.48 & damage(:) >= threshold;
candidateNodeIds = find(candidateMask);
[componentNodeIds, componentSize] = localLargestConnectedComponent( ...
    candidateMask, connectivity, size(coords, 1));
diagnostics = struct('x_min', 0.48, 'damage_threshold', threshold, ...
    'minimum_connected_nodes', 3, 'candidate_node_ids', candidateNodeIds, ...
    'connected_component_node_ids', componentNodeIds, ...
    'connected_component_size', componentSize, 'hit', componentSize >= 3);
end

function [largestComponent, largestSize] = localLargestConnectedComponent(candidateMask, connectivity, nodeCount)
edges = [connectivity(:, [1 2]); connectivity(:, [2 3]); ...
    connectivity(:, [3 4]); connectivity(:, [4 1])];
edges = unique(sort(edges, 2), 'rows');
edges = edges(candidateMask(edges(:, 1)) & candidateMask(edges(:, 2)), :);
adjacency = sparse([edges(:, 1); edges(:, 2)], [edges(:, 2); edges(:, 1)], ...
    true, nodeCount, nodeCount);
unvisited = find(candidateMask).';
largestComponent = zeros(0, 1);
largestSize = 0;
while ~isempty(unvisited)
    component = localConnectedComponent(unvisited(1), adjacency);
    component = sort(component(:));
    unvisited = setdiff(unvisited, component.');
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

function semantics = localFieldSemantics()
semantics = struct( ...
    'node_coords', "nodal_coordinates", ...
    'connectivity', "element_q4_connectivity_1_based", ...
    'u', "nodal", 'v', "nodal", 'd_node', "nodal", ...
    'd_gp', "gauss_point_latent_fem_truth", ...
    'alpha_bar_gp', "gauss_point_latent_fem_truth", ...
    'f_alpha_gp', "gauss_point_latent_fem_truth", ...
    'psi_raw_gp', "gauss_point_latent_fem_truth", ...
    'g_gp', "gauss_point_latent_fem_truth", ...
    'psi_active_gp', "gauss_point_latent_fem_truth", ...
    'strain_gp', "gauss_point_latent_fem_truth", ...
    'd_elem', "element", 'alpha_bar_elem', "element_latent_fem_truth", ...
    'f_alpha_elem', "element_latent_fem_truth", ...
    'psi_raw_elem', "element_latent_fem_truth", ...
    'g_elem', "element_latent_fem_truth", ...
    'psi_active_elem', "element_latent_fem_truth", ...
    'strain_elem', "element_latent_fem_truth", ...
    'strain_energy_raw_elem', "element_latent_fem_truth", ...
    'strain_energy_active_elem', "element_latent_fem_truth", ...
    'reaction_vector', "nodal_component_blocked_x_then_y", ...
    'reaction_top_xy', "boundary_resultant_xy", ...
    'reaction_bottom_xy', "boundary_resultant_xy", ...
    'reaction_top_resultant', "boundary_resultant_l2", ...
    'reaction_bottom_resultant', "boundary_resultant_l2", ...
    'crack_mask_elem', "element_binary_by_threshold", ...
    'crack_tip_diagnostics', "derived_crack_diagnostic", ...
    'connected_right_boundary_diagnostics', "derived_crack_diagnostic");
end

function digest = localMeshSha256(coords, connectivity)
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(typecast(double(coords(:)), 'uint8'));
hasher.update(typecast(int64(connectivity(:)), 'uint8'));
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(string(reshape(dec2hex(digestBytes, 2).', 1, [])));
end

function [outputPath, relativePath] = localCanonicalOutputPath(outputRoot, cycle)
relativePath = string(sprintf('states/cycle_%04d.mat', cycle));
outputPath = fullfile(char(outputRoot), 'states', sprintf('cycle_%04d.mat', cycle));
end

function value = localIsFiniteReal(value)
value = isnumeric(value) && isreal(value) && all(isfinite(value), 'all');
end

function localInputError(message, varargin)
error('toyRoad:InvalidPeakStateInput', message, varargin{:});
end
