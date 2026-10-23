function run_manav_static_fem_progress(griph_root,out_root,prefix_root)
% NEW constrained model: native AT1 energy with explicit nodal box0<=alpha<=1.
assert(~isfolder(out_root),'Fresh output required');mkdir(out_root);cd(out_root);
diary(fullfile(out_root,'solver.log'));started=tic;step=0;step_started=tic;
elapsed_offset=0;equilibrium_evaluations=0;phase_evaluations=0;native_phase_calls=0;
native_last_entered=[];native_last_completed=[];box_last_state=[];phase_direction_last=[];
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
energy_geom=box_q4_geometry(nodes,quads,quad,GEOM.t);
schedule=[.03:.03:.21,.24:.01:.40]';assert(numel(schedule)==24 && abs(schedule(end)-.4)<1e-12);
sp=phase_field.fem.solver.step.params('n_step',24,'ux_final',.4);
sp.ux_increment=diff([0;schedule]);sp.uy_increment=zeros(size(schedule));
alpha=zeros(MESH.num_node,1);alpha(crack)=1;previous=zeros(size(alpha));
u=zeros(dofs.num_dof,1);history=zeros(MESH.num_elem,quad.num_gauss_pts,1);
sys=phase_field.System(mat,GEOM,quad,dofs,bc,sp,MESH,phase_field.StressState.PlaneStrain,alpha,'AT1');
eq=@phase_field.mex.fem.assembly.equilibrium.AMOR;
pf=@phase_field.mex.fem.assembly.pf.AT1_PENALTY;
rhs=zeros(size(u));driver=zeros(MESH.num_elem,quad.num_gauss_pts);
% Prefix is immutable verified R022 output, copied without numerical changes.
resume_mesh=load(fullfile(prefix_root,'mesh.mat'));
assert(isequal(nodes,resume_mesh.nodes) && isequal(quads,resume_mesh.quads) && isequal(schedule,resume_mesh.schedule),'MANAV:ResumeMesh','Prefix mesh/schedule changed');
for prefix_step=0:16
    copyfile(fullfile(prefix_root,sprintf('state_%03d.mat',prefix_step)),out_root);
end
for name={'mesh.mat','constraint_contract.mat','trajectory.csv','coupling.csv','option_scope_integration.json'}
    copyfile(fullfile(prefix_root,name{1}),out_root);
