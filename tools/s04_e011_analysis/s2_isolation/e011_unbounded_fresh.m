function out=e011_unbounded_fresh(evaluate,d0,lower,upper,free,maxeval,tol)
%E011_UNBOUNDED_FRESH Original phase Newton direction, fresh stop; clip at return.
d=d0(:);free=free(:);fixed=setdiff((1:numel(d))',free);bc=d(fixed);
calls=0;trace=[];failure="";stop="budget";r=[];h=[];
while calls<maxeval
 [K,r,h]=evaluate(d);calls=calls+1;r=r(:);
 assert(all(isfinite(nonzeros(K))) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'),'E011:Nonfinite','Nonfinite unbounded assembly');
 value=norm(r(free));row=struct('call',calls,'raw_l2',value,'dmin',min(d),'dmax',max(d));
 if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
 if value<=tol,stop="fresh_tolerance";break;end
 if calls==maxeval,break;end
 A=K(free,free);A=.5*(A+A');shift=max(0,-min(full(diag(A)))+1e-8);ok=false;
 for k=1:8
  delta=cholmod2(A+shift*speye(size(A,1)),-r(free));
  if all(isfinite(delta)),ok=true;break;end
  shift=max(1e-8,10*max(shift,1e-12));
 end
 assert(ok,'E011:Nonfinite','Nonfinite phase direction');d(free)=d(free)+delta;
 assert(isequal(d(fixed),bc) && all(isfinite(d)),'E011:Nonfinite','Nonfinite phase update');
end
unclipped=d;d=min(max(d,lower),upper);infeasible=nnz(d<lower-1e-12|d>upper+1e-12);
if isempty(r),value=Inf;end
out=struct('d',d,'unclipped',unclipped,'r',r,'history',h,'calls',calls,'stop',stop,'failure',failure, ...
 'returned_residual_available',~isempty(r),'infeasible_nodes',infeasible,'filtered_l2',value, ...
 'raw_l2_before_clip',value,'trace',trace,'trials',[]);
end
