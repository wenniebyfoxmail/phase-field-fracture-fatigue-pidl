function [summary,predictor,Kcache]=e011_s2x_case(mode,pre,start,sys,eq,pf,par,folder,ref,cache_check,predictor_check)
%E011_S2X_CASE One c1s2 trial solve; never commits or propagates history.
assert(~isfolder(folder));mkdir(folder);frozen=pre;
counts=struct('u',0,'d',0);trial_f_min=1;trial_alpha_max=0;phase_calls_with_f_below_one=0;
if strcmp(mode,'original'),caps=struct('u',251002,'d',250003);else,caps=struct('u',250,'d',250);end
candidate=[];proof=[];out=[];stage="cache";
try
 [Kcache,~,~]=matrix_eq(start.u,start.d);
 if ~isempty(cache_check),assert(isequal(Kcache,cache_check),'E011:CacheMismatch','Common cache differs');end
 sys.STIFFNESS_MATRIX.KK=Kcache;
 [predicted,res_displ,D_RHS]=phase_field.fem.solver.step.pre_iter_update(2,sys,start.u,par.step);
 assert(all(D_RHS==0));predictor=struct('u',predicted,'r',res_displ,'d',start.d);
 if ~isempty(predictor_check),assert(isequaln(predictor,predictor_check),'E011:PredictorMismatch','Common predictor differs');end
 stage="solve";
 if strcmp(mode,'original')
  out=e011_original_step(sys,@eq_counted,@pf_counted,predicted,start.d,pre.lower,pre.history,res_displ,D_RHS,par,folder,@read_counts,2);
  candidate=struct('u',out.u,'d',out.d,'raw',out.raw);accepted=out.native_accepted;
 else
  limits=struct('admission_u',0,'admission_d',0,'max_u',248,'max_d',247,'max_outer',20,'u_tol',1e-8,'d_tol',4e-6,'joint_tol',4e-6);
  out=e011_coupled_solve(@matrix_eq,@matrix_pf,predicted,start.d,pre.lower,ones(size(pre.d)),sys.DOFS.active_dof,sys.DOFS.active_dof_pf,limits,@checkpoint);
  assert(out.counts.u==counts.u-1 && out.counts.d==counts.d);
  assert(~isempty(out.final),'E011:NoFinal','No completed endpoint');
  candidate=struct('u',out.final.u,'d',out.final.d,'raw',out.final.raw);accepted=out.joint_pass;
 end
 stage="fresh_audit";
 [~,ru,raw]=matrix_eq(candidate.u,candidate.d);[~,rd,h]=matrix_pf(candidate.d,raw);
 assert(max(abs(raw-candidate.raw)./max(1,abs(raw)),[],'all')<=1e-10,'E011:StaleRaw','Raw stale');
 fu=sys.DOFS.active_dof(:);fd=sys.DOFS.active_dof_pf(:);q=rd(fd);
 lo=candidate.d(fd)<=pre.lower(fd)+1e-10;hi=candidate.d(fd)>=1-1e-10;
 q(lo)=min(q(lo),0);q(hi)=max(q(hi),0);q(lo&hi)=0;
 ur=norm(ru(fu));dr=norm(q);C=max((ur+dr)/4e-6,ur/1e-8);
 fixed_u=setdiff((1:numel(predicted))',fu);fixed_d=setdiff((1:numel(pre.d))',fd);
 bounds=all(candidate.d>=pre.lower-1e-12 & candidate.d<=1+1e-12);
 fixed_bc=isequal(candidate.u(fixed_u),predicted(fixed_u)) && isequal(candidate.d(fixed_d),start.d(fixed_d));
 assert(bounds && fixed_bc && all(isfinite([ur dr C])) && isequaln(pre,frozen));
 proof=struct('u_l2',ur,'d_feasible_l2',dr,'criterion',C,'joint_pass',C<=1,'ru',ru,'rd',rd,'raw',raw,'history234',h(:,:,2:4),'bounds',bounds,'fixed_bc',fixed_bc);
 reference=struct('required',~isempty(ref),'pass',true);
 if ~isempty(ref)
  reference.u_maxerr=max(abs(candidate.u-ref.candidate.u));reference.d_maxerr=max(abs(candidate.d-ref.candidate.d));
  reference.history234_scaled_maxerr=max(abs(proof.history234-ref.proof.history234)./max(1,abs(ref.proof.history234)),[],'all');
  reference.raw=e011_raw_equivalence(sys.MESH.node(:,1:2),sys.MESH.elem(:,1:4),candidate.u,raw,ref.candidate.u,ref.proof.raw,sys.QUADRATURE);
  reference.outer=out.completed_outer;reference.expected_outer=ref.out.completed_outer;
  reference.pass=reference.u_maxerr<=1e-10 && reference.d_maxerr<=1e-10 && reference.history234_scaled_maxerr<=1e-10 && reference.raw.pass && reference.outer==reference.expected_outer;
 end
 summary=struct('status','completed','mode',mode,'pre_version',pre.version,'C',C,'joint_pass',C<=1,'native_accepted',accepted,'outer',out.completed_outer,'u_calls',counts.u,'d_calls',counts.d,'reference_pass',reference.pass,'history_commits',0,'trial_f_min',trial_f_min,'trial_alpha_max',trial_alpha_max,'phase_calls_with_f_below_one',phase_calls_with_f_below_one,'final_f_min',min(h(:,:,4),[],'all'),'final_alpha_max',max(h(:,:,2),[],'all'));
 save(fullfile(folder,'completed.mat'),'pre','start','predictor','candidate','proof','out','counts','summary','reference','-v7.3');
 assert(accepted && (~strcmp(mode,'repaired') || C<=1),'E011:NativeMiss','Native acceptance miss; stop without retry');
 assert(reference.pass,'E011:AnchorMismatch','Anchor does not reproduce saved endpoint');
 write_json(fullfile(folder,'result.json'),summary);
 fprintf('[E011_S2X_CASE] %s C=%.12g outer=%d calls=%d/%d fmin=%.9g\n',folder,C,out.completed_outer,counts.u,counts.d,trial_f_min);
