function out=e011_coupled_solve(eq,pf,u0,d0,lower,upper,fu,fd,limits,checkpoint)
%E011_COUPLED_SOLVE Fixed-history complete-block alternation, no load commits.
% eq(u,d)->K,Ru,raw; pf(d,raw)->K,Rd,h; neither callback commits history.
u0=u0(:);d0=d0(:);lower=lower(:);upper=upper(:);fu=fu(:);fd=fd(:);
fixed_u=setdiff((1:numel(u0))',fu);fixed_d=setdiff((1:numel(d0))',fd);
counts=struct('u',limits.admission_u,'d',limits.admission_d);
initial=[];current=[];first_u=[];first_block=[];trace=[];inner=[];attempt=[];last_native_attempt=[];last_native_evaluated=[];
stop="outer_budget";failure="";stage="initial_joint_audit";
work_u=[];work_d=[];work_ru=[];work_raw=[];capture_first=false;block=0;
try
 [~,ru,raw]=mechanical(u0,d0);[~,rd,h]=phase(d0,raw);
 current=point(u0,d0,raw,ru,rd,h,0,"initial");initial=current;
 checkpoint(current,trace,counts);
 if current.joint_pass,stop="joint_tolerance";end
 while ~current.joint_pass && block<limits.max_outer
  % Reserve the next completed same-state joint audit inside these caps.
  if limits.max_u-counts.u<2 || limits.max_d-counts.d<3
   stop="assembly_budget";break;
  end
  block=block+1;stage="displacement_inner";
  uout=e011_displacement_solve(@(u)mechanical(u,current.d),current.u,fu,limits.max_u-counts.u-1,limits.u_tol);
  attempt=struct('stage',stage,'u_out',uout);
  if ~uout.returned_residual_available || strlength(uout.failure)>0 || uout.residual_l2>limits.u_tol
   stop="displacement_inner_miss";break;
  end
  work_u=uout.u;work_d=current.d;work_ru=uout.r;work_raw=uout.raw;
  capture_first=isempty(first_u) && block==1;
  stage="constrained_damage_inner";
  dout=e011_damage_solve(@(d)phase(d,work_raw),current.d,lower,upper,fd,"constrained",limits.max_d-counts.d-1,limits.d_tol);
  attempt=struct('stage',stage,'u_out',uout,'d_out',dout);
  summary=struct('outer',block,'u_calls',uout.calls,'d_calls',dout.calls, ...
   'u_stop',uout.stop,'d_stop',dout.stop,'u_trace',uout.trace,'d_trace',dout.trace,'d_trials',dout.trials);
  if isempty(inner),inner=summary;else,inner(end+1)=summary;end %#ok<AGROW>
  if ~dout.returned_residual_available || strlength(dout.failure)>0 || dout.infeasible_nodes>0 || dout.filtered_l2>limits.d_tol
   stop="damage_inner_miss";break;
  end
  stage="post_damage_joint_audit";
  [~,ru,raw]=mechanical(uout.u,dout.d);[~,rd,h]=phase(dout.d,raw);
  next=point(uout.u,dout.d,raw,ru,rd,h,block,"completed_joint");
  du=max(abs(next.u-current.u));dd=max(abs(next.d-current.d));
  row=struct('outer',block,'u_l2',next.u_l2,'d_feasible_l2',next.d_feasible_l2, ...
   'sum_l2',next.sum_l2,'criterion',next.criterion,'joint_pass',next.joint_pass, ...
   'calls_u',counts.u,'calls_d',counts.d,'u_delta_max',du,'d_delta_max',dd, ...
   'zero_u_update',du==0,'zero_d_update',dd==0);
  if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
  current=next;if isempty(first_block),first_block=current;end
  attempt=[];checkpoint(current,trace,counts);
  if current.joint_pass,stop="joint_tolerance";break;end
  if du==0 && dd==0,stop="exact_stagnation";break;end
 end
catch exception
 stop="numerical_failure";failure=string(exception.identifier)+": "+string(exception.message);
end
pass=~isempty(current) && current.joint_pass && stop=="joint_tolerance" && strlength(failure)==0;
out=struct('initial',initial,'first_u',first_u,'first_block',first_block,'final',current, ...
 'trace',trace,'inner',inner,'last_attempt',attempt,'last_native_attempt',last_native_attempt,'last_native_evaluated',last_native_evaluated,'counts',counts,'completed_outer',numel(trace), ...
 'stop',stop,'failure',failure,'failure_stage',stage,'joint_pass',pass,'history_commits',0);
assert(counts.u<=limits.max_u && counts.d<=limits.max_d);
 function [K,r,raw]=mechanical(u,d)
  assert(counts.u<limits.max_u,'E011:UBudget','Mechanical assembly cap');counts.u=counts.u+1;
  last_native_attempt=struct('kind',"mechanical",'u',u,'d',d);
  [K,r,raw]=eq(u,d);r=r(:);
  assert(all(isfinite(nonzeros(K))) && all(isfinite(r)) && all(isfinite(raw),'all'),'Nonfinite coupled mechanical assembly');
  last_native_evaluated=struct('kind',"mechanical",'u',u,'d',d,'r',r,'raw',raw);
 end
 function [K,r,h]=phase(d,raw)
  assert(counts.d<limits.max_d,'E011:DBudget','Phase assembly cap');counts.d=counts.d+1;
  last_native_attempt=struct('kind',"phase",'d',d,'raw',raw);
  [K,r,h]=pf(d,raw);r=r(:);
  assert(all(isfinite(nonzeros(K))) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'),'Nonfinite coupled phase assembly');
  last_native_evaluated=struct('kind',"phase",'d',d,'raw',raw,'r',r,'history234',h(:,:,2:4));
  if capture_first
   assert(isequal(d,work_d));
   first_u=point(work_u,work_d,work_raw,work_ru,r,h,1,"u_only_not_completed_block");
   capture_first=false;
  end
 end
 function s=point(u,d,raw,ru,rd,h,outer,label)
  assert(all(isfinite(u)) && all(isfinite(d)) && all(isfinite(raw),'all'));
  assert(all(isfinite(ru)) && all(isfinite(rd)) && all(isfinite(h(:,:,2:4)),'all'));
  assert(isequal(u(fixed_u),u0(fixed_u)) && isequal(d(fixed_d),d0(fixed_d)),'Prescribed values changed');
  assert(all(d>=lower-1e-12 & d<=upper+1e-12),'Infeasible coupled point');
  q=rd(fd);lo=d(fd)<=lower(fd)+1e-10;hi=d(fd)>=upper(fd)-1e-10;
  q(lo)=min(q(lo),0);q(hi)=max(q(hi),0);q(lo&hi)=0;
  ur=norm(ru(fu));dr=norm(q);total=ur+dr;criterion=max(total/limits.joint_tol,ur/limits.u_tol);
  assert(all(isfinite([ur dr total criterion])),'Nonfinite joint norm');
  s=struct('u',u,'d',d,'raw',raw,'ru',ru,'rd',rd,'history234',h(:,:,2:4), ...
   'outer',outer,'label',label,'u_l2',ur,'d_feasible_l2',dr,'sum_l2',total, ...
   'criterion',criterion,'joint_pass',criterion<=1,'calls',counts);
 end
end
