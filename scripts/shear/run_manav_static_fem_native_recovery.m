function run_manav_static_fem_native_recovery(griph_root,out_root)
% PROPOSED repair only, not executed: native recovery Newton, fresh certificate.
assert(~isfolder(out_root),'Fresh output required');mkdir(out_root);cd(out_root);
diary(fullfile(out_root,'solver.log'));started=tic;step=0;step_started=tic;
equilibrium_evaluations=0;phase_evaluations=0;recovery_calls=0;
recovery_last_entered=[];recovery_last_completed=[];
addpath(fullfile(griph_root,'Sources'));addpath(genpath(fullfile(griph_root,'Dependencies')));
[MESH,GEOM]=specimen.external.gmsh_import(fullfile(griph_root,'Dependencies','meshes','sens_mesh.m'),'t',1);
nodes=MESH.node;quads=MESH.elem;assert(size(quads,2)==4);
top=find(abs(nodes(:,2)-.5)<1e-10);bot=find(abs(nodes(:,2)+.5)<1e-10);
crack=find(abs(nodes(:,2))<1e-10 & nodes(:,1)>=-.5-1e-10 & nodes(:,1)<=1e-10);
assert(numel(crack)==251);
mat=phase_field.init.material_characteristic(1,'AT1','E',1,'ni',.3,'Gc',.01,...
    'ell',.01,'res_stiff',0,'tol_irrev',.001,'tol_AT1_recovery',.001);
