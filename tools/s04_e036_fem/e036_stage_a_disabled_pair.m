function report=e036_stage_a_disabled_pair(sys,par,common,binding,overlay_path,overlay_sha256,budget,out_dir)
%E036_STAGE_A_DISABLED_PAIR Exactly absent/false c1s1 controls from stored U0.
% Uses the literal predictor + staggered + commit body of the reviewed overlay.
% Excludes trajectory loops/postprocessing; saves the six native field/key
% checkpoint variables locally. This is not a full native resume checkpoint.
% No fresh acceptance callback is run inside either disabled numerical path.
pair_clock=tic;pair_cap=budget.total_wall_seconds;e036_stage_a_clock(budget,pair_clock,pair_cap);
assert(isfield(budget,'arm_wall_seconds') && isnumeric(budget.arm_wall_seconds) && ...
 isscalar(budget.arm_wall_seconds) && isfinite(budget.arm_wall_seconds) && budget.arm_wall_seconds>0, ...
 'E036A:ArmWatchdog','Explicit per-arm timeout is required');
assert(isfield(budget,'arm_deadline_dir') && ...
 ~isfolder(budget.arm_deadline_dir) && ~isfile(budget.arm_deadline_dir) && ...
 isfolder(fileparts(budget.arm_deadline_dir)) && ...
 ~isempty(regexp(char(budget.watchdog_id),'^[a-z0-9_]+$','once')), ...
 'E036A:ArmWatchdog','Require a fresh logs/<watchdog_id>_arms directory path');
[~,deadline_leaf]=fileparts(budget.arm_deadline_dir);
assert(strcmp(deadline_leaf,[char(budget.watchdog_id) '_arms']), ...
 'E036A:ArmWatchdog','Per-arm deadline directory does not match watchdog ID');
assert(binding.u0_admitted && binding.u0_audit.joint_pass && binding.native_solves==0 && common.version==0, ...
 'E036A:U0Admission','Use the checked existing U0 from e036_stage_a_context');
assert(strcmp(e036_sha256_file(overlay_path),overlay_sha256),'E036A:Overlay','Overlay hash mismatch');
assert(nargout('phase_field.fem.solver.newton_raphson')==7, ...
 'E036A:NativeSignature','Pinned original body requires the producer native seven-output Newton');
body=fileread(overlay_path);body=strrep(body,sprintf('\r\n'),sprintf('\n'));
first='        [displ, res_displ, D_RHS_tract] = phase_field.fem.solver.step.pre_iter_update(i_step, sys, displ, SOL_STEP_PAR);';
last='        % ============================STEP POST-PROCESSING=============================';
a=strfind(body,first);b=strfind(body,last);
assert(numel(a)==1 && numel(b)==1 && a<b,'E036A:SourceSlice','Original native-body anchors changed');
body=body(a:b-1);
assert(contains(body,'e036_enabled = exist(') && contains(body,'if e036_enabled') && ...
 contains(body,'history_vars_old...') && contains(body,'n_iter_displ]'), ...
 'E036A:SourceSlice','Expected audited overlay body is missing');
assert(~isfolder(out_dir) && ~isfile(out_dir) && isfolder(fileparts(out_dir)), ...
 'E036A:Output','Require fresh output directory with existing parent');
mkdir(out_dir);
source_receipt=struct('overlay_path',overlay_path,'overlay_sha256',overlay_sha256, ...
 'first_anchor',first,'last_exclusive_anchor',last,'body_modifications','none', ...
 'native_signature_outputs',7,'steps_per_arm',1,'cycle',1,'substep',1, ...
 'common_sha256',binding.common_sha256,'budget',budget,'binding',binding);
save(fullfile(out_dir,'source_and_input.mat'),'source_receipt','common','par','-v7.3');
fid=fopen(fullfile(out_dir,'native_single_step_body.m'),'w');assert(fid>=0);
cleanup=onCleanup(@()fclose(fid));fwrite(fid,body,'char');clear cleanup;
assert(strcmp(e036_sha256_file(binding.options.common_file),binding.common_sha256), ...
 'E036A:InputDrift','Stored U0 changed before control launch');
stored=load(binding.options.common_file,'common','initial_KK');
assert(isequaln(common,stored.common),'E036A:Preimage','Control input differs from the admitted stored U0');
initial_KK=stored.initial_KK;clear stored;
assert(par.solver.max_iter_displ==binding.cfg.max_iter_displacement && ...
 par.solver.max_iter_pf==250 && par.solver.tol_displ==1e-6 && ...
 par.solver.tol_p_field==4e-4 && par.stag.tol==4e-4, ...
 'E036A:Solver','Native settings changed after context binding');
