function out=e011_s2ra_mechanical(sys,native,u0,d,free,budget,tol,refresh)
% Native cached return versus same-direction fresh return. No external RHS.
calls=0;last=[];u=u0;raw=[];value=NaN;non_conv=true;failure="";
if refresh
 out=e011_s2ra_fresh_u(@matrix,u0,free,budget,tol);
 out.policy_pass=out.returned_residual_available && strlength(out.failure)==0 && out.residual_l2<tol;
 out.residual_state="returned";
 if isempty(last),out.evaluated_u=[];else,out.evaluated_u=last.u;end
 assert(calls==out.calls);return;
end
try
 [~,value,u,raw,~,non_conv]=phase_field.fem.solver.newton_raphson(@counted,sys,u0,0.0,d,0.0, ...
  free,sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col, ...
  'max_iter',budget,'res_tol',tol,'D_RHS_tract',0.0,'line_search',false);
 assert(all(isfinite(u)) && isfinite(value),'E011:Nonfinite','Nonfinite native mechanical return');
catch ex
 failure=string(ex.identifier)+": "+string(ex.message);
end
out=struct('u',u,'raw',raw,'calls',calls,'residual_l2',value,'failure',failure, ...
 'policy_pass',~non_conv && strlength(failure)==0 && value<tol,'residual_state',"pre_last_update", ...
 'evaluated_u',[],'r',[]);
if ~isempty(last),out.evaluated_u=last.u;out.r=last.r;end
assert(calls<=budget);
 function [kv,r,raw,h]=counted(varargin)
  assert(calls<budget,'E011:UBudget','Mechanical inner cap');calls=calls+1;
  [kv,r,raw,h]=native(varargin{:});
  assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(raw),'all'),'E011:Nonfinite','Nonfinite mechanical fixture/callback');
  last=struct('u',varargin{7},'r',r,'raw',raw);
 end
 function [K,r,raw]=matrix(x)
  [kv,r,raw,~]=counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,x,0.0,d,sys.stress_state.as_number,0.0);
  K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
 end
end