bc=phase_field.fem.bc.set_boundaries('fix_X',bot,'fix_Y',[bot;top],'disp_X',top,'non_hom_pf',crack);
dofs=phase_field.init.dofs(MESH,bc);quad=phase_field.init.quadrature(MESH.dim);
schedule=[.03:.03:.21,.24:.01:.40]';assert(numel(schedule)==24 && abs(schedule(end)-.4)<1e-12);
sp=phase_field.fem.solver.step.params('n_step',24,'ux_final',.4);
sp.ux_increment=diff([0;schedule]);sp.uy_increment=zeros(size(schedule));
alpha=zeros(MESH.num_node,1);alpha(crack)=1;previous=zeros(size(alpha));
u=zeros(dofs.num_dof,1);history=zeros(MESH.num_elem,quad.num_gauss_pts,1);
sys=phase_field.System(mat,GEOM,quad,dofs,bc,sp,MESH,phase_field.StressState.PlaneStrain,alpha,'AT1');
eq=@phase_field.mex.fem.assembly.equilibrium.AMOR;
pf=@phase_field.mex.fem.assembly.pf.AT1_PENALTY;
rhs=zeros(size(u));driver=zeros(MESH.num_elem,quad.num_gauss_pts);
fid=fopen(fullfile(out_root,'newton_trace.csv'),'w');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'step,stagger,field,event,iteration,trial,residual,trial_residual,lambda,seconds\n');
cf=fopen(fullfile(out_root,'coupling.csv'),'w');assert(cf>=0);closec=onCleanup(@()fclose(cf));
fprintf(cf,'step,U,stagger,res_u,res_pf,alpha_min,alpha_max,max_healing,seconds\n');
tf=fopen(fullfile(out_root,'trajectory.csv'),'w');assert(tf>=0);closet=onCleanup(@()fclose(tf));
fprintf(tf,'step,U,Rx_top,Rx_bottom,E_el,E_d,res_u,res_pf,alpha_min,alpha_max,max_healing,stag_iters,seconds\n');
stage='recovery';stag=0;kind='phase';U=0;res_u=NaN;res_pf=NaN;certificate_valid=false;
write_guard(600);
try
    [~,~,alpha,~,~,bad_recovery]=phase_field.fem.solver.newton_raphson( ...
        @counted_native_phase,sys,alpha,previous,driver,history,dofs.active_dof_pf,...
        sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,...
        'max_iter',500,'res_tol',1e-6,'line_search',false,...
        'regularize_pf_only',true,'pf_czm_damping',false,'verbose',false);
    assert(~bad_recovery && all(isfinite(alpha)),'Native recovery Newton failed');
    pc=phase_assembly(alpha);res_pf=norm(pc.R(dofs.active_dof_pf));
    assert(res_pf<=1e-6 && all(alpha(crack)==1));
    ec=equilibrium_assembly(u);tmp=sys.STIFFNESS_MATRIX;tmp.KK=ec.K;sys.STIFFNESS_MATRIX=tmp;
    alpha_initial=alpha;previous=alpha;timing='initial_unloaded_after_recovery_before_loading';
    p_field=alpha;p_field_old=previous;displ=u;
    save(fullfile(out_root,'mesh.mat'),'nodes','quads','schedule','top','bot','crack','alpha_initial','-v7');
    save(fullfile(out_root,'state_000.mat'),'p_field','p_field_old','displ','U','step','timing','res_pf','-v7');
    finish_guard();
    for step=1:24
        step_started=tic;U=schedule(step);res_u=NaN;res_pf=NaN;certificate_valid=false;
        write_guard(1800);stage='load_update';
        [u,~,rhs]=phase_field.fem.solver.step.pre_iter_update(step,sys,u,sp);
        accepted=false;
        for stag=1:1000
            res_u=NaN;res_pf=NaN;certificate_valid=false;check();stage='mechanics';kind='mechanics';
            [u,ec,er]=solve_field(@equilibrium_assembly,u,dofs.active_dof);
            assert(er.ok,['Mechanics failed: ',er.reason,' ',er.message]);driver=ec.driver;
            stage='phase';kind='phase';
            [alpha,pc,pr]=solve_field(@phase_assembly,alpha,dofs.active_dof_pf);
            assert(pr.ok,['Phase failed: ',pr.reason,' ',pr.message]);
            % Both residuals refer to exactly this returned (u,alpha), history fixed.
            stage='same_state_certificate';ec=equilibrium_assembly(u);driver=ec.driver;pc=phase_assembly(alpha);
            res_u=norm(ec.R(dofs.active_dof));res_pf=norm(pc.R(dofs.active_dof_pf));
            certificate_valid=true;tmp=sys.STIFFNESS_MATRIX;tmp.KK=ec.K;sys.STIFFNESS_MATRIX=tmp;
            fprintf(cf,'%d,%.17g,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f\n',...
                step,U,stag,res_u,res_pf,min(alpha),max(alpha),max(previous-alpha),toc(started));
            fprintf('COUPLED step=%d U=%.4f stag=%d Ru=%.9g Rpf=%.9g alpha=[%.9g,%.9g]\n',step,U,stag,res_u,res_pf,min(alpha),max(alpha));
            if res_u+res_pf<=1e-4,accepted=true;break;end
        end
        assert(accepted,'Staggered iteration limit');stage='validity';
        assert(all(alpha(crack)==1),'Initial crack BC changed');
        assert(min(alpha)>=-.005 && max(alpha)<=1.005 && max(previous-alpha)<=.005,'Damage admissibility failed');
        p_field=alpha;p_field_old=previous;displ=u;forces=ec.force;pf_force=pc.R;
        E_el=ec.energy;E_d=phase_field.mex.fem.processing.fracture_energy(MESH,GEOM.t,quad,mat,sys.CC,alpha,8/3,1);
        assert(isfinite(E_el+E_d));Rx_top=sum(forces(top));Rx_bottom=sum(forces(bot));
        timing='post_solve_pre_history_update';history_vars_old=history;
        save(fullfile(out_root,sprintf('state_%03d.mat',step)),'p_field','p_field_old','displ','U','step','timing',...
            'driver','forces','pf_force','history_vars_old','res_u','res_pf','E_el','E_d','equilibrium_evaluations','phase_evaluations','-v7');
        fprintf(tf,'%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%.6f\n',...
            step,U,Rx_top,Rx_bottom,E_el,E_d,res_u,res_pf,min(alpha),max(alpha),max(previous-alpha),stag,toc(started));
        fprintf('ACCEPTED step=%d U=%.4f seconds=%.1f\n',step,U,toc(started));
        stage='post_accepted_history_update';certificate_valid=false;res_u=NaN;res_pf=NaN;
        previous=alpha;
        [~,~,~,history]=pf(MESH,dofs,GEOM.t,quad,mat,sys.CC,alpha,previous,driver,sys.stress_state.as_number,history);
        check();finish_guard();
    end
    f=fopen(fullfile(out_root,'COMPLETED.txt'),'w');assert(f>=0);fprintf(f,'24 accepted loaded states through U=.4\n');fclose(f);
