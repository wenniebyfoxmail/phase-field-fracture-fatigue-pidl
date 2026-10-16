function [result,predictor,Kcache]=e011_s2i_case(bits,pre,start,sys,eq,pf,par,folder,ref,cache_check,predictor_check)
%E011_S2I_CASE Same-origin bounded 3-control diagnostic; no accepted commits.
assert(~isfolder(folder));mkdir(folder);frozen=pre;
D=bits(1);S=bits(2);F=bits(3);assert(ismember(D,[0 1]) && ismember(S,[0 1 2]) && ismember(F,[0 1]));
mat=sys.MAT_CHAR;assert(isscalar(mat) && mat.p==2 && mat.alpha_T==.5);mat0=mat;mat0.p=0;
counts=struct('u',0,'d',0);core_d_cap=248-2*F;
predictor=[];Kcache=[];current=[];first=[];out=[];ledger=[];worst=[];stage="cache";accepted=false;reason="not_started";fatal=false;
try
 [Kcache,~,~]=matrix_eq(start.u,start.d);
 if ~isempty(cache_check),assert(isequal(Kcache,cache_check),'E011:CacheMismatch','Cache mismatch');end
 sys.STIFFNESS_MATRIX.KK=Kcache;
 [predicted,res_displ,D_RHS]=phase_field.fem.solver.step.pre_iter_update(2,sys,start.u,par.step);
 predictor=struct('u',predicted,'r',res_displ,'d',start.d);assert(all(D_RHS==0));
 if ~isempty(predictor_check),assert(isequaln(predictor,predictor_check),'E011:PredictorMismatch','Predictor mismatch');end
 stage="algorithm";par.stag.max_iter=20;
 if S==0
  [~,iru,iraw]=matrix_eq(predicted,start.d);[~,ird,ih]=matrix_pf(start.d,iraw);checkpoint(make_point(predicted,start.d,iraw,iru,ird,ih,0),[],counts);
  if D==0
   out=e011_original_observed(sys,@eq_counted,@pf_counted,predicted,start.d,pre.lower,pre.history,res_displ,D_RHS,par,folder,@read_counts,2,@observe,@remaining_d);
  else
   out=e011_original_bounded(sys,@eq_counted,@pf_counted,predicted,start.d,pre.lower,pre.history,res_displ,D_RHS,par,folder,@read_counts,2,@observe,@remaining_d);
  end
  accepted=out.native_accepted;reason="cached_acceptance";
 else
  if S==1,u_tol=1e-8;d_tol=4e-6;joint_tol=4e-6;else,u_tol=1e-6;d_tol=4e-4;joint_tol=4e-4;end
  limits=struct('admission_u',0,'admission_d',0,'max_u',248,'max_d',core_d_cap,'max_outer',20,'u_tol',u_tol,'d_tol',d_tol,'joint_tol',joint_tol);
  out=e011_s2i_coupled(@matrix_eq,@matrix_pf,predicted,start.d,pre.lower,ones(size(start.d)),sys.DOFS.active_dof,sys.DOFS.active_dof_pf,limits,@checkpoint,D,S==2);
  assert(out.counts.u==counts.u-1 && out.counts.d==counts.d);
  nested_failure=e011_s2i_fatal(out);
  if strlength(nested_failure)>0,error('E011:ControllerFailure','%s',nested_failure);end
  accepted=out.joint_pass;reason=out.stop;
 end
catch ex
 reason=string(ex.identifier)+": "+string(ex.message);
 allowed=contains(reason,'E011:UBudget')||contains(reason,'E011:DBudget')||contains(reason,'E011:PhaseInnerMiss')||contains(reason,'E011:OriginalOuterCap')||contains(reason,'E011:InnerMiss');
 if ~allowed,fatal=true;end
