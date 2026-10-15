function out=e011_displacement_solve(evaluate,u0,free,maxeval,tol)
%E011_DISPLACEMENT_SOLVE Native Newton with fresh same-returned-field stopping.
u=u0(:);free=free(:);fixed=setdiff((1:numel(u))',free);bc=u(fixed);
assert(all(isfinite(u)) && maxeval>=1 && tol>0);
calls=0;accepted=0;r=[];raw=[];trace=[];failure="";stop="budget";
last_attempted_u=u;last_evaluated_u=[];stage="initial_assembly";
try
 [K,r,raw]=call(u);
 while true
  value=norm(r(free));assert(isfinite(value),'Nonfinite mechanical norm');
  row=struct('calls',calls,'accepted',accepted,'residual_l2',value);
  if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
  if value<=tol,stop="fresh_tolerance";break;end
  if calls>=maxeval,break;end
  stage="factorization";
  delta=cholmod2(K(free,free),-r(free));assert(all(isfinite(delta)),'Nonfinite displacement direction');
  trial=u;trial(free)=u(free)+delta;assert(isequal(trial(fixed),bc));
  stage="trial_assembly";[Kt,rt,rawt]=call(trial);
  u=trial;K=Kt;r=rt;raw=rawt;accepted=accepted+1;
 end
catch exception
 stop="numerical_failure";failure=string(exception.identifier)+": "+string(exception.message);
end
value=NaN;
if ~isempty(r)
 value=norm(r(free));
 if ~isfinite(value),stop="numerical_failure";failure=failure+" | nonfinite final norm";end
end
out=struct('u',u,'r',r,'raw',raw,'calls',calls,'accepted',accepted,'trace',trace, ...
 'residual_l2',value,'stop',stop,'failure',failure,'returned_residual_available',~isempty(r), ...
 'last_attempted_u',last_attempted_u,'last_evaluated_u',last_evaluated_u,'failure_stage',stage);
assert(isequal(u(fixed),bc) && calls<=maxeval);
 function [K,r,raw]=call(x)
  last_attempted_u=x;assert(calls<maxeval);calls=calls+1;
  assert(all(isfinite(x)),'Nonfinite attempted displacement');
  [K,r,raw]=evaluate(x);r=r(:);
  assert(all(isfinite(nonzeros(K))) && all(isfinite(r)) && all(isfinite(raw),'all'),'Nonfinite native mechanical assembly');
  last_evaluated_u=x;
 end
end
