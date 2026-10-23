function out=e036_f2_solve(sys,eq,pf,u0,d0,pre,bc,traction,policy,budget,limits,checkpoint)
%E036_F2_SOLVE Isolated c1s4 fixed-f box alternating candidate, ZERO commits.
% Local preparation only. No producer entry/dispatch authority is created here.
% The caller must bind the actual F1 c1s3 admission/source and original load
% predictor, and use the existing E036 persistence/readback path only after
% out.accepted is true. Never insert this F2 endpoint into the primary F1 arm.
required(limits,{'max_outer','u_maxeval','d_maxeval','d_inner_tol','f_tol'});
assert(limits.max_outer>=1 && limits.max_outer<=1500 && fix(limits.max_outer)==limits.max_outer);
assert(limits.u_maxeval>=1 && limits.u_maxeval<=250 && fix(limits.u_maxeval)==limits.u_maxeval);
assert(limits.d_maxeval>=2 && limits.d_maxeval<=250 && fix(limits.d_maxeval)==limits.d_maxeval);
assert(limits.d_inner_tol==4e-8 && limits.f_tol==1e-10 && policy.joint_tol==4e-6 && policy.u_tol==1e-8 && ...
 policy.active_tol==1e-10 && policy.bound_tol==1e-8 && policy.history_tol==1e-10 && ...
 strcmp(string(policy.phase_semantics),'nodal_box_kkt'),'E036F2:Policy','Frozen strict F2 policy required');
assert(pre.state_key.cycle==1 && pre.state_key.substep==3 && pre.version==3 && ...
 pre.state_key.nominal_umax==.12 && pre.state_key.displacement==.08999988 && ...
 strcmp(pre.state_key.trajectory,'S04_E011_FEM_Q4_C120'),'E036F2:Scope','Only the declared actual F1 c1s3 preimage');
