function export_fem_nodal_trajectory(base, outdir, cycles)
% Export selected FEM peak nodal states for common-operator trajectory replay.

if nargin < 3, cycles = [1 20 60 76 82 83 85 89]; end
if nargin < 2, error('outdir is required'); end
if nargin < 1, error('base production-output directory is required'); end
if ~exist(outdir, 'dir'), mkdir(outdir); end

specs = {
    'q4', fullfile(base, 'S04_E011_FEM_Q4_C120', 'native_gp_staging');
    't3', fullfile(base, 'S04_E011_FEM_T3_C120', 'native_gp_staging')
};

for ispec = 1:size(specs,1)
    topology = specs{ispec,1};
    root = specs{ispec,2};
    u_node = [];
    v_node = [];
    d_node = [];
    source_files = strings(numel(cycles),1);
    source_bytes = zeros(numel(cycles),1,'uint64');
    source_mtime = strings(numel(cycles),1);
    for ic = 1:numel(cycles)
        c = cycles(ic);
        path = fullfile(root, sprintf('cycle_%04d_peak_%s.mat', c, topology));
        assert(isfile(path), 'Missing source: %s', path);
        s = load(path, 'converged_peak_solution');
        p = s.converged_peak_solution;
        if isempty(u_node)
            nn = numel(p.u);
            u_node = zeros(nn,numel(cycles));
            v_node = zeros(nn,numel(cycles));
            d_node = zeros(nn,numel(cycles));
        end
        assert(numel(p.u)==size(u_node,1) && numel(p.v)==size(v_node,1) && numel(p.d)==size(d_node,1));
        u_node(:,ic) = p.u(:);
        v_node(:,ic) = p.v(:);
        d_node(:,ic) = p.d(:);
        info = dir(path);
        source_files(ic) = string(path);
        source_bytes(ic) = uint64(info.bytes);
        source_mtime(ic) = string(info.date);
        fprintf('%s c%d nn=%d d=[%.9g, %.9g]\n', topology, c, nn, min(p.d(:)), max(p.d(:)));
    end
    state_contract = 'FEM cycle peak converged_peak_solution after final staggered iterate';
    schema = 's04e011-fem-nodal-trajectory-v1';
    output_path = fullfile(outdir, sprintf('fem_%s_nodal_trajectory.mat', topology));
    save(output_path, 'schema', 'state_contract', 'topology', 'cycles', ...
        'u_node', 'v_node', 'd_node', 'source_files', 'source_bytes', 'source_mtime', '-v7.3');
    fprintf('saved %s\n', output_path);
end
end
