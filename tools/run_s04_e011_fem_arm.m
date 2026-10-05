function result = run_s04_e011_fem_arm(reference_dir, mesh_file, output_root, topology, max_cycle)
%RUN_S04_E011_FEM_ARM Execute one native Q4/T3 arm under one frozen contract.

arguments
    reference_dir (1,1) string
    mesh_file (1,1) string
    output_root (1,1) string
    topology (1,1) string {mustBeMember(topology,["q4","t3"])}
    max_cycle (1,1) double {mustBeInteger,mustBePositive,mustBeLessThanOrEqual(max_cycle,120)}
end

cfg = build_SENS_hard_recovery_loading5_primary_config(reference_dir);
cfg.output_identity = "S04_E011_FEM_" + upper(topology) + "_C" + string(max_cycle);
cfg.requested_cycles = 1:max_cycle;
cfg.defer_stop_until_cycle = max_cycle;
work_dir = fullfile(output_root, cfg.output_identity);
if isfolder(work_dir)
    error('S04:E011:OutputExists', 'Refusing to reuse output directory: %s', work_dir);
end
options = struct( ...
    'work_dir', work_dir, ...
    'validate_only', false, ...
    'max_cycle', max_cycle, ...
    'mesh_file', mesh_file, ...
    'topology', topology);
% Save every accepted physical-cycle substep.  The U=0 recovery state is
% separately frozen in state0_analysis.mat and initial_state_metadata.mat.
[request_cycle, request_substep] = ndgrid(1:max_cycle, 1:5);
options.request28_targets = [request_cycle(:), request_substep(:)];
options.request28_semantic_classes = repmat( ...
    "accepted-post-commit", numel(request_cycle), 1);

result = run_SENS_hard_recovery_native_q4_capture(cfg, options);
result.experiment_id = "S04-E011";
result.topology = topology;
result.mesh_file = mesh_file;
result.mesh_sha256 = phase_field.audit.sha256_file(mesh_file);
result.reference_dir = reference_dir;
result.max_cycle_requested = max_cycle;
result.finished_at = datetime('now', 'TimeZone', 'UTC');
save(fullfile(work_dir, 'S04_E011_result.mat'), 'result', '-v7.3');
end
