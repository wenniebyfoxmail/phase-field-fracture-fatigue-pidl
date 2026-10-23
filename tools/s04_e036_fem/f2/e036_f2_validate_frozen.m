function [model,receipt]=e036_f2_validate_frozen(native,g,d,raw,old,free,two_points)
%E036_F2_VALIDATE_FROZEN In-job actual-native binding, never a fake frozen f.
% native(x) retains the REAL old history and recomputes its own trial f.
% Its current-f result is checked against explicit Q4 integration at each
% point; the separate anchor-f quadratic is checked by energy differences.
% No MATLAB execution has yet validated this preparation.
atol=1e-10;rtol=1e-8;d=d(:);free=free(:);
[Kn,rn,hn]=native(d);f=hn(:,:,4);
[H,r,E,branch,b]=e036_f2_quadratic(g,d,raw,f,old.lower);
anchor=compare(Kn,rn,H,r);history_check(d,hn);
probe=[];energy_check=[];probe_history=[];
if two_points
 x=d;target=.5*(old.lower(:)+1);x(free)=d(free)+1e-3*(target(free)-d(free));
 assert(any(x~=d),'E036F2:Probe','A distinct predeclared feasible two-point direction is required');
 assert(all(x>=old.lower(:) & x<=1));
 [Kx,rx,hx]=native(x);history_check(x,hx);
 [Hx,rx_explicit,~,probe_branch]=e036_f2_quadratic(g,x,raw,hx(:,:,4),old.lower);
 probe=compare(Kx,rx,Hx,rx_explicit);
 [Hf,rf,Ex,~,bf]=e036_f2_quadratic(g,x,raw,f,old.lower);
 frozen=compare(Hf,rf,H,H*x+b);close(bf,b,'Frozen linear coefficient changed');
 v=x-d;direct=Ex-E;predicted=r'*v+.5*v'*(H*v);
 close(direct,predicted,'Frozen quadratic energy difference differs');
 energy_check=struct('direct_energy_delta',direct,'quadratic_energy_delta',predicted, ...
  'absolute_error',abs(direct-predicted),'frozen_gradient',frozen,'probe_branch',probe_branch);
 probe_history=struct('actual_native_f_delta_max',max(abs(hx(:,:,4)-f),[],'all'), ...
  'scope','native probe uses its own recomputed f; frozen comparison separately uses anchor f');
end
model=struct('H',H,'b',b,'f',f,'anchor',d,'history_diagnostic_only',hn, ...
 'energy_anchor',E,'history_commits',0);
receipt=struct('schema','e036-f2-frozen-native-check-v1','accepted',true, ...
 'two_points',logical(two_points),'atol',atol,'rtol',rtol,'anchor_native',anchor, ...
 'anchor_branch',branch,'probe_native',probe,'probe_history',probe_history, ...
 'energy_check',energy_check,'old_history_modified',false,'native_f_overridden',false);
 function z=compare(Knative,rnative,Kexplicit,rexplicit)
  ek=maxabs(Knative-Kexplicit);er=maxabs(rnative(:)-rexplicit(:));
  assert(ek<=atol+rtol*maxabs(Knative) && er<=atol+rtol*maxabs(rnative), ...
   'E036F2:NativeMismatch','Native current-f tangent/residual and explicit physical quadratic differ');
  z=struct('matrix_max_abs_error',ek,'residual_max_abs_error',er, ...
   'matrix_native_scale',maxabs(Knative),'residual_native_scale',maxabs(rnative));
 end
 function close(a,b,message)
  assert(maxabs(a-b)<=atol+rtol*max(maxabs(a),maxabs(b)),'E036F2:Energy','%s',message);
 end
 function history_check(x,h)
  dg=x(g.cells)*g.N;driver=((1-dg).^2+g.material.res_stiff).*raw;
  A=old.history(:,:,2)+max(driver-old.history(:,:,3),0);
  expected=min(1,(2*g.material.alpha_T./(A+g.material.alpha_T)).^g.material.p);
  close(h(:,:,2),A,'Native trial accumulated history differs');
  close(h(:,:,3),driver,'Native active driver differs');close(h(:,:,4),expected,'Native f law differs');
 end
end
function value=maxabs(a)
if issparse(a),a=nonzeros(a);end
if isempty(a),value=0;else,value=max(abs(a),[],'all');end
assert(isfinite(value),'E036F2:Nonfinite','Nonfinite comparison');
end
