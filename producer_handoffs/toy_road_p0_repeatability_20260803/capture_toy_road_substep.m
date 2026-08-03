function capture = capture_toy_road_substep(capture, ordinal, dNode, psiRawGp, ...
    historyPre, historyPost, exportedHistory, fAlphaGp, connectivity, shapeFunctions)
%CAPTURE_TOY_ROAD_SUBSTEP Snapshot one converged substep around its history commit.

required = {'cycle','previous','state0','next_substep_ordinal','d_node','d_gp', ...
    'alpha_bar_gp','f_alpha_gp','psi_raw_gp'};
localRequire(isstruct(capture) && isscalar(capture) && ...
    all(isfield(capture, required)), 'capture is not an initialized cycle capture.');
localRequire(isa(ordinal, 'double') && isscalar(ordinal) && isfinite(ordinal) && ...
    ordinal == capture.next_substep_ordinal && ordinal >= 1 && ordinal <= 5, ...
    'substep ordinals must be captured exactly once in order 1 through 5.');

nNode = size(capture.state0.d_node, 1);
nElem = size(capture.state0.alpha_bar_gp, 1);
localRequire(localFiniteDouble(dNode) && isequal(size(dNode), [nNode 1]), ...
    'dNode must be an n_node-by-1 finite double array.');
gpSize = [nElem 4];
localRequire(localFiniteDouble(psiRawGp) && isequal(size(psiRawGp), gpSize), ...
    'psiRawGp must be an n_elem-by-4 finite double array.');
localRequire(localFiniteDouble(historyPre) && isequal(size(historyPre), gpSize) && ...
    localFiniteDouble(historyPost) && isequal(size(historyPost), gpSize) && ...
    localFiniteDouble(exportedHistory) && isequal(size(exportedHistory), gpSize), ...
    'history arrays must be finite n_elem-by-4 doubles.');
localRequire(isequaln(exportedHistory, historyPost), ...
    'the exported history slice must be the supplied post-commit history.');
localRequire(all(historyPost >= historyPre - 1e-12, 'all'), ...
    'post-commit history must not decrease from pre-commit history.');
localRequire(localFiniteDouble(fAlphaGp) && isequal(size(fAlphaGp), gpSize), ...
    'fAlphaGp must be an n_elem-by-4 finite double array.');
localRequire(isa(connectivity, 'double') && isequal(size(connectivity), [nElem 4]) && ...
    all(isfinite(connectivity), 'all') && all(connectivity == floor(connectivity), 'all') && ...
    all(connectivity >= 1, 'all') && all(connectivity <= nNode, 'all'), ...
    'connectivity must be a valid n_elem-by-4 one-based double array.');
localRequire(localFiniteDouble(shapeFunctions) && isequal(size(shapeFunctions), [4 4]), ...
    'shapeFunctions must be a finite 4-by-4 double array.');

expectedHistoryPre = localExpectedHistoryPre(capture, ordinal);
localRequire(max(abs(historyPre - expectedHistoryPre), [], 'all') <= 1e-12, ...
    'historyPre must equal the immediately preceding committed history.');

if ordinal == 1
    capture.d_node = NaN(nNode, 5);
    capture.d_gp = NaN(nElem, 4, 5);
    capture.alpha_bar_gp = NaN(nElem, 4, 5);
    capture.f_alpha_gp = NaN(nElem, 4, 5);
    capture.psi_raw_gp = NaN(nElem, 4, 5);
else
    localRequire(isequal(size(capture.d_node), [nNode 5]) && ...
        isequal(size(capture.d_gp), [nElem 4 5]) && ...
        isequal(size(capture.alpha_bar_gp), [nElem 4 5]) && ...
        isequal(size(capture.f_alpha_gp), [nElem 4 5]) && ...
        isequal(size(capture.psi_raw_gp), [nElem 4 5]), ...
        'capture dimensions changed after the first substep.');
end

elementDamage = reshape(dNode(connectivity), nElem, 4);
dGp = (shapeFunctions * elementDamage.').';
capture.d_node(:,ordinal) = dNode;
capture.d_gp(:,:,ordinal) = dGp;
capture.alpha_bar_gp(:,:,ordinal) = exportedHistory;
capture.f_alpha_gp(:,:,ordinal) = fAlphaGp;
capture.psi_raw_gp(:,:,ordinal) = psiRawGp;
capture.next_substep_ordinal = ordinal + 1;
end

function history = localExpectedHistoryPre(capture, ordinal)
if ordinal > 1
    history = capture.alpha_bar_gp(:,:,ordinal - 1);
elseif capture.cycle == 1
    history = capture.state0.alpha_bar_gp;
else
    history = capture.previous.alpha_bar_gp(:,:,5);
end
end

function value = localFiniteDouble(value)
value = isa(value, 'double') && isreal(value) && all(isfinite(value), 'all');
end

function localRequire(condition, message)
if ~condition
    error('toyRoadP0:InvalidCycleCapture', message);
end
end
