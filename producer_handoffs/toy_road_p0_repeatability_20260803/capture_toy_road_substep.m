function [capture, historyPost] = capture_toy_road_substep(capture, ordinal, ...
    dNode, psiRawGp, historyPre, commitCallback)
%CAPTURE_TOY_ROAD_SUBSTEP Snapshot raw state, commit history once, and retain post state.

required = {'cycle','previous','state0','connectivity','shape_operator', ...
    'alpha_T','p','commit_state','next_substep_ordinal','d_node','d_gp', ...
    'alpha_bar_gp','f_alpha_gp','psi_raw_gp'};
localRequire(isstruct(capture) && isscalar(capture) && ...
    all(isfield(capture, required)), 'capture is not an initialized cycle capture.');
localRequire(isa(ordinal, 'double') && isscalar(ordinal) && isfinite(ordinal) && ...
    ordinal == capture.next_substep_ordinal && ordinal >= 1 && ordinal <= 5, ...
    'substep ordinals must be captured exactly once in order 1 through 5.');
localRequire(capture.commit_state.get() == ordinal, ...
    'the substep commit token is stale, duplicated, or already consumed.');
localRequire(isa(commitCallback, 'function_handle'), ...
    'commitCallback must be the normal history commit function handle.');

nNode = size(capture.state0.d_node, 1);
nElem = size(capture.state0.alpha_bar_gp, 1);
gpSize = [nElem 4];
localRequire(localFiniteDouble(dNode) && isequal(size(dNode), [nNode 1]), ...
    'dNode must be an n_node-by-1 finite double array.');
localRequire(localFiniteDouble(psiRawGp) && isequal(size(psiRawGp), gpSize), ...
    'psiRawGp must be an n_elem-by-4 finite double array.');
localRequire(localFiniteDouble(historyPre) && isequal(size(historyPre), gpSize), ...
    'historyPre must be an n_elem-by-4 finite double array.');
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
    localRequire(localCaptureDimensionsMatch(capture, nNode, nElem), ...
        'capture dimensions changed after the first substep.');
end

elementDamage = reshape(dNode(capture.connectivity), nElem, 4);
dGp = (capture.shape_operator * elementDamage.').';
capture.d_node(:,ordinal) = dNode;
capture.d_gp(:,:,ordinal) = dGp;
capture.psi_raw_gp(:,:,ordinal) = psiRawGp;
preCommitSnapshot = struct( ...
    'cycle', capture.cycle, ...
    'substep_ordinal', ordinal, ...
    'd_node', capture.d_node(:,ordinal), ...
    'd_gp', capture.d_gp(:,:,ordinal), ...
    'psi_raw_gp', capture.psi_raw_gp(:,:,ordinal), ...
    'history_pre', historyPre);

localRequire(capture.commit_state.compareAndSet(ordinal, -ordinal), ...
    'the substep commit token is stale, duplicated, or already consumed.');
historyPost = commitCallback(historyPre, preCommitSnapshot);
localRequire(localFiniteDouble(historyPost) && isequal(size(historyPost), gpSize), ...
    'the history commit callback must return one finite n_elem-by-4 double state.');
localRequire(all(historyPost >= historyPre - 1e-12, 'all'), ...
    'post-commit history must not decrease from pre-commit history.');

fAlphaGp = min(1, ...
    (1 - ((historyPost - capture.alpha_T) ./ ...
          (historyPost + capture.alpha_T))).^capture.p);
capture.alpha_bar_gp(:,:,ordinal) = historyPost;
capture.f_alpha_gp(:,:,ordinal) = fAlphaGp;
capture.next_substep_ordinal = ordinal + 1;
capture.commit_state.set(ordinal + 1);
end

function value = localCaptureDimensionsMatch(capture, nNode, nElem)
value = isequal(size(capture.d_node), [nNode 5]) && ...
    isequal(size(capture.d_gp), [nElem 4 5]) && ...
    isequal(size(capture.alpha_bar_gp), [nElem 4 5]) && ...
    isequal(size(capture.f_alpha_gp), [nElem 4 5]) && ...
    isequal(size(capture.psi_raw_gp), [nElem 4 5]);
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