end
prefix_lines=splitlines(strtrim(fileread(fullfile(prefix_root,'trajectory.csv'))));
last_columns=strsplit(char(prefix_lines(end)),',');assert(str2double(last_columns{1})==16 && str2double(last_columns{2})==.32);
elapsed_offset=str2double(last_columns{13});
fid=fopen(fullfile(out_root,'newton_trace.csv'),'w');assert(fid>=0);closer=onCleanup(@()fclose(fid));
fprintf(fid,'step,stagger,field,event,iteration,trial,residual,trial_residual,lambda,seconds\n');
cf=fopen(fullfile(out_root,'coupling.csv'),'a');assert(cf>=0);closec=onCleanup(@()fclose(cf));
tf=fopen(fullfile(out_root,'trajectory.csv'),'a');assert(tf>=0);closet=onCleanup(@()fclose(tf));
stage='recovery';stag=0;kind='phase';U=0;res_u=NaN;res_pf=NaN;certificate_valid=false;native_return_pf_residual=NaN;
native_return_residual_timing='native PF returned point, fixed input driver and history';
write_guard();
try
    phase_opts=struct('res_tol',1e-6,'check',@check,'curvature',@phase_curvature,'ray_step',@phase_ray_step,'observe_direction',@record_phase_direction,'clear_direction',@clear_phase_direction);
    base=load(fullfile(prefix_root,'state_016.mat'));
    assert(base.step==16 && base.U==.32 && strcmp(base.timing,'post_solve_pre_history_update'));
    alpha=base.p_field;u=base.displ;previous=alpha;driver=base.driver;history=base.history_vars_old;
    assert(all(alpha>=0 & alpha<=1) && all(alpha(crack)==1));
    % Replay exactly the original post-accepted-state native history update.
    [~,~,~,history]=pf(MESH,dofs,GEOM.t,quad,mat,sys.CC,alpha,previous,driver,sys.stress_state.as_number,history);
    ec=equilibrium_assembly(u);assert(isequal(ec.driver,base.driver),'MANAV:ResumeDriver','Native restored driver differs');
    tmp=sys.STIFFNESS_MATRIX;tmp.KK=ec.K;sys.STIFFNESS_MATRIX=tmp;
    fprintf('CONTINUATION source=R022 accepted_prefix=16 next_U=.33 iteration_budget=none\n');
    f=fopen(fullfile(out_root,'resume_provenance.json'),'w');assert(f>=0);
    fprintf(f,'%s',jsonencode(struct('source','S04-E035-R022','accepted_prefix',16,'prefix_U',.32,'native_history_update_replayed',true,'native_driver_exact_match',true,'iteration_budget',[],'trajectory_seconds','prefix accepted wall plus continuation wall; prior failed work excluded and separately recorded')));fclose(f);
    for step=17:24
        step_started=tic;U=schedule(step);res_u=NaN;res_pf=NaN;certificate_valid=false;
        native_return_pf_residual=NaN;
        write_guard();stage='load_update';
        [u,~,rhs]=phase_field.fem.solver.step.pre_iter_update(step,sys,u,sp);
        accepted=false;
        stag=0;
        while true
            stag=stag+1;
            res_u=NaN;res_pf=NaN;certificate_valid=false;native_return_pf_residual=NaN;check();stage='mechanics';kind='mechanics';
            [u,ec,er]=solve_field(@equilibrium_assembly,u,dofs.active_dof);
            assert(er.ok,['Mechanics failed: ',er.reason,' ',er.message]);driver=ec.driver;
            stage='phase';kind='phase';
            [alpha,~,pr]=box_phase_ray_progress(@phase_assembly,@(K,b)cholmod2(K,b),alpha,dofs.active_dof_pf,phase_opts);
            assert(pr.ok,'Box loaded PF failed');
            pc=phase_assembly(alpha);
            [~,native_return_pf_residual]=box_kkt_residual(alpha,pc.R,dofs.active_dof_pf);
            assert(native_return_pf_residual<=1e-6,'Fresh native PF return residual failed');
            % Both residuals refer to exactly this returned (u,alpha), history fixed.
            native_return_pf_residual=NaN;
            stage='same_state_certificate';ec=equilibrium_assembly(u);driver=ec.driver;pc=phase_assembly(alpha);
            res_u=norm(ec.R(dofs.active_dof));[pf_kkt,res_pf]=box_kkt_residual(alpha,pc.R,dofs.active_dof_pf);
            certificate_valid=true;tmp=sys.STIFFNESS_MATRIX;tmp.KK=ec.K;sys.STIFFNESS_MATRIX=tmp;
            fprintf(cf,'%d,%.17g,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f\n',...
                step,U,stag,res_u,res_pf,min(alpha),max(alpha),max(previous-alpha),(elapsed_offset+toc(started)));
            fprintf('COUPLED step=%d U=%.4f stag=%d Ru=%.9g Rpf=%.9g alpha=[%.9g,%.9g]\n',step,U,stag,res_u,res_pf,min(alpha),max(alpha));
            if res_u+res_pf<=1e-4,accepted=true;break;end
        end
        assert(accepted);stage='validity';
        assert(all(alpha(crack)==1),'Initial crack BC changed');
        assert(min(alpha)>=-.005 && max(alpha)<=1.005 && max(previous-alpha)<=.005,'Damage admissibility failed');
        assert(all(alpha>=0 & alpha<=1),'Exact box constraint failed');
        p_field=alpha;p_field_old=previous;displ=u;forces=ec.force;pf_force=pc.R;
        E_el=ec.energy;E_d=phase_field.mex.fem.processing.fracture_energy(MESH,GEOM.t,quad,mat,sys.CC,alpha,8/3,1);
        assert(isfinite(E_el+E_d));Rx_top=sum(forces(top));Rx_bottom=sum(forces(bot));
        Ry_top=sum(forces(top+MESH.num_node));Ry_bottom=sum(forces(bot+MESH.num_node));
        Ralong_top=Rx_top;Ralong_bottom=Rx_bottom;res_pf_raw=norm(pf_force(dofs.active_dof_pf));
        E_hist=history_energy(alpha,previous);
        timing='post_solve_pre_history_update';history_vars_old=history;
        save(fullfile(out_root,sprintf('state_%03d.mat',step)),'p_field','p_field_old','displ','U','step','timing',...
            'driver','forces','pf_force','history_vars_old','res_u','res_pf','E_el','E_d','equilibrium_evaluations','phase_evaluations','pf_kkt','res_pf_raw','Ry_top','Ry_bottom','Ralong_top','Ralong_bottom','E_hist','-v7');
        fprintf(tf,'%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%.6f,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n',...
            step,U,Rx_top,Rx_bottom,E_el,E_d,res_u,res_pf,min(alpha),max(alpha),max(previous-alpha),stag,(elapsed_offset+toc(started)),Ry_top,Ry_bottom,Ralong_top,Ralong_bottom,E_hist,res_pf_raw);
        fprintf('ACCEPTED step=%d U=%.4f seconds=%.1f\n',step,U,(elapsed_offset+toc(started)));
        stage='post_accepted_history_update';certificate_valid=false;res_u=NaN;res_pf=NaN;native_return_pf_residual=NaN;
        previous=alpha;
        [~,~,~,history]=pf(MESH,dofs,GEOM.t,quad,mat,sys.CC,alpha,previous,driver,sys.stress_state.as_number,history);
        check();finish_guard();
    end
    f=fopen(fullfile(out_root,'COMPLETED.txt'),'w');assert(f>=0);fprintf(f,'24 accepted loaded states through U=.4\n');fclose(f);
