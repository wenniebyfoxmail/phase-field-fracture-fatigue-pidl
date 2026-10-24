function receipt = run_fixed_weight_saved_state_audit(cfg)
%RUN_FIXED_WEIGHT_SAVED_STATE_AUDIT Explicit entry point for the reviewed audit.
%
% No default configuration is provided.  `cfg.execute` must be set to true
% manually after review; otherwise fw_saved_state_audit fails before any file is
% read or output directory is created.

arguments
    cfg (1,1) struct
end
receipt = fw_saved_state_audit(cfg);
end