catch failure
    rejection_reason=failure.message;failure_stage=stage;timing='unaccepted_current_returned_pair';
    if step==0,timing='unaccepted_outer_call_field; native_preupdate_points_saved_separately';end
    p_field=alpha;p_field_old=previous;displ=u;elapsed_seconds=toc(started);step_seconds=toc(step_started);
    save(fullfile(out_root,sprintf('failed_state_%03d.mat',step)),'p_field','p_field_old','displ','U','step','stag',...
        'timing','driver','res_u','res_pf','certificate_valid','recovery_last_entered','recovery_last_completed','failure_stage','rejection_reason','elapsed_seconds','step_seconds','-v7');
    rethrow(failure);
end
diary off;
    function check()
        assert(toc(started)<10800,'MANAV:TotalBudget','Three-hour FEM limit');
        limit=1800;if step==0,limit=600;end
        assert(toc(step_started)<limit,'MANAV:StepBudget','Per-state limit');
    end
    function c=equilibrium_assembly(value)
        check();equilibrium_evaluations=equilibrium_evaluations+1;
        [kv,f,d,~]=eq(MESH,dofs,GEOM.t,quad,mat,sys.CC,value,0,alpha,sys.stress_state.as_number,0);
        K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
        c=struct('u',value,'K',K,'R',f-rhs,'force',f,'driver',d,'energy',.5*(value'*K*value));check();
    end
    function varargout=counted_native_phase(varargin)
        recovery_calls=recovery_calls+1;
        recovery_last_entered=struct('call',recovery_calls,'alpha',varargin{7},...
            'timing','native_assembly_input_before_Newton_update','assembled',false);
        save(fullfile(out_root,'recovery_last_points.mat'),'recovery_last_entered','recovery_last_completed','-v7');
        check();phase_evaluations=phase_evaluations+1;
        [varargout{1:nargout}]=pf(varargin{:});
        recovery_last_completed=struct('call',recovery_calls,'alpha',varargin{7},'Rpf',varargout{2},...
            'timing','native_assembly_input_before_Newton_update','assembled',true);
        fprintf(fid,'%d,0,native_recovery,preupdate_assembly,%d,-1,%.17g,NaN,NaN,%.6f\n',...
            step,recovery_calls,norm(varargout{2}(dofs.active_dof_pf)),toc(started));
        save(fullfile(out_root,'recovery_last_points.mat'),'recovery_last_entered','recovery_last_completed','-v7');
        check();
    end
    function c=phase_assembly(value)
        check();phase_evaluations=phase_evaluations+1;
        [kv,r,~,~]=pf(MESH,dofs,GEOM.t,quad,mat,sys.CC,value,previous,driver,sys.stress_state.as_number,history);
        K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
        c=struct('u',value,'K',K,'R',r,'force',r,'driver',[],'energy',0);check();
    end
    function [value,c,report]=solve_field(assembler,value,active)
        opts=struct('max_iter',500,'max_backtracks',12,'beta',.5,'c1',1e-4,'res_tol',1e-6,'check',@check,'observe',@observe);
        [value,c,report]=bounded_mechanical_newton(assembler,@(K,b)cholmod2(K,b),value,active,opts);
    end
    function observe(e)
        active=dofs.active_dof_pf;if strcmp(kind,'mechanics'),active=dofs.active_dof;end
        tr=NaN;if ~isempty(e.trial_cache),tr=norm(e.trial_cache.R(active));end
        fprintf(fid,'%d,%d,%s,%s,%d,%d,%.17g,%.17g,%.17g,%.6f\n',...
            step,stag,kind,e.kind,e.iteration,e.trial,e.pre_residual,tr,e.lambda,toc(started));
        check();
    end
    function write_guard(seconds_limit)
        deadline=datetime('now','TimeZone','UTC')+seconds(seconds_limit);deadline.Format="yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";
        g=struct('step',step,'deadline_utc',char(deadline),'limit_seconds',seconds_limit);
        target=fullfile(out_root,sprintf('step_guard_%03d.json',step));f=fopen([target,'.tmp'],'w');assert(f>=0);
        fprintf(f,'%s',jsonencode(g));fclose(f);movefile([target,'.tmp'],target);
    end
    function finish_guard()
        f=fopen(fullfile(out_root,sprintf('step_done_%03d.txt',step)),'w');assert(f>=0);fclose(f);
    end
end
