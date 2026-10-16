function out=e011_s2ra_coupled(eq,pf,usolve,u0,d0,lower,upper,fu,fd,limits,checkpoint,refresh)
% One controller, independent refresh and tolerance factors; no state commits.
fu=fu(:);fd=fd(:);lower=lower(:);upper=upper(:);
counts=struct('u',0,'d',0);current=[];trace=[];attempt=[];failure="";stop="outer_budget";block=0;
fixed_u=setdiff((1:numel(u0))',fu);fixed_d=setdiff((1:numel(d0))',fd);
try
 [~,ru,raw]=mechanical(u0,d0);[~,rd,h]=phase(d0,raw);
 current=point(u0,d0,raw,ru,rd,h,0,feasible(d0,rd),[]);
 checkpoint(current,trace,counts);
 while block<limits.max_outer
  if limits.max_u-counts.u<3 || limits.max_d-counts.d<3,stop="assembly_budget";break;end
  block=block+1;
  uout=usolve(current.u,current.d,limits.max_u-counts.u-2,limits.u_tol,refresh);
  counts.u=counts.u+uout.calls;attempt=struct('stage',"displacement_inner",'u_out',uout);
  if ~uout.policy_pass,stop="displacement_inner_miss";break;end
  % Identical observational callback in BOTH R cells; never fed to cached phase.
  [~,before_ru,before_raw]=mechanical(uout.u,current.d);
  input=struct('u_evaluated',uout.evaluated_u,'u_returned',uout.u,'raw',uout.raw, ...
   'fresh_before_raw',before_raw,'fresh_before_ru',before_ru,'d_before',current.d, ...
   'cached_u_residual_l2',uout.residual_l2,'mechanical_residual_state',uout.residual_state);
  dout=e011_damage_solve(@(x)phase(x,input.raw),current.d,lower,upper,fd,"constrained",limits.max_d-counts.d-1,limits.d_tol);
  attempt=struct('stage',"damage_inner",'u_out',uout,'d_out',dout,'phase_input',input);
  if ~dout.returned_residual_available || strlength(dout.failure)>0 || dout.infeasible_nodes>0 || dout.filtered_l2>limits.d_tol
   stop="damage_inner_miss";break;
  end
  input.cached_rd=dout.r;input.cached_history234=dout.history(:,:,2:4);
  [~,ru,raw]=mechanical(uout.u,dout.d);[~,rd,h]=phase(dout.d,raw);
  next=point(uout.u,dout.d,raw,ru,rd,h,block,dout.filtered_l2,input);
  du=max(abs(next.u-current.u));dd=max(abs(next.d-current.d));
  row=struct('outer',block,'policy_C',next.policy_C,'fresh_C',next.criterion, ...
   'u_l2',next.u_l2,'d_cached_l2',next.d_cached_l2,'d_fresh_l2',next.d_feasible_l2, ...
   'raw_timing_scaled_maxerr',next.raw_timing_scaled_maxerr,'raw_damage_scaled_maxerr',next.raw_damage_scaled_maxerr, ...
   'u_calls',counts.u,'d_calls',counts.d,'u_delta_max',du,'d_delta_max',dd);
  if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
  attempt.stage="completed_block";current=next;checkpoint(current,trace,counts);
  fprintf('[E011_S2RA_OUTER] outer=%d policyC=%.10g freshC=%.10g Rd_cached/fresh=%.6g/%.6g\n',block,next.policy_C,next.criterion,next.d_cached_l2,next.d_feasible_l2);
  if next.policy_pass,stop="policy_tolerance";break;end
  if du==0 && dd==0,stop="exact_stagnation";break;end
 end
catch ex
 stop="numerical_failure";failure=string(ex.identifier)+": "+string(ex.message);
end
accepted=~isempty(current) && current.policy_pass && stop=="policy_tolerance" && strlength(failure)==0;
out=struct('final',current,'trace',trace,'last_attempt',attempt,'counts',counts, ...
 'completed_outer',numel(trace),'stop',stop,'failure',failure,'policy_pass',accepted,'history_commits',0);
assert(counts.u<=limits.max_u && counts.d<=limits.max_d);
 function [K,r,raw]=mechanical(u,d)
  assert(counts.u<limits.max_u,'E011:UBudget','Mechanical cap');counts.u=counts.u+1;
  [K,r,raw]=eq(u,d);assert(all(isfinite(nonzeros(K))) && all(isfinite(r)) && all(isfinite(raw),'all'),'E011:Nonfinite','Nonfinite mechanics');
 end
 function [K,r,h]=phase(d,raw)
  assert(counts.d<limits.max_d,'E011:DBudget','Phase cap');counts.d=counts.d+1;
  [K,r,h]=pf(d,raw);assert(all(isfinite(nonzeros(K))) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'),'E011:Nonfinite','Nonfinite phase');
 end
 function value=feasible(d,r)
  q=r(fd);lo=d(fd)<=lower(fd)+1e-10;hi=d(fd)>=upper(fd)-1e-10;
  q(lo)=min(q(lo),0);q(hi)=max(q(hi),0);q(lo&hi)=0;value=norm(q);
 end
 function p=point(u,d,raw,ru,rd,h,outer,cached,input)
  assert(all(d>=lower-1e-12 & d<=upper+1e-12));
  assert(isequal(u(fixed_u),u0(fixed_u)) && isequal(d(fixed_d),d0(fixed_d)));
  ur=norm(ru(fu));dr=feasible(d,rd);[policy_C,eligible]=e011_s2ra_stop(ur,cached,dr,limits,refresh,outer);
  p=struct('u',u,'d',d,'raw',raw,'ru',ru,'rd',rd,'history234',h(:,:,2:4), ...
   'outer',outer,'u_l2',ur,'d_feasible_l2',dr,'d_cached_l2',cached,'policy_C',policy_C, ...
   'policy_pass',eligible,'criterion',max((ur+dr)/4e-6,ur/1e-8),'phase_input',input, ...
   'raw_timing_scaled_maxerr',0,'raw_damage_scaled_maxerr',0);
  if ~isempty(input)
   p.raw_timing_scaled_maxerr=max(abs(input.raw-input.fresh_before_raw)./max(1,abs(input.fresh_before_raw)),[],'all');
   p.raw_damage_scaled_maxerr=max(abs(raw-input.fresh_before_raw)./max(1,abs(raw)),[],'all');
  end
  assert(all(isfinite([ur dr cached policy_C p.criterion])),'E011:Nonfinite','Nonfinite norms');
 end
end
