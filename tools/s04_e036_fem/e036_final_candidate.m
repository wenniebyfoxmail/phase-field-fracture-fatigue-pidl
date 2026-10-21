function [audit,proposal]=e036_final_candidate(eq,pf,state,old,free,policy,inner_f)
%E036_FINAL_CANDIDATE Fresh common-state check; pure proposal, never a commit.
% eq(u,d)->[Ru,raw]; pf(d,lower,raw,old_history)->[Rd,trial_history].
% Derived from E011 coupled_solve point() and commit_once preimage contracts.
% Old history/lower are value inputs. Both phase calls use the SAME old history.
u=state.u(:);d=state.d(:);lower=old.lower(:);upper=state.upper(:);
fu=free.u(:);fd=free.d(:);proposal=[];
assert(all(isfield(policy,{'phase_semantics','joint_tol','u_tol','bound_tol','active_tol','history_tol'})), ...
 'E036:Policy','Explicit residual semantics and tolerances are required');
assert(ismember(string(policy.phase_semantics),["soft_penalty_equations","nodal_box_kkt"]), ...
 'E036:Semantics','Unknown phase problem; no implicit constraint reinterpretation');
assert(all(isfinite([policy.joint_tol,policy.u_tol,policy.bound_tol,policy.active_tol,policy.history_tol])) ...
 && policy.joint_tol>0 && policy.u_tol>0 && policy.bound_tol>=0 ...
 && policy.active_tol>=0 && policy.active_tol<=policy.bound_tol ...
 && policy.history_tol>=0,'E036:Policy','Invalid tolerances');
assert(numel(d)==numel(lower) && numel(d)==numel(upper) && all(lower<=upper));
assert(all(isfinite(u)) && all(isfinite(d)) && all(isfinite(lower)) && all(isfinite(upper)), ...
 'E036:Nonfinite','Nonfinite final state or bounds');
assert(all(lower>=0) && all(upper==1),'E036:Domain', ...
 'The common damage domain requires nonnegative incoming lower and upper=1');
assert(all(isfinite(old.history(:,:,2:4)),'all'),'E036:Nonfinite','Nonfinite incoming history');
assert(isequal(u(free.fixed_u),state.fixed_u_values(:)) && ...
 isequal(d(free.fixed_d),state.fixed_d_values(:)),'E036:Boundary','Prescribed values changed');
assert(numel(unique(fu))==numel(fu) && numel(unique(fd))==numel(fd));
assert(isequal(sort([fu;free.fixed_u(:)]),(1:numel(u))') && ...
 isequal(sort([fd;free.fixed_d(:)]),(1:numel(d))'),'E036:Dofs','DOF partition invalid');
[ru,raw]=eq(u,d);ru=ru(:);
[rd,trial_history]=pf(d,lower,raw,old.history);rd=rd(:);
assert(numel(ru)==numel(u) && numel(rd)==numel(d),'E036:Shape','Residual size mismatch');
assert(all(isfinite(ru)) && all(isfinite(rd)) && all(isfinite(raw),'all') ...
 && all(isfinite(trial_history(:,:,2:4)),'all'),'E036:Nonfinite','Nonfinite fresh assembly');
% Physical bounds are exact so every accepted state remains an admissible
% incoming lower on the next substep. Only healing uses bound_tol.
feasible=all(d>=0 & d<=1 & d>=lower-policy.bound_tol);
q=rd(fd);lo=d(fd)<=lower(fd)+policy.active_tol;hi=d(fd)>=upper(fd)-policy.active_tol;
both=lo&hi;collapsed=upper(fd)==lower(fd);
q(lo & ~both)=min(q(lo & ~both),0);q(hi & ~both)=max(q(hi & ~both),0);
% A merely narrow interval still has feasible directions. Keep its raw
% residual conservatively when tolerance makes both bounds appear active.
q(collapsed)=0;
ur=norm(ru(fu));dr=norm(rd(fd));kr=norm(q);
if string(policy.phase_semantics)=="nodal_box_kkt",selected=kr;else,selected=dr;end
criterion=max((ur+selected)/policy.joint_tol,ur/policy.u_tol);
assert(all(isfinite([ur,dr,kr,criterion])),'E036:Nonfinite','Nonfinite residual norms');
accepted=feasible && criterion<=1;
audit=struct('u',u,'d',d,'raw',raw,'ru',ru,'rd',rd, ...
 'u_free_l2',ur,'d_raw_free_l2',dr,'d_nodal_box_l2',kr, ...
 'd_selected_l2',selected,'sum_l2',ur+selected,'criterion',criterion, ...
 'phase_semantics',string(policy.phase_semantics),'policy',policy, ...
 'feasible',feasible,'joint_pass',accepted,'history_commits',0, ...
 'f_solve',trial_history(:,:,4),'f_commit',[], ...
 'f_last_inner_return',inner_f,'history234_solve',trial_history(:,:,2:4), ...
 'assembly_calls_u',1,'assembly_calls_d',1,'old_version',old.version);
if ~accepted,return;end
% Build the would-be native commit from final fields and NEW lower=d, but
% OLD incoming history. Do not feed trial_history back as old history.
[~,committed_history]=pf(d,d,raw,old.history);
assert(all(isfinite(committed_history(:,:,2:4)),'all'),'E036:Nonfinite','Nonfinite commit proposal');
delta=max(abs(committed_history(:,:,2:4)-trial_history(:,:,2:4)),[],'all');
assert(delta<=policy.history_tol,'E036:HistoryMapping','Solve/commit history disagree at identical fields');
audit.f_commit=committed_history(:,:,4);audit.commit_history_max_delta=delta;
audit.assembly_calls_d=2;
proposal=struct('u',u,'d',d,'lower',d,'raw',raw,'history',committed_history, ...
 'pre_version',old.version,'version',old.version+1);
end
