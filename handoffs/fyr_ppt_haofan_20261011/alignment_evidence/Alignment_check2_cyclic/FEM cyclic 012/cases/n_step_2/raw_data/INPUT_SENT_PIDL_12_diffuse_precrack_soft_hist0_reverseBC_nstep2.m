% Request 21 Variant A: soft-hist0 reverseBC with two retained substeps.
% Uses an explicit peak+unload schedule because the stock cyclic step builder
% enforces at least three retained cyclic increments.

INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC

example_name = 'SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_nstep2';
SOL_STEP_PAR.n_step = 2;
SOL_STEP_PAR.loading = 'cyclic';
SOL_STEP_PAR.discretization = 'custom_peak_unload';
SOL_STEP_PAR.ux_increment = [0, 0];
SOL_STEP_PAR.uy_increment = [0.12, -0.12];
SOL_STEP_PAR.tx_increment = [0, 0];
SOL_STEP_PAR.ty_increment = [0, 0];

diffuse_precrack_metadata.requested_n_step = 2;
diffuse_precrack_metadata.n_step = SOL_STEP_PAR.n_step;
diffuse_precrack_metadata.retained_load_factors = [1, 0];
diffuse_precrack_metadata.retained_uy_values = cumsum(SOL_STEP_PAR.uy_increment);
diffuse_precrack_metadata.cycle_update_semantics = 'Request 21 n_step=2: explicit peak+unload schedule; history refresh occurs at peak and unloaded/end-of-cycle states';
