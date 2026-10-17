function [result,predictor,Kcache]=e011_s2uj_case(bits,pre,start,sys,eq,pf,par,folder,ref,cache_check,predictor_check)
% Fixed fresh/strict constrained phase; separate inner u and joint/outer-u tolerances.
assert(~isfolder(folder));mkdir(folder);frozen=pre;U=bits(1);J=bits(2);R=1;
assert(all(ismember(bits,[0 1])) && ~par.step.line_search && sys.MAT_CHAR.p==2);
counts=struct('u',0,'d',0);current=[];out=[];first=[];ledger=[];fatal=false;reason="not_started";accepted=false;predictor=[];Kcache=[];
limits=e011_s2uj_limits(U,J);
try
 [Kcache,~,~]=matrix_eq(start.u,start.d);
 if ~isempty(cache_check),assert(isequal(Kcache,cache_check),'E011:CacheMismatch','Cache differs');end
 sys.STIFFNESS_MATRIX.KK=Kcache;
 [predicted,r,D_RHS]=phase_field.fem.solver.step.pre_iter_update(2,sys,start.u,par.step);
 predictor=struct('u',predicted,'r',r,'d',start.d);assert(all(D_RHS==0));
 if ~isempty(predictor_check),assert(isequaln(predictor,predictor_check),'E011:PredictorMismatch','Predictor differs');end
 out=e011_s2ra_coupled(@matrix_eq,@matrix_pf,@usolve,predicted,start.d,pre.lower,ones(size(start.d)),sys.DOFS.active_dof,sys.DOFS.active_dof_pf,limits,@checkpoint,R);
 assert(out.counts.u==counts.u-1 && out.counts.d==counts.d,'E011:CountsMismatch','Callback counts differ');
 nested=e011_s2i_fatal(out);if strlength(nested)>0,error('E011:ControllerFailure','%s',nested);end
 accepted=out.policy_pass;reason=out.stop;
catch ex
 reason=string(ex.identifier)+": "+string(ex.message);
 if ~startsWith(reason,"E011:UBudget:") && ~startsWith(reason,"E011:DBudget:"),fatal=true;end
end
reference=struct('required',~isempty(ref),'pass',false);
try
 if ~isequaln(pre,frozen),error('E011:HistoryChanged','Old predecessor changed');end
 if ~isempty(ref) && ~fatal
  reference.u_maxerr=max(abs(current.u-ref.current.u));reference.d_maxerr=max(abs(current.d-ref.current.d));
  reference.history234_scaled_maxerr=max(abs(current.history234-ref.current.history234)./max(1,abs(ref.current.history234)),[],'all');
  reference.raw=e011_raw_equivalence(sys.MESH.node(:,1:2),sys.MESH.elem(:,1:4),current.u,current.raw,ref.current.u,ref.current.raw,sys.QUADRATURE);
  reference.outer=current.outer;reference.expected_outer=ref.current.outer;
  reference.pass=accepted && reference.u_maxerr<=1e-10 && reference.d_maxerr<=1e-10 && reference.history234_scaled_maxerr<=1e-10 && reference.raw.pass && reference.outer==reference.expected_outer;
  assert(reference.pass,'E011:AnchorMismatch','S2I anchor differs');
 end
catch ex
 fatal=true;accepted=false;reason=string(ex.identifier)+": "+string(ex.message);
end
if isempty(current),C=NaN;PC=NaN;outer=0;else,C=current.criterion;PC=current.policy_C;outer=current.outer;end
result=struct('U',U,'J',J,'refresh',R,'status','miss','accepted',accepted && ~fatal,'reason',reason,'fresh_C',C,'policy_C',PC, ...
 'outer',outer,'u_calls',counts.u,'phase_calls',counts.d,'reference',reference,'fatal',fatal,'history_commits',0);
if result.accepted,result.status='accepted';end
save(fullfile(folder,'case.mat'),'pre','start','predictor','current','first','out','ledger','counts','limits','result','reference','-v7.3');
fid=fopen(fullfile(folder,'result.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
fprintf('[E011_S2UJ_CASE] U%dJ%d accepted=%d policyC=%.10g freshC=%.10g outer=%d calls=%d/%d\n',U,J,result.accepted,PC,C,outer,counts.u,counts.d);
assert(counts.u<=250 && counts.d<=250);
if fatal,error('E011:FatalCase','%s',reason);end
 function value=usolve(u,d,budget,tol,refresh)
  value=e011_s2ra_mechanical(sys,@eq_counted,u,d,sys.DOFS.active_dof,budget,tol,refresh);
 end
 function [kv,r,raw,h]=eq_counted(varargin)
  assert(counts.u<249,'E011:UBudget','Native mechanical cap');counts.u=counts.u+1;
  ok=all(isfinite(varargin{7}));if ~ok,fatal=true;end
  assert(ok,'E011:Nonfinite','Nonfinite input u');
  [kv,r,raw,h]=eq(varargin{:});ok=all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(raw),'all');
  if ~ok,fatal=true;end
  assert(ok,'E011:Nonfinite','Nonfinite mechanics');
 end
 function [K,r,raw]=matrix_eq(u,d)
  [kv,r,raw,~]=eq_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,u,0.0,d,sys.stress_state.as_number,0.0);
  K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
 end
 function [K,r,h]=matrix_pf(d,raw)
  assert(counts.d<248,'E011:DBudget','Native phase cap');counts.d=counts.d+1;
  [kv,r,~,h]=pf(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d,pre.lower,raw,sys.stress_state.as_number,pre.history);
  ok=all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all');if ~ok,fatal=true;end
  assert(ok,'E011:Nonfinite','Nonfinite phase');
  row=struct('call',counts.d,'dmin',min(d),'dmax',max(d),'lower_violations',nnz(d<pre.lower-1e-12),'upper_violations',nnz(d>1+1e-12),'alpha_max',max(h(:,:,2),[],'all'),'f_min',min(h(:,:,4),[],'all'));
  if isempty(ledger),ledger=row;else,ledger(end+1)=row;end %#ok<AGROW>
  K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
 end
 function checkpoint(point,trace,calls)
  point.controls=struct('U',U,'J',J,'refresh',R,'limits',limits);current=point;if point.outer==1,first=point;end
  save(fullfile(folder,sprintf('outer_%02d.mat',point.outer)),'point','trace','calls','-v7.3');
 end
end