end
if ~isequaln(pre,frozen),fatal=true;accepted=false;reason="E011:HistoryChanged";end
reference=struct('required',~isempty(ref),'pass',false);
native=[];
try
if ~isempty(current) && ~fatal
 native=current;
 if F==1
  stage="native_final_audit";[~,rd,~,h]=phase_eval(current.d,current.raw,false,false);
  native=make_point(current.u,current.d,current.raw,current.ru,rd,h,current.outer);
  if ~isempty(worst)
   stage="native_worst_audit";[~,wr,~,wh]=phase_eval(worst.d,worst.raw,false,false);
   assert(max(abs(wh(:,:,2:3)-worst.history234(:,:,1:2)),[],'all')<=1e-10);
   worst.native_p2_rd=wr;worst.native_p2_history234=wh(:,:,2:4);
  end
 end
 if ~isempty(ref)
  reference.u_maxerr=max(abs(current.u-ref.candidate.u));reference.d_maxerr=max(abs(current.d-ref.candidate.d));
  reference.history234_scaled_maxerr=max(abs(current.history234-ref.proof.history234)./max(1,abs(ref.proof.history234)),[],'all');
  reference.raw=e011_raw_equivalence(sys.MESH.node(:,1:2),sys.MESH.elem(:,1:4),current.u,current.raw,ref.candidate.u,ref.proof.raw,sys.QUADRATURE);
  reference.outer=current.outer;reference.expected_outer=ref.out.completed_outer;
  reference.pass=accepted && reference.u_maxerr<=1e-10 && reference.d_maxerr<=1e-10 && reference.history234_scaled_maxerr<=1e-10 && reference.raw.pass && reference.outer==reference.expected_outer;
  if ~reference.pass,fatal=true;reason="E011:AnchorMismatch";end
 end
end
catch ex
 fatal=true;accepted=false;reason="dual_audit: "+string(ex.identifier)+": "+string(ex.message);
