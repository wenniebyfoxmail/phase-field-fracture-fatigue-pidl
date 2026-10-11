% =========================================================================
% SENT fatigue - reverseBC u=0.12 soft diffuse pre-crack, hist0, with
% PIDL-equivalent fatigue-driver/history mask on the old left precrack line.
%
% Mac Request 22, 2026-06-09:
%   mask_fatigue = true, mask_energy = false
%
% This input keeps the standard retained-material soft precrack mechanics.
% The solver/exporter must enforce the mask only on fatigue-history slots:
%   alpha_bar -> 0, driver/Dalpha slot -> 0, f_alpha -> 1
% on x <= 0.5 and |y - 0.5| <= 2*ell.
% =========================================================================

if ~exist('soft_hist0_example_name', 'var')
    soft_hist0_example_name = ...
        'SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask';
end

INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC

precrack_fatigue_driver_mask_enabled = true;
precrack_fatigue_driver_mask_elem = ...
    (precrack_centroids(:,1) <= L_crack + 1e-12) & ...
    (abs(precrack_centroids(:,2) - 0.5) <= 2 * ell + 1e-12);

fprintf('[INPUT] precrack fatigue-driver mask elems = %d (x<=%.3g, |y-0.5|<=%.3g)\n', ...
    nnz(precrack_fatigue_driver_mask_elem), L_crack, 2*ell);

diffuse_precrack_metadata.precrack_fatigue_driver_mask_enabled = ...
    precrack_fatigue_driver_mask_enabled;
diffuse_precrack_metadata.precrack_fatigue_driver_mask = ...
    'PIDL-equivalent: mask_fatigue=True, mask_energy=False on old left precrack line';
diffuse_precrack_metadata.precrack_fatigue_driver_mask_plate = ...
    'x <= 0.5, |y - 0.5| <= 2*ell; mechanics/H/psi kept for audit';
diffuse_precrack_metadata.precrack_fatigue_driver_mask_n_elem = ...
    nnz(precrack_fatigue_driver_mask_elem);
