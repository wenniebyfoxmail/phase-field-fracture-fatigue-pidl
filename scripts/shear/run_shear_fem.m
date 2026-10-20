function run_shear_fem(griph_root, out_root, max_steps)
% One fresh, bounded AT1/AMOR monotonic shear trajectory. Native GRIPHFiTH
% assembly/Newton/staggering are retained; no edits to the shared installation.
assert(~isfolder(out_root), 'Fresh output directory required');
mkdir(out_root); cd(out_root);
diary(fullfile(out_root,'solver.log'));
start = tic;
addpath(fullfile(griph_root,'Sources'));
addpath(genpath(fullfile(griph_root,'Dependencies')));
[MESH, GEOM] = specimen.external.gmsh_import(...
    fullfile(griph_root,'Dependencies','meshes','sens_mesh.m'), 't', 1);
nodes = MESH.node; quads = MESH.elem;
assert(size(quads,2)==4, 'Expected native Q4 mesh');
top = find(abs(nodes(:,2)-0.5)<1e-10);
bot = find(abs(nodes(:,2)+0.5)<1e-10);
assert(~isempty(top) && ~isempty(bot));
MAT_CHAR = phase_field.init.material_characteristic(1,'AT1',...
    'E',1,'ni',0.3,'Gc',0.01,'ell',0.01,'res_stiff',0,...
    'tol_irrev',0.005,'tol_AT1_recovery',0.001);
NODE_BOUNDARIES = phase_field.fem.bc.set_boundaries(...
    'fix_X',bot,'fix_Y',[bot;top],'disp_X',top);
DOFS = phase_field.init.dofs(MESH,NODE_BOUNDARIES);
QUADRATURE = phase_field.init.quadrature(MESH.dim);
schedule = [0.03:0.03:0.21, 0.24:0.01:0.46]';
if nargin < 3, max_steps=numel(schedule); end
assert(max_steps>=1 && max_steps<=numel(schedule) && max_steps==floor(max_steps));
SOL_STEP_PAR = phase_field.fem.solver.step.params(...
    'n_step',numel(schedule),'ux_final',schedule(end));
SOL_STEP_PAR.ux_increment = diff([0;schedule]);
SOL_STEP_PAR.uy_increment = zeros(size(schedule));
SOL_STAG_PAR = phase_field.fem.solver.stag.params('tol',1e-4,'max_iter',1000);
% Retained-material diffuse AT1 notch, matching utils.hist_alpha_init.
distance = hypot(nodes(:,1)-min(max(nodes(:,1),-0.5),0),nodes(:,2));
alpha_initial = max(1-distance/0.02,0).^2;
p_field = alpha_initial; p_field_old = alpha_initial;
displ = zeros(DOFS.num_dof,1);
history_vars_old = zeros(MESH.num_elem,QUADRATURE.num_gauss_pts,1);
sys = phase_field.System(MAT_CHAR,GEOM,QUADRATURE,DOFS,NODE_BOUNDARIES,...
    SOL_STEP_PAR,MESH,phase_field.StressState.PlaneStrain,p_field,'AT1');
