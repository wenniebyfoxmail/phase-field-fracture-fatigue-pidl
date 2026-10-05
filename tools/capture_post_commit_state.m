function snapshot = capture_post_commit_state(state)
%CAPTURE_POST_COMMIT_STATE Immutable native-Q4/T3 accepted-substep snapshot.

arguments
    state (1,1) struct
end
required = ["cycle","substep","load_factor","semantic_class", ...
    "staggered_iterations","damage_committed","history_committed", ...
    "cyclemax_updated","node_coords","connectivity","u_node", ...
    "d_node","psi_raw_gp","psi_cyclemax_gp","history_vars_old", ...
    "d_gp","g_gp","strain_gp","trace_strain_gp"];
for index = 1:numel(required)
    if ~isfield(state,required(index))
        error('phase_field:audit:MissingRequest28StateField', ...
            'Post-commit state is missing %s.',required(index));
    end
end
if ~state.damage_committed || ~state.history_committed || ~state.cyclemax_updated
    error('phase_field:audit:UncommittedRequest28State', ...
        'Capture requires both commits and cycle-max update.');
end
num_node = size(state.node_coords,1);
num_elem = size(state.connectivity,1);
arity = size(state.connectivity,2);
num_gp = size(state.psi_raw_gp,2);
if ~ismember(arity,[3 4]) || num_gp ~= arity || ...
        ~isequal(size(state.node_coords),[num_node 2]) || ...
        ~isequal(size(state.u_node),[num_node 2]) || ...
        ~isequal(size(state.d_node),[num_node 1]) || ...
        ~isequal(size(state.psi_raw_gp),[num_elem num_gp]) || ...
        ~isequal(size(state.psi_cyclemax_gp),[num_elem num_gp]) || ...
        ~isequal(size(state.history_vars_old),[num_elem num_gp 4]) || ...
        ~isequal(size(state.d_gp),[num_elem num_gp]) || ...
        ~isequal(size(state.g_gp),[num_elem num_gp]) || ...
        ~isequal(size(state.strain_gp),[num_elem num_gp 3]) || ...
        ~isequal(size(state.trace_strain_gp),[num_elem num_gp])
    error('phase_field:audit:InvalidRequest28StateShape', ...
        'Accepted-substep arrays do not match the native Q4/T3 contract.');
end
snapshot = struct();
for index = 1:numel(required)
    name = required(index);
    value = state.(name);
    if isnumeric(value)
        if any(~isfinite(value),'all')
            error('phase_field:audit:NonFiniteRequest28State', ...
                'Post-commit field %s contains non-finite values.',name);
        end
        value = value + zeros(size(value),'like',value);
    end
    snapshot.(name) = value;
end
snapshot.state_timing = ...
    "post-convergence/post-damage-commit/post-history-commit/post-cyclemax-update";
snapshot.topology = "arity" + string(arity);
snapshot.num_gauss_points = num_gp;
snapshot.node_ids = (1:num_node).';
snapshot.element_ids = (1:num_elem).';
snapshot.history_H_gp = snapshot.history_vars_old(:,:,1);
snapshot.alpha_bar_gp = snapshot.history_vars_old(:,:,2);
snapshot.psi_eff_prev_gp = snapshot.history_vars_old(:,:,3);
snapshot.f_alpha_gp = snapshot.history_vars_old(:,:,4);
snapshot.psi_raw_peak_elem = mean(snapshot.psi_raw_gp,2);
snapshot.psi_cyclemax_elem = mean(snapshot.psi_cyclemax_gp,2);
snapshot.alpha_bar_elem = mean(snapshot.alpha_bar_gp,2);
snapshot.f_alpha_elem = mean(snapshot.f_alpha_gp,2);
snapshot.d_elem = mean(snapshot.d_node(snapshot.connectivity),2);
end