catch ex
 failure=struct('stage',stage,'identifier',ex.identifier,'message',ex.message,'counts',counts,'history_commits',0,'trial_f_min',trial_f_min,'trial_alpha_max',trial_alpha_max);
 save(fullfile(folder,'failure.mat'),'pre','start','candidate','proof','out','failure','-v7.3');write_json(fullfile(folder,'failure.json'),failure);rethrow(ex);
end
 function value=read_counts()
  value=counts;
 end
 function [kv,r,raw,h]=eq_counted(varargin)
  assert(counts.u<caps.u,'E011:UBudget','Native u cap');counts.u=counts.u+1;
  [kv,r,raw,h]=eq(varargin{:});assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(raw),'all'));
 end
 function [kv,r,aux,h]=pf_counted(varargin)
  assert(counts.d<caps.d,'E011:DBudget','Native phase cap');counts.d=counts.d+1;
  [kv,r,aux,h]=pf(varargin{:});assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'));
  fmin=min(h(:,:,4),[],'all');trial_f_min=min(trial_f_min,fmin);trial_alpha_max=max(trial_alpha_max,max(h(:,:,2),[],'all'));
  phase_calls_with_f_below_one=phase_calls_with_f_below_one+(fmin<1);
 end
 function [K,r,raw]=matrix_eq(u,d)
  [kv,r,raw,~]=eq_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,u,0.0,d,sys.stress_state.as_number,0.0);
  K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
 end
 function [K,r,h]=matrix_pf(d,raw)
  [kv,r,~,h]=pf_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d,pre.lower,raw,sys.stress_state.as_number,pre.history);
  K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
 end
 function checkpoint(state,trace,calls)
  save(fullfile(folder,'last_completed_trial.mat'),'state','trace','calls','-v7.3');
 end
end
function write_json(path,value)
fid=fopen(path,'w');assert(fid>=0);cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value));
end