assert(java.io.File(char(budget.arm_deadline_dir)).mkdir(), ...
 'E036A:ArmWatchdog','Could not exclusively create per-arm deadline directory');
try
 absent=one_arm('absent',sys,par,common,initial_KK,body,budget,fullfile(out_dir,'absent'));
 e036_stage_a_clock(budget,pair_clock,pair_cap);
 disabled=one_arm('false',sys,par,common,initial_KK,body,budget,fullfile(out_dir,'false'));
 fields={'displ','p_field','p_field_old','history_vars_old','SOL_CYCL_VAR','i_step_completed', ...
  'SOL_STAG_VAR','res_displ','res_pf','strain_en_undgr','history_vars_new','i_stag','KK'};
 for k=1:numel(fields)
  name=fields{k};assert(isequaln(absent.(name),disabled.(name)), ...
   'E036A:DisabledIdentity','Absent/false differ in %s',name);
 end
 assert(strcmp(e036_sha256_file(overlay_path),overlay_sha256),'E036A:OverlayDrift','Overlay changed during controls');
 report=struct('status','exact_disabled_identity','cycle',1,'substep',1,'native_solves',2, ...
  'predictor_solves',2,'recovery_solves',0,'per_arm_seconds',budget.arm_wall_seconds, ...
  'comparison_fields',{fields},'absent_checkpoint_sha256',absent.checkpoint_sha256, ...
  'false_checkpoint_sha256',disabled.checkpoint_sha256,'elapsed_seconds',toc(pair_clock), ...
  'scope','original native acceptance; disabled compatibility only, not common final-state acceptance');
 e036_stage_a_clock(budget,pair_clock,pair_cap);
 save(fullfile(out_dir,'disabled_identity.mat'),'report','-v7.3');
 e036_stage_a_clock(budget,pair_clock,pair_cap);
catch ex
 failure=struct('identifier',ex.identifier,'message',ex.message, ...
  'elapsed_seconds',toc(pair_clock),'retry_permitted',false);
 try
  save(fullfile(out_dir,'failure.mat'),'failure','-v7.3');
 catch diagnostic_ex
  try
   warning('E036A:DiagnosticSave','Could not save pair failure diagnostics: %s; original error retained: %s', ...
    diagnostic_ex.message,ex.identifier);
  catch
   % A caller may promote warnings to errors; preserve the original failure.
  end
 end
 rethrow(ex);
end
end

function output=one_arm(mode,sys,par,common,initial_KK,body,budget,out_dir)
% Deliberately no nested functions: original script variables stay local here.
started=datetime('now','TimeZone','UTC');clock=tic;arm_cap=budget.arm_wall_seconds;
e036_stage_a_clock(budget,clock,arm_cap);assert(~isfolder(out_dir));mkdir(out_dir);
arm=struct('schema','e036-stage-a-arm-v1','watchdog_id',char(budget.watchdog_id), ...
 'matlab_pid',feature('getpid'),'mode',mode,'arm_started_utc',utc_text(started), ...
 'deadline_utc',utc_text(started+seconds(arm_cap)),'wall_seconds',arm_cap, ...
 'authority_id',budget.authority_id,'authority_sha256',budget.authority_sha256);
