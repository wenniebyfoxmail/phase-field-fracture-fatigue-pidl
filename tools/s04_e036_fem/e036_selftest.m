function result=e036_selftest()
%E036_SELFTEST Tiny pure callbacks only: no MEX, linear solve or training.
old_history=zeros(1,1,4);old_history(:,:,4)=1;
old=struct('lower',[0;0],'history',old_history,'version',0);
state=struct('u',[0;0],'d',[0;0],'upper',[1;1], ...
 'fixed_u_values',0,'fixed_d_values',0);
free=struct('u',1,'d',1,'fixed_u',2,'fixed_d',2);
box=e036_policy('fresh_original_tolerances','nodal_box_kkt');
soft=e036_policy('fresh_original_tolerances','soft_penalty_equations');
ru=[0;1e9];rd=[1;1e9];calls_u=0;calls_d=0;
% At pristine AT1 lower bound, positive raw force is a normal reaction.
[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(a.joint_pass && a.d_raw_free_l2==1 && a.d_nodal_box_l2==0 && n.version==1);
assert(calls_u==1 && calls_d==2 && isequal(old.history,old_history));
assert(isequal(a.f_solve,a.f_commit) && a.history_commits==0);
[a,n]=e036_final_candidate(@eq,@pf,state,old,free,soft,1);
assert(~a.joint_pass && isempty(n) && a.assembly_calls_d==1);
% Wrong-sign force on a lower bound is not a reaction and must fail.
rd(1)=-1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && isempty(n) && a.d_nodal_box_l2==1);
% Interior nonzero residual cannot be removed by bound filtering.
state.d(1)=.5;rd(1)=1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && isempty(n));
% Upper-bound negative reaction passes; positive force fails.
state.d(1)=1;rd(1)=-1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(a.joint_pass && ~isempty(n));
rd(1)=1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && isempty(n));
% Near both bounds does not collapse a nonzero feasible interval.
old.lower(1)=1-1e-10;state.d(1)=1-5e-11;rd(1)=1;
[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && a.d_nodal_box_l2==1 && isempty(n));
old.lower(1)=1;state.d(1)=1;
[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(a.joint_pass && a.d_nodal_box_l2==0 && ~isempty(n));old.lower(1)=0;
% No silent clipping: out-of-domain field stays unchanged and is rejected.
state.d(1)=1+1e-4;rd(1)=-1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && ~a.feasible && isempty(n) && a.d(1)==state.d(1));
% A tiny physical-bound violation cannot become an invalid next-step lower.
state.d(1)=-1e-9;rd(1)=1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && ~a.feasible && isempty(n));
state.d(1)=1+1e-9;rd(1)=-1;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && ~a.feasible && isempty(n));
% Fresh mechanical field can veto a cached/inner phase pass.
state.d(1)=0;rd(1)=1;ru(1)=2e-6;[a,n]=e036_final_candidate(@eq,@pf,state,old,free,box,1);
assert(~a.joint_pass && a.criterion==2 && isempty(n));
% Prescribed values and NaNs fail before commit proposal.
ru(1)=0;bad=state;bad.d(2)=.1;
reject(@()e036_final_candidate(@eq,@pf,bad,old,free,box,1),'E036:Boundary');
ru(1)=NaN;
reject(@()e036_final_candidate(@eq,@pf,state,old,free,box,1),'E036:Nonfinite');
% Invalid domain/tolerance contracts cannot use reaction filtering to pass.
ru(1)=0;bad_policy=box;bad_policy.active_tol=2*box.bound_tol;
reject(@()e036_final_candidate(@eq,@pf,state,old,free,bad_policy,1),'E036:Policy');
bad_old=old;bad_old.lower(1)=-1e-5;
reject(@()e036_final_candidate(@eq,@pf,state,bad_old,free,box,1),'E036:Domain');
bad=state;bad.upper(1)=2;
reject(@()e036_final_candidate(@eq,@pf,bad,old,free,box,1),'E036:Domain');
result=struct('status','passed','cases',17,'native_solves',0,'history_commits',0);
 function [r,raw]=eq(u,d)
  calls_u=calls_u+1;assert(isequal(u,state.u) && isequal(d,state.d));r=ru;raw=.1;
 end
 function [r,h]=pf(d,lower,raw,history)
  calls_d=calls_d+1;assert(isequal(history,old_history) && raw==.1);
  assert(isequal(lower,old.lower) || isequal(lower,d));r=rd;h=old_history;
  q=(1-d(1))^2*raw;h(:,:,2)=max(q-old_history(:,:,3),0);h(:,:,3)=q;
  h(:,:,4)=min(1,(1/(h(:,:,2)+.5))^2);
 end
end
function reject(f,expected)
try
 f();
catch ex
 assert(strcmp(ex.identifier,expected));return;
end
error('E036:MissingGuard','Expected rejection was absent');
end
