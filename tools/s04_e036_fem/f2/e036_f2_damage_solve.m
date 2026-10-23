function out=e036_f2_damage_solve(evaluate,d0,lower,upper,free,mode,maxeval,tol)
%E036_F2_DAMAGE_SOLVE Isolated constrained core; no history propagation.
% Derived from tools/s04_e011_analysis/constrained_damage/e011_damage_solve.m
% Source SHA256: 9ba0a0ecc17811c1be0651623a712026d90a99076f7b7621e9a5b2bd232596b5
% Prepared source only; no MATLAB syntax or numerical validation.
% Caller owns frozen-f semantics, assembly time guards and final E036 admission.
% A terminal budget/stall/nonfinite failure returns without an automatic retry.
% evaluate(d) returns K, fresh residual, and trial history/diagnostics.
% maxeval counts every callback, including rejected trials. No cached stop.
assert(isscalar(string(mode)) && string(mode)=="constrained");
d=d0(:);lower=lower(:);upper=upper(:);free=free(:);
assert(all(isfinite(d)) && all(isfinite(lower)) && all(isfinite(upper)));
assert(numel(d)==numel(lower) && numel(d)==numel(upper));
assert(all(lower>=0 & lower<=upper) && all(upper==1) && all(d>=lower & d<=upper), ...
 'E036F2:Bounds','Exact feasible physical-box input required; no input repair');
fixed=setdiff((1:numel(d))',free);fixed_values=d(fixed);
assert(isscalar(maxeval) && isfinite(maxeval) && maxeval==fix(maxeval) && maxeval>=2 && ...
 isscalar(tol) && isfinite(tol) && tol>0);
calls=0;factorizations=0;iterations=0;accepted=0;trace=[];trials=[];scale=[];
K=[];r=[];h=[];stop="budget";failure="";last_attempted_d=d;last_evaluated_d=[];failure_stage="initial_assembly";
try
[K,r,h]=call(d);scale=full(diag(K));
assert(all(isfinite(scale(free))) && all(scale(free)>0),'E036F2:BadDiagonal','Nonpositive native phase diagonal');
scale=max(scale,eps);failure_stage="iteration";
while true
 [filtered,natural]=metrics(d,r);raw=norm(r(free));
 criterion=filtered;
 row=struct('calls',calls,'accepted',accepted,'raw_l2',raw, ...
  'filtered_l2',filtered,'natural_l2',natural,'infeasible_nodes',nnz(d<lower | d>upper),'lambda',NaN,'direction',"none");
 if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
 if criterion<=tol,stop="fresh_tolerance";break;end
 if calls>=maxeval,break;end
 iterations=iterations+1;
 K=.5*(K+K');
 % Primal/dual prediction includes active-variable displacement in free RHS.
 predicted=d-r./scale;
 aLo=free(predicted(free)<=lower(free));
 aHi=free(predicted(free)>=upper(free) & predicted(free)>lower(free));
 aset=unique([aLo;aHi]);inactive=setdiff(free,aset);
 delta=zeros(size(d));delta(aLo)=lower(aLo)-d(aLo);delta(aHi)=upper(aHi)-d(aHi);
 if ~isempty(inactive)
  failure_stage="active_set_factorization";
  factorizations=factorizations+1;
  delta(inactive)=cholmod2(K(inactive,inactive),-r(inactive)-K(inactive,aset)*delta(aset));
 end
 assert(all(isfinite(delta)),'Nonfinite active-set direction');
 ok=false;oldnatural=natural;
 for direction=1:2
  if direction==2
   delta=min(max(d-r./scale,lower),upper)-d;delta(fixed)=0;
  end
  for j=0:20
   if calls>=maxeval,break;end
   lambda=2^(-j);trial=min(max(d+lambda*delta,lower),upper);trial(fixed)=fixed_values;
   if isequal(trial,d),continue;end
   failure_stage="constrained_trial_assembly";
   [Kt,rt,ht]=call(trial);[ft,nt]=metrics(trial,rt);
   % Both merit descent and endpoint feasibility are evaluated at this trial.
   admissible=ft<=tol || nt <= (1-1e-4*lambda)*oldnatural;
   tr=struct('call',calls,'iteration',iterations,'direction',direction,'lambda',lambda,'filtered_l2',ft,'natural_l2',nt,'admissible',admissible);
   if isempty(trials),trials=tr;else,trials(end+1)=tr;end %#ok<AGROW>
   if admissible
    d=trial;K=Kt;r=rt;h=ht;ok=true;accepted=accepted+1;
    trace(end).lambda=lambda;
    if direction==1,trace(end).direction="active_set";else,trace(end).direction="projected_diagonal";end
    break;
   end
  end
  if ok || calls>=maxeval,break;end
 end
 if ~ok
  if calls>=maxeval,stop="budget";else,stop="line_search_stall";end
  break;
 end
end
catch exception
 stop="numerical_failure";failure=string(exception.identifier)+": "+string(exception.message);
end
filtered=NaN;natural=NaN;raw=NaN;
if ~isempty(r) && ~isempty(scale) && all(isfinite(scale(free))) && all(scale(free)>0)
 try
  [filtered,natural]=metrics(d,r);raw=norm(r(free));assert(isfinite(raw),'Nonfinite raw norm');
 catch exception
  filtered=NaN;natural=NaN;raw=NaN;stop="numerical_failure";
  failure=failure+" | final metrics: "+string(exception.message);
 end
end
out=struct('d',d,'r',r,'history',h,'calls',calls,'factorizations',factorizations,'iterations',iterations,'accepted',accepted, ...
 'stop',stop,'raw_l2',raw,'filtered_l2',filtered,'natural_l2',natural, ...
 'trace',trace,'trials',trials,'infeasible_nodes',nnz(d<lower | d>upper), ...
 'returned_residual_available',~isempty(r),'scale',scale,'history_commits',0,'failure',failure, ...
 'last_attempted_d',last_attempted_d,'last_evaluated_d',last_evaluated_d,'last_accepted_d',d,'failure_stage',failure_stage);
assert(isequal(d(fixed),fixed_values) && calls<=maxeval);
assert(out.infeasible_nodes==0);

 function [kk,rr,hh]=call(x)
  last_attempted_d=x;assert(calls<maxeval);calls=calls+1;
  assert(all(isfinite(x)),'Nonfinite attempted field');
  assert(all(x>=lower & x<=upper) && isequal(x(fixed),fixed_values), ...
   'E036F2:Bounds','Every evaluated trial must retain exact box and fixed DOFs');
  [kk,rr,hh]=evaluate(x);rr=rr(:);
  assert(all(isfinite(nonzeros(kk))) && all(isfinite(rr)) && all(isfinite(hh(:,:,2:4)),'all'),'Nonfinite assembly');
  last_evaluated_d=x;
 end
 function [f,n]=metrics(x,rr)
  assert(all(isfinite(rr)) && all(isfinite(x)),'Nonfinite pre-filter residual');
  q=rr(free);lo=x(free)<=lower(free)+1e-10;hi=x(free)>=upper(free)-1e-10;
  both=lo&hi;collapsed=upper(free)==lower(free);
  q(lo & ~both)=min(q(lo & ~both),0);q(hi & ~both)=max(q(hi & ~both),0);
  % E036 keeps raw residual in narrow noncollapsed boxes; only exact collapse is fixed.
  q(collapsed)=0;f=norm(q);
  z=scale(free).*(x(free)-min(max(x(free)-rr(free)./scale(free),lower(free)),upper(free)));
  n=norm(z);assert(isfinite(f) && isfinite(n));
 end
end
