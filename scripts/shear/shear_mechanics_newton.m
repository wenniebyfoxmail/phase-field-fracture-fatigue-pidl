function [u,driver,forces,ru,energy,report] = shear_mechanics_newton(eq,sys,u,alpha,rhs,check,root,step,stag,U,get_count)
% Task-local mechanics only. Native assembly, cholmod2 and PF law unchanged.
folder=fullfile(root,'mechanics',sprintf('step_%03d',step),sprintf('stag_%04d',stag));
assert(~isfolder(folder),'Fresh mechanics trace required'); mkdir(folder);
save(fullfile(folder,'phase_context.mat'),'alpha','U','step','stag','-v7');
fid=fopen(fullfile(folder,'trace.csv'),'w');assert(fid>=0);cleanup=onCleanup(@()fclose(fid));
fprintf(fid,'event,iteration,trial,lambda,pre_Ru,trial_Ru,pre_merit,trial_merit,slope,linear_residual,evaluations,updates,global_evaluation_id,seconds\n');
started=tic;active=sys.DOFS.active_dof(:);
opts=struct('max_iter',500,'max_backtracks',12,'beta',0.5,'c1',1e-4,...
    'res_tol',1e-6,'check',check,'observe',@observe);
[u,cache,report]=bounded_mechanical_newton(@assemble,@(K,b)cholmod2(K,b),u,active,opts);
report.trace_folder=folder;
if isempty(cache)
    driver=[];forces=[];ru=NaN;energy=NaN;
else
    driver=cache.driver;forces=cache.force;ru=norm(cache.R(active));energy=cache.energy;
end
save(fullfile(folder,'report.mat'),'report','-v7');
    function c=assemble(value)
        [kv,f,d,~]=eq(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,...
            sys.MAT_CHAR,sys.CC,value,0,alpha,sys.stress_state.as_number,0);
        K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
        R=f;if any(rhs~=0), R=R-rhs;end
        c=struct('u',value,'K',K,'force',f,'R',R,'driver',d,'energy',0.5*(value'*K*value),'evaluation_id',get_count());
    end
    function observe(e)
        tr=NaN;tm=NaN;
        if ~isempty(e.trial_cache),tr=norm(e.trial_cache.R(active));tm=0.5*tr^2;end
        gid=NaN;if ~isempty(e.trial_cache),gid=e.trial_cache.evaluation_id;elseif ~isempty(e.cache),gid=e.cache.evaluation_id;end
        fprintf(fid,'%s,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%d,%.17g,%.6f\n',...
            e.kind,e.iteration,e.trial,e.lambda,e.pre_residual,tr,e.pre_merit,tm,...
            e.slope,e.linear_residual,e.report.evaluations,e.report.updates,gid,toc(started));
        if any(strcmp(e.kind,{'pre','direction','accepted','converged','failure'}))
            frame=struct('kind',e.kind,'iteration',e.iteration,'trial',e.trial,...
                'lambda',e.lambda,'slope',e.slope,'linear_residual',e.linear_residual,...
                'direction',e.direction,'report',e.report,'available_origin_force',~isempty(e.cache));
            if ~isempty(e.cache)
                frame.u=e.cache.u;frame.forces=e.cache.force;frame.R=e.cache.R;
                frame.evaluation_id=e.cache.evaluation_id;frame.driver=e.cache.driver;frame.energy=e.cache.energy;
            end
            if any(strcmp(e.kind,{'pre','direction'}))
                file=fullfile(folder,sprintf('iter_%04d_origin.mat',e.iteration));
            elseif strcmp(e.kind,'accepted')
                file=fullfile(folder,sprintf('iter_%04d_accepted.mat',e.iteration));
            else
                file=fullfile(folder,[e.kind,'.mat']);
                frame.last_trial_u=e.trial_u;
                frame.available_trial_force=~isempty(e.trial_cache);
                if ~isempty(e.trial_cache)
                    frame.last_trial_forces=e.trial_cache.force;
                    frame.last_trial_driver=e.trial_cache.driver;
                end
            end
            save(file,'-struct','frame','-v7');
        end
        check();
    end
end