catch failure
    rejection_reason=failure.message;failure_stage=stage;timing='unaccepted_current_returned_pair';
    if any(strcmp(stage,{'recovery','phase'})),timing='unaccepted_outer_call_field; native_preupdate_points_saved_separately';end
    p_field=alpha;p_field_old=previous;displ=u;elapsed_seconds=(elapsed_offset+toc(started));step_seconds=toc(step_started);
    save(fullfile(out_root,sprintf('failed_state_%03d.mat',step)),'p_field','p_field_old','displ','U','step','stag',...
        'timing','driver','res_u','res_pf','certificate_valid','native_return_pf_residual','native_return_residual_timing','native_last_entered','native_last_completed','failure_stage','rejection_reason','elapsed_seconds','step_seconds','box_last_state','phase_direction_last','history','rhs','-v7');
    rethrow(failure);
end
diary off;
    function check()
        % Direct user authorization 2026-10-23: no compute time limit.
    end
    function c=equilibrium_assembly(value)
        check();equilibrium_evaluations=equilibrium_evaluations+1;
        [kv,f,d,~]=eq(MESH,dofs,GEOM.t,quad,mat,sys.CC,value,0,alpha,sys.stress_state.as_number,0);
        K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
        c=struct('u',value,'K',K,'R',f-rhs,'force',f,'driver',d,'energy',.5*(value'*K*value));check();
    end
    function varargout=counted_native_phase(varargin)
        native_phase_calls=native_phase_calls+1;
        native_last_entered=struct('call',native_phase_calls,'step',step,'stagger',stag,'alpha',varargin{7},...
            'timing','native_assembly_input_before_Newton_update','assembled',false);
        save(fullfile(out_root,'native_phase_last_points.mat'),'native_last_entered','native_last_completed','-v7');
        check();phase_evaluations=phase_evaluations+1;
        [varargout{1:nargout}]=pf(varargin{:});
        native_last_completed=struct('call',native_phase_calls,'step',step,'stagger',stag,'alpha',varargin{7},'Rpf',varargout{2},...
            'timing','native_assembly_input_before_Newton_update','assembled',true);
        fprintf(fid,'%d,%d,native_phase,preupdate_assembly,%d,-1,%.17g,NaN,NaN,%.6f\n',...
            step,stag,native_phase_calls,norm(varargout{2}(dofs.active_dof_pf)),(elapsed_offset+toc(started)));
        save(fullfile(out_root,'native_phase_last_points.mat'),'native_last_entered','native_last_completed','-v7');
        check();
    end
    function c=phase_assembly(value)
        check();phase_evaluations=phase_evaluations+1;
        [kv,r,~,~]=pf(MESH,dofs,GEOM.t,quad,mat,sys.CC,value,previous,driver,sys.stress_state.as_number,history);
        K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
        [Epf,~,energy_gradient]=box_q4_pf_energy(value,previous,driver,mat,energy_geom);
        energy_gradient_mismatch=norm(energy_gradient-r);
        assert(energy_gradient_mismatch<=1e-10*max(1,norm(r)),'BOX:NativeEnergyGradient','Native residual disagrees with original Q4 PF energy derivative');
        c=struct('u',value,'K',K,'R',r,'force',r,'driver',[],'energy',Epf);
        box_last_state=struct('alpha',value,'Rpf',r,'energy',Epf,'energy_gradient_mismatch',energy_gradient_mismatch,'driver',driver,'previous',previous,'step',step,'stagger',stag);check();
    end
    function Q=phase_curvature(a,direction)
        Q=box_q4_ray_curvature(a,direction,previous,driver,mat,energy_geom);
    end
    function clear_phase_direction()
        phase_direction_last=[];
    end
    function record_phase_direction(a,direction,R,choice)
        phase_direction_last=struct('alpha',a,'direction',direction,'Rpf',R,'choice',choice,'step',step,'stagger',stag);
    end
    function [lambda,info]=phase_ray_step(a,direction,slope)
        [lambda,info]=box_q4_ray_step(a,direction,previous,driver,mat,energy_geom,slope);
    end
    function E=history_energy(a,h)
        [~,E]=box_q4_pf_energy(a,h,driver,mat,energy_geom);
    end
    function [value,c,report]=solve_field(assembler,value,active)
        mechanics_opts=struct('beta',.5,'c1',1e-4,'res_tol',1e-6,'check',@check,'observe',@observe);
        [value,c,report]=unlimited_mechanical_newton(assembler,@(K,b)cholmod2(K,b),value,active,mechanics_opts);
    end
    function observe(e)
        active=dofs.active_dof_pf;if strcmp(kind,'mechanics'),active=dofs.active_dof;end
        tr=NaN;if ~isempty(e.trial_cache),tr=norm(e.trial_cache.R(active));end
        fprintf(fid,'%d,%d,%s,%s,%d,%d,%.17g,%.17g,%.17g,%.6f\n',...
            step,stag,kind,e.kind,e.iteration,e.trial,e.pre_residual,tr,e.lambda,(elapsed_offset+toc(started)));
        check();
    end
    function write_guard()
        g=struct('step',step,'unlimited_compute',true);
        target=fullfile(out_root,sprintf('step_guard_%03d.json',step));f=fopen([target,'.tmp'],'w');assert(f>=0);
        fprintf(f,'%s',jsonencode(g));fclose(f);movefile([target,'.tmp'],target);
    end
    function finish_guard()
        f=fopen(fullfile(out_root,sprintf('step_done_%03d.txt',step)),'w');assert(f>=0);fclose(f);
    end
end
