function [audit,proposal]=e036_native_candidate(sys,eq,pf,u,d,upper,old,bc,traction,policy,inner_f)
%E036_NATIVE_CANDIDATE Native adapters only; no solve, projection or mutation.
assert(numel(sys.MAT_CHAR)==1 && isfield(policy,'expected_material'), ...
 'E036:Material','Canonical homogeneous material binding is required');
names=fieldnames(policy.expected_material);
for k=1:numel(names)
 name=names{k};expected=policy.expected_material.(name);
 assert(isfield(sys.MAT_CHAR,name) && ...
  abs(sys.MAT_CHAR.(name)-expected)<=1e-12*max(1,abs(expected)), ...
  'E036:Material','Native material differs from the declared acceptance contract');
end
state=struct('u',u,'d',d,'upper',upper+zeros(size(d)), ...
 'fixed_u_values',bc.u,'fixed_d_values',bc.d);
free=struct('u',sys.DOFS.active_dof(:),'d',sys.DOFS.active_dof_pf(:), ...
 'fixed_u',bc.fixed_u,'fixed_d',bc.fixed_d);
[audit,proposal]=phase_field.audit.e036_final_candidate(@mechanical,@phase,state,old,free,policy,inner_f);
audit.native_material=sys.MAT_CHAR;
audit.thickness=sys.GEOM.t;
audit.residual_units='assembled nodal energy derivative; no mass or parameter-gradient normalization';
 function [r,raw]=mechanical(uu,dd)
  [~,r,raw,~]=eq(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
   uu,0.0,dd,sys.stress_state.as_number,0.0);
  r=r-traction;
 end
 function [r,h]=phase(dd,lower,raw,history)
  [~,r,~,h]=pf(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
   dd,lower,raw,sys.stress_state.as_number,history);
 end
end