write_arm_event(budget.arm_deadline_dir,[mode '_started.json'],arm);
sys.STIFFNESS_MATRIX.KK=initial_KK;
displ=common.u;p_field=common.d;p_field_old=common.lower;history_vars_old=common.history;
SOL_PAR=par.solver;SOL_STAG_PAR=par.stag;SOL_STEP_PAR=par.step;
assert(SOL_STAG_PAR.max_iter==1500 && SOL_STEP_PAR.n_step==5 && ~SOL_STEP_PAR.line_search);
SOL_STAG_VAR=phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
SOL_CYCL_VAR=struct('n_cycle',1);i_step=1;example_name=char(out_dir);
CRACK_PAR=phase_field.fem.crack.params(sys.MAT_CHAR,'AT1','crack_thres',.95);
native_q4_capture=struct('enabled',false);regularize_pf_newton=true;damage_upper_bound=1;
if strcmp(mode,'false'),e036_final_acceptance=struct('enabled',false); %#ok<NASGU>
else,assert(strcmp(mode,'absent'));end
eq=str2func('phase_field.mex.fem.assembly.equilibrium.AMOR');
pf=str2func('phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE');
assembly_equilibrium_fh=@(varargin)e036_stage_a_native_call(eq,budget,clock,arm_cap,varargin{:}); %#ok<NASGU>
assembly_pf_fh=@(varargin)e036_stage_a_native_call(pf,budget,clock,arm_cap,varargin{:}); %#ok<NASGU>
save(fullfile(out_dir,'predecessor.mat'),'common','mode','initial_KK','-v7.3');
try
 e036_stage_a_clock(budget,clock,arm_cap);
 eval(body); % Exact saved/reviewed original overlay numerical segment only.
 e036_stage_a_clock(budget,clock,arm_cap);
 assert(~e036_enabled && stag_converged && i_step==1 && SOL_CYCL_VAR.n_cycle==1, ...
  'E036A:Control','Disabled single-step native path did not complete');
 assert(all(isfinite(displ)) && all(isfinite(p_field)) && ...
  all(isfinite(history_vars_old(:,:,2:4)),'all'),'E036A:Nonfinite','Native control returned invalid fields');
 assert(all(D_RHS_tract==0),'E036A:Traction','Unexpected external traction');
 assert(isequal(common.d,common.lower) && common.version==0,'E036A:Preimage','Input state changed');
 i_step_completed=1;checkpoint=fullfile(out_dir,'step_checkpoint.mat');
 save(checkpoint,'displ','p_field','p_field_old','history_vars_old','SOL_CYCL_VAR','i_step_completed','-v7.3');
 saved=load(checkpoint);
 assert(isequaln(saved.displ,displ) && isequaln(saved.p_field,p_field) && ...
  isequaln(saved.p_field_old,p_field_old) && isequaln(saved.history_vars_old,history_vars_old) && ...
  isequal(saved.SOL_CYCL_VAR,SOL_CYCL_VAR) && saved.i_step_completed==1, ...
  'E036A:Readback','Native control checkpoint readback differs');
 output=saved;output.SOL_STAG_VAR=SOL_STAG_VAR;output.res_displ=res_displ;output.res_pf=res_pf;
 output.strain_en_undgr=strain_en_undgr;output.history_vars_new=history_vars_new;
 output.i_stag=i_stag;output.KK=sys.STIFFNESS_MATRIX.KK;
 output.checkpoint_sha256=e036_sha256_file(checkpoint);output.elapsed_seconds=toc(clock);
 output.f_last_inner_return=history_vars_new(:,:,4);
 output.scope='six native field/key variables; no full native resume metadata';
 e036_stage_a_clock(budget,clock,arm_cap);
 save(fullfile(out_dir,'native_result.mat'),'output','mode','-v7.3');
 e036_stage_a_clock(budget,clock,arm_cap);
 finished=datetime('now','TimeZone','UTC');
 assert(finished<started+seconds(arm_cap),'E036A:WallLimit','Arm finished after its external deadline');
 arm.arm_finished_utc=utc_text(finished);
 write_arm_event(budget.arm_deadline_dir,[mode '_finished.json'],arm);
catch ex
 failure=struct('identifier',ex.identifier,'message',ex.message,'mode',mode, ...
  'elapsed_seconds',toc(clock),'retry_permitted',false);
 try
  save(fullfile(out_dir,'failure.mat'),'failure','common','displ','p_field','p_field_old','history_vars_old','SOL_STAG_VAR','-v7.3');
 catch diagnostic_ex
  try
   warning('E036A:DiagnosticSave','Could not save %s arm failure diagnostics: %s; original error retained: %s', ...
    mode,diagnostic_ex.message,ex.identifier);
  catch
   % Diagnostic warning policy must not replace the original native failure.
  end
 end
 rethrow(ex);
end
end

function value=utc_text(value)
value.Format='yyyy-MM-dd''T''HH:mm:ss.SSS''Z''';value=char(value);
end
function write_arm_event(folder,name,event)
destination=fullfile(folder,name);temporary=[destination '.tmp'];
assert(~isfile(destination) && ~isfile(temporary),'E036A:ArmWatchdog','Never overwrite an arm deadline record');
[fid,message]=fopen(temporary,'w','n','UTF-8');assert(fid>=0,'E036A:ArmWatchdog','%s',message);
closer=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(event));[message,number]=ferror(fid);
assert(number==0,'E036A:ArmWatchdog','%s',message);clear closer;
[ok,message]=movefile(temporary,destination);assert(ok,'E036A:ArmWatchdog','%s',message);
end