end
if isempty(current),C=NaN;outer=0;else,C=current.criterion;outer=current.outer;end
if isempty(native),NC=NaN;else,NC=native.criterion;end
if isempty(worst),minf=1;maxalpha=0;else,minf=worst.f_min;maxalpha=worst.alpha_max;end
result=struct('status','miss','bits',bits,'accepted',accepted && ~fatal,'reason',reason,'C_effective',C,'C_native_p2',NC,'outer',outer,'u_calls',counts.u,'phase_calls',counts.d,'history_commits',0,'reference',reference,'trial_effective_f_min',minf,'trial_alpha_max',maxalpha,'fatal',fatal);
if result.accepted,result.status='accepted';end
save(fullfile(folder,'case.mat'),'pre','start','predictor','current','first','native','worst','out','ledger','counts','result','reference','stage','-v7.3');write_json(fullfile(folder,'result.json'),result);
fprintf('[E011_S2I_CASE] %s accepted=%d C=%.10g nativeC=%.10g outer=%d calls=%d/%d reason=%s\n',folder,result.accepted,C,NC,outer,counts.u,counts.d,reason);
assert(counts.u<=250 && counts.d<=250);
if fatal,error('E011:FatalCase','%s',reason);end
 function value=remaining_d()
  value=core_d_cap-counts.d-1;
 end
 function value=read_counts()
  value=counts;
 end
 function [kv,r,raw,h]=eq_counted(varargin)
  assert(counts.u<249,'E011:UBudget','Mechanical cap');counts.u=counts.u+1;
  [kv,r,raw,h]=eq(varargin{:});ok=all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(raw),'all');
  if ~ok,fatal=true;end
  assert(ok,'E011:Nonfinite','Nonfinite mechanical call');
 end
 function [kv,r,aux,h]=pf_counted(varargin)
  [kv,r,aux,h]=phase_eval(varargin{7},varargin{9},true,true);
 end
 function [kv,r,aux,h]=phase_eval(d,raw,effective,record)
  if record,assert(counts.d<core_d_cap,'E011:DBudget','Phase core cap');else,assert(counts.d<250,'E011:DBudget','Phase audit cap');end
  counts.d=counts.d+1;active_mat=mat;if effective && F==1,active_mat=mat0;end
  [kv,r,aux,h]=pf(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,active_mat,sys.CC,d,pre.lower,raw,sys.stress_state.as_number,pre.history);
  ok=all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all');if ~ok,fatal=true;end
  assert(ok,'E011:Nonfinite','Nonfinite phase call');
  if effective && F==1
   if ~all(h(:,:,4)==1,'all'),fatal=true;end
   assert(all(h(:,:,4)==1,'all'),'E011:FrozenF','p0 coefficient not identically1');
  end
  if record
   fm=min(h(:,:,4),[],'all');am=max(h(:,:,2),[],'all');native_f=min(1,(1-(h(:,:,2)-.5)./(h(:,:,2)+.5)).^2);
   row=struct('call',counts.d,'dmin',min(d),'dmax',max(d),'lower_violations',nnz(d<pre.lower-1e-12),'upper_violations',nnz(d>1+1e-12),'alpha_max',am,'effective_f_min',fm,'native_p2_f_pred_min',min(native_f,[],'all'));
   if isempty(ledger),ledger=row;else,ledger(end+1)=row;end %#ok<AGROW>
   if isempty(worst) || am>worst.alpha_max
    worst=struct('call',counts.d,'d',d,'raw',raw,'history234',h(:,:,2:4),'alpha_max',am,'f_min',fm,'native_p2_f_pred',native_f);
   end
  end
 end
 function [K,r,raw]=matrix_eq(u,d)
  [kv,r,raw,~]=eq_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,mat,sys.CC,u,0.0,d,sys.stress_state.as_number,0.0);
  K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
 end
 function [K,r,h]=matrix_pf(d,raw)
  [kv,r,~,h]=phase_eval(d,raw,true,true);K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
 end
 function observe(u,d,raw,outer)
  [~,ru,freshraw]=matrix_eq(u,d);assert(max(abs(raw-freshraw)./max(1,abs(freshraw)),[],'all')<=1e-10);
  [~,rd,h]=matrix_pf(d,freshraw);checkpoint(make_point(u,d,freshraw,ru,rd,h,outer),[],counts);
 end
 function checkpoint(point,trace,calls)
  assert(all(point.d>=pre.lower-1e-12 & point.d<=1+1e-12));
  fixed_u=setdiff((1:numel(point.u))',sys.DOFS.active_dof(:));fixed_d=setdiff((1:numel(point.d))',sys.DOFS.active_dof_pf(:));
  assert(isequal(point.u(fixed_u),predictor.u(fixed_u)) && isequal(point.d(fixed_d),start.d(fixed_d)));
  point.stop_criterion=point.criterion;point.criterion=max((point.u_l2+point.d_feasible_l2)/4e-6,point.u_l2/1e-8);
  current=point;if point.outer==1 && isempty(first),first=point;end
  save(fullfile(folder,sprintf('outer_%02d.mat',point.outer)),'point','trace','calls','-v7.3');
 end
 function point=make_point(u,d,raw,ru,rd,h,outer)
  fu=sys.DOFS.active_dof(:);fd=sys.DOFS.active_dof_pf(:);q=rd(fd);lo=d(fd)<=pre.lower(fd)+1e-10;hi=d(fd)>=1-1e-10;
  q(lo)=min(q(lo),0);q(hi)=max(q(hi),0);q(lo&hi)=0;ur=norm(ru(fu));dr=norm(q);C0=max((ur+dr)/4e-6,ur/1e-8);
  point=struct('u',u,'d',d,'raw',raw,'ru',ru,'rd',rd,'history234',h(:,:,2:4),'outer',outer,'u_l2',ur,'d_feasible_l2',dr,'criterion',C0);
 end
end
function write_json(path,value)
fid=fopen(path,'w');assert(fid>=0);cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value));
end