eq = @phase_field.mex.fem.assembly.equilibrium.AMOR;
pf = @phase_field.mex.fem.assembly.pf.AT1_PENALTY;
save(fullfile(out_root,'mesh.mat'),'nodes','quads','alpha_initial','schedule','top','bot','-v7');
U=0; step=0; timing='initial_unloaded_before_any_solve';
save(fullfile(out_root,'state_000.mat'),'nodes','quads','p_field','p_field_old','displ','U','step','timing','-v7');
fid=fopen(fullfile(out_root,'trajectory.csv'),'w');
cleaner=onCleanup(@() fclose(fid));
fprintf(fid,'step,U,Rx_top,Rx_bottom,E_el,E_d,res_u,res_pf,alpha_min,alpha_max,max_healing,stag_iters,seconds\n');
for step=1:max_steps
    assert(toc(start)<14400,'Four-hour FEM budget reached');
    previous_alpha=p_field_old;
    [displ,res_displ,D_RHS_tract] = phase_field.fem.solver.step.pre_iter_update(step,sys,displ,SOL_STEP_PAR);
    res_displ_0=norm(res_displ(DOFS.active_dof));
    SOL_STAG_VAR=phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
    accepted=false;
    for it=1:SOL_STAG_PAR.max_iter
        assert(toc(start)<14400,'Four-hour FEM budget reached');
        [~,ru,displ,driver,~,bad_u]=phase_field.fem.solver.newton_raphson(...
            eq,sys,displ,0,p_field,0,DOFS.active_dof,...
            sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,...
            'D_RHS_tract',D_RHS_tract,'max_iter',500,'res_tol',1e-6,'verbose',false);
        assert(~bad_u && all(isfinite(displ)),'Displacement Newton failed');
        [rpf0,rpf,p_field,~,~,bad_pf]=phase_field.fem.solver.newton_raphson(...
            pf,sys,p_field,p_field_old,driver,history_vars_old,DOFS.active_dof_pf,...
            sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,...
            'max_iter',500,'res_tol',1e-6,'regularize_pf_only',true,'verbose',false);
        assert(~bad_pf && all(isfinite(p_field)),'Phase-field Newton failed');
        if it==1, res_pf_0=rpf0; end
        [SOL_STAG_VAR,driver,accepted,KK]=phase_field.fem.solver.stag.post_iter_update(...
            eq,it,SOL_STAG_VAR,sys,D_RHS_tract,p_field,displ,...
            res_pf_0,rpf,res_displ_0,SOL_STAG_PAR);
        temp=sys.STIFFNESS_MATRIX; temp.KK=KK; sys.STIFFNESS_MATRIX=temp;
        if accepted, break; end
    end
    assert(accepted,'Staggered solve failed; do not export an accepted state');
    [~,forces,driver,~]=eq(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,...
        sys.MAT_CHAR,sys.CC,displ,0,p_field,sys.stress_state.as_number,0);
    res_u=norm(forces(DOFS.active_dof));
    [~,pf_force,~,~]=pf(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,...
        sys.MAT_CHAR,sys.CC,p_field,p_field_old,driver,sys.stress_state.as_number,history_vars_old);
    res_pf=norm(pf_force(DOFS.active_dof_pf));
    assert(isfinite(res_u+res_pf) && res_u+res_pf<=1e-4,'Accepted-state residual check failed');
    max_healing=max(previous_alpha-p_field);
    alpha_min=min(p_field); alpha_max=max(p_field);
    fprintf('CANDIDATE step=%d U=%.17g alpha_min=%.17g alpha_max=%.17g max_healing=%.17g res_u=%.17g res_pf=%.17g\n',...
        step,schedule(step),alpha_min,alpha_max,max_healing,res_u,res_pf);
    valid_damage=alpha_min>=-0.005 && alpha_max<=1.005 && max_healing<=0.005;
    if ~valid_damage
        U=schedule(step); timing='unaccepted_post_solve_pre_history_update';
        save(fullfile(out_root,sprintf('failed_state_%03d.mat',step)),...
            'p_field','p_field_old','displ','U','step','timing','driver','forces',...
            'res_u','res_pf','alpha_min','alpha_max','max_healing','-v7');
    end
    assert(valid_damage,...
        'Damage bounds or irreversibility exceeded tolerance');
    U=schedule(step); timing='post_solve_pre_history_update';
    E_el=SOL_STAG_VAR.el_en(it); E_d=SOL_STAG_VAR.fract_en(it);
    Rx_top=sum(forces(top)); Rx_bottom=sum(forces(bot));
    save(fullfile(out_root,sprintf('state_%03d.mat',step)),...
        'p_field','p_field_old','displ','U','step','timing','driver','forces','res_u','res_pf','E_el','E_d','-v7');
    fprintf(fid,'%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%.6f\n',...
        step,U,Rx_top,Rx_bottom,E_el,E_d,res_u,res_pf,min(p_field),max(p_field),max_healing,it,toc(start));
    fprintf('ACCEPTED step=%d U=%.4f Rx=%.6g maxalpha=%.6g seconds=%.1f\n',step,U,Rx_top,max(p_field),toc(start));
    p_field_old=p_field;
    [~,~,~,history_vars_old]=pf(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,...
        sys.MAT_CHAR,sys.CC,p_field,p_field_old,driver,sys.stress_state.as_number,history_vars_old);
end
fid_done=fopen(fullfile(out_root,'COMPLETED.txt'),'w');
fprintf(fid_done,'All %d requested states accepted (full trajectory=%d). Elapsed %.3f seconds.\n',max_steps,numel(schedule),toc(start)); fclose(fid_done);
diary off;
end
