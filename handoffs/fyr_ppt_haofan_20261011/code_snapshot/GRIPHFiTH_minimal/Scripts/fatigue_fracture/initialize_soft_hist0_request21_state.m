% Shared Request 21 soft-hist0 initial state.
p_field = precrack_soft_profile;
p_field_old = precrack_soft_profile;
initial_precrack_exclusion_nodes = precrack_nodes;
history_vars_old(:,:,2) = 0.0;
history_vars_old(:,:,3) = 0.0;
history_vars_old(:,:,4) = 1.0;

initial_state_audit = struct();
initial_state_audit.profile = diffuse_precrack_metadata.profile;
initial_state_audit.n_precrack_nodes = numel(precrack_nodes);
initial_state_audit.n_precrack_core_nodes = numel(precrack_core_nodes);
initial_state_audit.n_precrack_elems = numel(precrack_elems);
initial_state_audit.n_precrack_core_elems = numel(precrack_core_elems);
initial_state_audit.precrack_d_mean = mean(precrack_soft_profile(precrack_nodes), 'omitnan');
initial_state_audit.precrack_d_max = max(precrack_soft_profile(precrack_nodes));
initial_state_audit.precrack_elem_d_mean = mean(precrack_elem_profile(precrack_elems), 'omitnan');
initial_state_audit.precrack_elem_d_max = max(precrack_elem_profile(precrack_elems));
initial_state_audit.precrack_alpha_bar_mean = 0.0;
initial_state_audit.precrack_alpha_bar_max = 0.0;
initial_state_audit.precrack_f_alpha_mean = 1.0;
initial_state_audit.precrack_f_alpha_min = 1.0;
initial_state_audit.outside_alpha_bar_mean = 0.0;
initial_state_audit.outside_alpha_bar_max = 0.0;
initial_state_audit.tol_irrev = diffuse_precrack_metadata.tol_irrev;
initial_state_audit.penalty_irrev = diffuse_precrack_metadata.penalty_irrev;
initial_state_audit.res_stiff = diffuse_precrack_metadata.res_stiff;
initial_state_audit.requested_n_step = diffuse_precrack_metadata.requested_n_step;
initial_state_audit.n_step = diffuse_precrack_metadata.n_step;
initial_state_audit.retained_load_factors = diffuse_precrack_metadata.retained_load_factors;
initial_state_audit.retained_uy_values = diffuse_precrack_metadata.retained_uy_values;
initial_state_audit.cycle_update_semantics = diffuse_precrack_metadata.cycle_update_semantics;

save([example_name filesep 'diffuse_precrack_metadata.mat'], ...
    'diffuse_precrack_metadata', 'precrack_nodes', 'precrack_core_nodes', ...
    'precrack_elems', 'precrack_core_elems', 'precrack_centroids', ...
    'precrack_soft_profile', 'precrack_elem_profile', ...
    'initial_precrack_exclusion_nodes', 'initial_state_audit');