assert(pre.admission.accepted && pre.admission.native_residual_checked && pre.admission.checkpoint_readback_verified);
assert(isequal(pre.lower,pre.d) && all(traction==0));
u=u0(:);d=d0(:);old=pre;lower=pre.lower(:);upper=ones(size(d));
fu=sys.DOFS.active_dof(:);fd=sys.DOFS.active_dof_pf(:);
fixed_u=setdiff((1:numel(u))',fu);fixed_d=setdiff((1:numel(d))',fd);
assert(isequal(sort(bc.fixed_u(:)),fixed_u) && isequal(sort(bc.fixed_d(:)),fixed_d));
assert(isequal(u(fixed_u),bc.u(:)) && isequal(d(fixed_d),bc.d(:)) && all(bc.d==1));
assert(all(lower>=0 & lower<=d & d<=1) && all(isfinite(u)) && all(isfinite(d)));
top=find(sys.MESH.node(:,2)==max(sys.MESH.node(:,2)));
assert(all(u(top+sys.MESH.num_node)==.11999988),'E036F2:Load','Exact c1s4 prescribed load required');
assert(isequal(sort(fixed_d),[5;6;(696:944)']),'E036F2:Crack','Original fixed crack DOFs required');
names=fieldnames(policy.expected_material);
for k=1:numel(names)
 name=names{k};assert(abs(sys.MAT_CHAR.(name)-policy.expected_material.(name))<= ...
  1e-12*max(1,abs(policy.expected_material.(name))),'E036F2:Material','Material drift');
end
timer=tic;step_timer=tic;counts=struct('u',0,'d',0,'qp_evaluations',0, ...
 'u_factorizations',0,'d_factorizations',0);trace=[];validations=[];
audit=[];proposal=[];last_attempt=[];last_native_attempt=[];last_native_evaluated=[];
model=[];stop='outer_cap';failure=[];
accepted=false;outer=0;stage='geometry';g=[];
try
 check();g=e036_f2_geometry(sys);check();
 for outer=1:limits.max_outer
  assert(isequaln(pre,old),'E036F2:History','Immutable preimage changed');
  stage='u_before';u_before=e036_f2_displacement_solve(@(x)mechanical(x,d),u,fu,limits.u_maxeval,policy.u_tol);
  counts.u_factorizations=counts.u_factorizations+u_before.factorizations;
  last_attempt=struct('stage',stage,'u_before',u_before);require_u(u_before);u=u_before.u;raw=u_before.raw;
  stage='frozen_operator_validation';
  [model,validation]=e036_f2_validate_frozen(@(x)phase(x,raw),g,d,raw,old,fd,outer==1);
  validation.outer=outer;
  if isempty(validations),validations=validation;else,validations(end+1)=validation;end %#ok<AGROW>
  stage='box_damage';
  d_out=e036_f2_damage_solve(@frozen,d,lower,upper,fd,'constrained',limits.d_maxeval,limits.d_inner_tol);
  counts.d_factorizations=counts.d_factorizations+d_out.factorizations;
  last_attempt=struct('stage',stage,'u_before',u_before,'damage',d_out);
  assert(strcmp(string(d_out.stop),'fresh_tolerance') && strlength(d_out.failure)==0 && ...
   d_out.returned_residual_available && d_out.filtered_l2<=limits.d_inner_tol && ...
   all(d_out.d>=lower & d_out.d<=1),'E036F2:DamageStop','Box subsolve failed; no recovery/retry');
  d=d_out.d;
  stage='u_after';u_after=e036_f2_displacement_solve(@(x)mechanical(x,d),u,fu,limits.u_maxeval,policy.u_tol);
  counts.u_factorizations=counts.u_factorizations+u_after.factorizations;
  last_attempt=struct('stage',stage,'u_before',u_before,'damage',d_out,'u_after',u_after);
  require_u(u_after);u=u_after.u;
  stage='fresh_common_state';
  [audit,candidate_proposal]=e036_native_candidate(sys,@eq_counted,@pf_counted,u,d,1,old,bc, ...
   traction,policy,model.f);
  f_delta=max(abs(audit.f_solve-model.f),[],'all');
  row=struct('outer',outer,'u_l2',audit.u_free_l2,'d_box_l2',audit.d_nodal_box_l2, ...
   'd_raw_l2',audit.d_raw_free_l2,'criterion',audit.criterion,'joint_pass',audit.joint_pass, ...
   'f_delta_max',f_delta,'f_consistent',f_delta<=limits.f_tol,'counts',counts, ...
   'box_stop',d_out.stop,'box_calls',d_out.calls,'u_before_calls',u_before.calls, ...
   'u_after_calls',u_after.calls,'elapsed_seconds',toc(timer));
  if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
  accepted=audit.joint_pass && f_delta<=limits.f_tol;
  if accepted,proposal=candidate_proposal;stop='fresh_joint_and_f';else,proposal=[];end
  fprintf(['E036_F2 outer=%.17g freshRu=%.17g KKT=%.17g fdelta=%.17g ' ...
   'native_u=%.17g native_d=%.17g qp_evaluations=%.17g ' ...
   'u_factorizations=%.17g d_factorizations=%.17g\n'], ...
   outer,audit.u_free_l2,audit.d_nodal_box_l2,f_delta,counts.u,counts.d, ...
   counts.qp_evaluations,counts.u_factorizations,counts.d_factorizations);
  check();checkpoint(progress(row));check();
  if accepted,break;end
 end
catch ex
 accepted=false;proposal=[];stop='failed_without_retry';
 failure=struct('identifier',ex.identifier,'message',ex.message,'stage',stage);
end
out=snapshot();
% Failure persistence belongs to the already-authorized caller. This adapter
% never changes accepted state, never manufactures completion, and never saves
% a checkpoint itself. A failed callback must not conceal the original failure.
 function s=progress(row)
  terminal_status='running';
  if accepted,terminal_status=stop;elseif outer==limits.max_outer,terminal_status='outer_cap';end
  s=struct('schema','e036-f2-c1s4-progress-v1','method','F2-frozen-f-nodal-box-u-d-u', ...
   'stage',stage,'outer',outer,'accepted',accepted,'terminal_status',terminal_status, ...
   'trace_row',row,'counts',counts,'limits',limits,'policy',policy, ...
   'history_commits',0,'no_history_commit',true,'elapsed_seconds',toc(timer));
 end
 function s=snapshot()
  frozen_f=[];if ~isempty(model),frozen_f=model.f;end
  s=struct('schema','e036-f2-c1s4-candidate-v1','method','F2-frozen-f-nodal-box-u-d-u', ...
   'accepted',accepted,'status',stop,'failure',failure,'stage',stage,'outer',outer, ...
   'u',u,'d',d,'audit',audit,'proposal',proposal,'f_frozen',frozen_f, ...
   'trace',trace,'validations',validations,'last_attempt',last_attempt, ...
   'last_native_attempt',last_native_attempt,'last_native_evaluated',last_native_evaluated,'counts',counts, ...
   'limits',limits,'policy',policy,'predecessor_version',old.version, ...
   'predecessor_unchanged',isequaln(pre,old),'history_commits',0, ...
   'elapsed_seconds',toc(timer),'scope','candidate only; no persistence/readback/accepted-state assignment');
 end
 function require_u(q)
  assert(strcmp(string(q.stop),'fresh_tolerance') && strlength(q.failure)==0 && ...
   q.returned_residual_available && q.residual_l2<=policy.u_tol, ...
   'E036F2:UStop','Fresh-return displacement solve failed; no recovery/retry');
 end
 function [K,r,raw]=mechanical(x,dd)
  [v,r,raw,~]=eq_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
   x,0.0,dd,sys.stress_state.as_number,0.0);
  K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,v);r=r-traction;
 end
 function [K,r,h]=phase(x,raw)
  [v,r,~,h]=pf_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
   x,lower,raw,sys.stress_state.as_number,old.history);
  K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,v);
 end
 function [K,r,h]=frozen(x)
  check();counts.qp_evaluations=counts.qp_evaluations+1;
  assert(all(x>=lower & x<=1) && isequal(x(fixed_d),bc.d(:)));
  K=model.H;r=K*x+model.b;h=model.history_diagnostic_only;
  check();
 end
 function varargout=eq_counted(varargin)
  check();counts.u=counts.u+1;
  last_native_attempt=struct('kind','mechanical','u',varargin{7},'d',varargin{9});
  [varargout{1:nargout}]=eq(varargin{:});
  last_native_evaluated=struct('kind','mechanical','u',varargin{7},'d',varargin{9}, ...
   'matrix_vector',varargout{1},'residual',varargout{2},'raw',varargout{3});check();
 end
 function varargout=pf_counted(varargin)
  check();counts.d=counts.d+1;
  last_native_attempt=struct('kind','phase','d',varargin{7},'lower',varargin{8},'raw',varargin{9});
  [varargout{1:nargout}]=pf(varargin{:});
  last_native_evaluated=struct('kind','phase','d',varargin{7},'lower',varargin{8},'raw',varargin{9}, ...
   'matrix_vector',varargout{1},'residual',varargout{2},'history',varargout{4});check();
 end
 function check()
  e036_job_clock(budget,budget.total_timer,budget.total_wall_seconds);
  assert(toc(step_timer)<=budget.step_wall_seconds,'E036F2:Time','F2 step anti-hang limit');
 end
end
function required(x,names)
assert(isstruct(x) && isscalar(x) && all(isfield(x,names)),'E036F2:Schema','Explicit limits required');
end
