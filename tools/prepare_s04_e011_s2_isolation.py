#!/usr/bin/env python3
"""Prepare exact c1s2 control-isolation bundle locally; never launch."""
import argparse,json,hashlib
from pathlib import Path
from prepare_s04_e011_s2_factorial import build as base_build,sha

def build(prior,priorx,out,root,commit):
 base_build(prior,out,root,commit)
 here=Path(__file__).parent/'s04_e011_analysis/s2_isolation';old=prior/'retrieved'
 for name in ['e011_s2i_case.m','e011_unbounded_fresh.m','e011_s2i_selftest.m','e011_s2i_fatal.m','e011_s2i_stop.m']:(out/name).write_bytes((here/name).read_bytes())
 (out/'e011_s2x_case.m').unlink();(out/'run_s04_e011_s2x.m').unlink()
 # Original numerical loop: observational callback only, or phase-strategy substitution.
 s=(old/'e011_original_step.m').read_text()
 s=s.replace('counts_fh,i_step)','counts_fh,i_step,observe,remaining_d)',1)
 # Keep numerical successful path unchanged; classify finite inner misses explicitly.
 for field,msg in [('res_displ','displacement residual is NaN or Newton-Raphson did not converge'),('res_pf','phase-field residual is NaN or Newton-Raphson did not converge')]:
  s=s.replace('if isnan('+field+') || non_conv',"if isnan("+field+"),error('E011:Nonfinite','Nonfinite returned residual');end\n            if non_conv")
  s=s.replace("error('"+msg+"');","error('E011:InnerMiss','Finite inner nonconvergence');")
 s=s.replace('                phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);','                % No life export for a diagnostic inner miss.')

 marker=" save(fullfile(work_dir,'original_progress.mat')"
 assert s.count(marker)==1;s=s.replace(marker,' observe(displ,p_field,strain_en_undgr,i_stag);\n'+marker)
 original=s.replace('e011_original_step(','e011_original_observed(',1).replace('observe,remaining_d)','observe,~)',1)
 (out/'e011_original_observed.m').write_text(original)
 start=s.index('            [i_res_pf_0, res_pf, p_field, ~, history_vars_new, non_conv] =')
 end=s.index("            if isnan(res_pf),error('E011:Nonfinite'",start)
 replacement='''            phase_budget=remaining_d();assert(phase_budget>=2,'E011:DBudget','Phase reserve');
            phase_result=bounded_phase(sys,assembly_pf_fh,p_field,p_field_old,strain_en_undgr,history_vars_old,phase_budget,SOL_PAR.tol_p_field);
            nested_failure=e011_s2i_fatal(phase_result);assert(strlength(nested_failure)==0,'E011:ControllerFailure','%s',nested_failure);
            assert(phase_result.returned_residual_available && strlength(phase_result.failure)==0 && phase_result.filtered_l2<=SOL_PAR.tol_p_field,'E011:PhaseInnerMiss','Constrained phase miss');
            i_res_pf_0=phase_result.trace(1).filtered_l2;res_pf=phase_result.filtered_l2;
            p_field=phase_result.d;history_vars_new=phase_result.history;non_conv=false;
'''
 s=s[:start]+replacement+s[end:]
 s=s.replace('e011_original_step(','e011_original_bounded(',1)
 s+='''
function out=bounded_phase(sys,native,d,lower,raw,history,budget,tol)
out=e011_damage_solve(@matrix,d,lower,ones(size(d)),sys.DOFS.active_dof_pf,"constrained",budget,tol);
 function [K,r,h]=matrix(x)
  [kv,r,~,h]=native(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,x,lower,raw,sys.stress_state.as_number,history);
  K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
 end
end
'''
 (out/'e011_original_bounded.m').write_text(s)
 s=(old/'e011_coupled_solve.m').read_text().replace('e011_coupled_solve(eq,pf,u0,d0,lower,upper,fu,fd,limits,checkpoint)','e011_s2i_coupled(eq,pf,u0,d0,lower,upper,fu,fd,limits,checkpoint,damage_mode,loose)',1)
 needle='  dout=e011_damage_solve(@(d)phase(d,work_raw),current.d,lower,upper,fd,"constrained",limits.max_d-counts.d-1,limits.d_tol);'
 assert s.count(needle)==1
 s=s.replace(needle,'''  if damage_mode==1
'''+needle+'''
  else
   dout=e011_unbounded_fresh(@(d)phase(d,work_raw),current.d,lower,upper,fd,limits.max_d-counts.d-1,limits.d_tol);
  end''')
 needle='criterion=max(total/limits.joint_tol,ur/limits.u_tol);';assert s.count(needle)==1
 s=s.replace(needle,'criterion=e011_s2i_stop(ur,dr,norm(rd(fd)),limits,damage_mode,loose);')
 (out/'e011_s2i_coupled.m').write_text(s)
 # Retain exact reviewed native setup prefix; do not run recovery or commit.
 s=(old/'run_s04_e011_c1_commit.m').read_text().split('assert(options.max_cycle==1')[0].replace('run_s04_e011_c1_commit','run_s04_e011_s2i',1)
 s+='''
assert(string(options.topology)=="q4" && cfg.displacement_tol==1e-6 && cfg.pf_tol==4e-4 && cfg.staggered_tol==4e-4);
m=options.manifest;z=load(m.staging(1).target,'node_coords','connectivity','free_dof_u','free_dof_d');
assert(isequal(z.node_coords,sys.MESH.node(:,1:2)) && isequal(z.connectivity,sys.MESH.elem(:,1:4)));
assert(isequal(z.free_dof_u,sys.DOFS.active_dof) && isequal(z.free_dof_d,sys.DOFS.active_dof_pf));clear z
z=load(m.staging(3).target,'proposed');pre=z.proposed;z=load(m.staging(4).target,'proposed');other=z.proposed;clear z
start=struct('u',pre.u,'d',max(pre.d,other.d));assert(pre.version==1 && other.version==1);
par=struct('inner',SOL_PAR,'stag',SOL_STAG_PAR,'step',SOL_STEP_PAR,'crack',CRACK_PAR);
mat0=sys.MAT_CHAR;mat0.p=0;admission=cell(3,1);
for k=1:3
 d=start.d;raw=pre.raw;if k>=2,d(sys.DOFS.active_dof_pf)=-.25;raw=ones(size(pre.raw));end
 if k==3,raw(:)=1e20;end
 [k2,r2,~,h2]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d,pre.lower,raw,sys.stress_state.as_number,pre.history);
 [k0,r0,~,h0]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,mat0,sys.CC,d,pre.lower,raw,sys.stress_state.as_number,pre.history);
 assert(all(isfinite([k2;k0;r2;r0])) && all(isfinite(h2(:,:,2:4)),'all') && all(h0(:,:,4)==1,'all'));
 assert(isequal(h0(:,:,2:3),h2(:,:,2:3)));
 if k==1,assert(all(h2(:,:,4)==1,'all') && max(abs(k0-k2))<=1e-10 && max(abs(r0-r2))<=1e-10);elseif k==2,assert(min(h2(:,:,4),[],'all')<1 && max(abs(r0-r2))>1e-10);else,assert(min(h2(:,:,4),[],'all')==0);end
 admission{k}=struct('d',d,'raw',raw,'lower',pre.lower,'history',pre.history,'k2',k2,'r2',r2,'h2',h2(:,:,2:4),'k0',k0,'r0',r0,'h0',h0(:,:,2:4));
end
node_coords=sys.MESH.node(:,1:2);connectivity=sys.MESH.elem(:,1:4);
save(fullfile(work_dir,'admission.mat'),'admission','node_coords','connectivity','-v7.3');clear admission k2 k0 r2 r0 h2 h0
ref=load(m.staging(5).target,'candidate','proof','out');
[r000,predictor,cache]=e011_s2i_case([0 0 0],pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'000'),ref,[],[]);
assert(r000.reference.pass);
ref=load(m.staging(6).target,'candidate','proof','out');
[r110,~,~]=e011_s2i_case([1 1 0],pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'110'),ref,cache,predictor);
assert(r110.reference.pass);clear ref
names={'001','100','101','111','T1','T0','011','010'};
bits=[0 0 1;1 0 0;1 0 1;1 1 1;1 2 0;0 2 0;0 1 1;0 1 0];
rows=cell(10,1);rows{1}=r000;rows{2}=r110;
for k=1:numel(names)
 [rows{k+2},~,~]=e011_s2i_case(bits(k,:),pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,names{k}),[],cache,predictor);
end
result=struct('status','completed','history_commits',0,'recovery_calls',0,'shared_setup_initial_assemblies',1,'admission_phase_calls',6,'cases',{rows},'case_names',{{'000','110',names{:}}},'cycle',1,'substep',2,'source_commit',m.source_commit);
fid=fopen(fullfile(work_dir,'result.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
fprintf('[E011_S2I_DONE] cases=10 history_commits=0\\n');
end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''
 (out/'run_s04_e011_s2i.m').write_text(s)
 manifest=json.loads((out/'input_manifest.json').read_text());manifest['protocol_revision']='S04-E011-S2I-r1'
 xr=r'C:\Users\xw436\jobs\E011_S2X_20261016_v1'
 for i,(name,case) in enumerate([('anchor000','C_OO'),('anchor110','C_RO')],4):
  p=priorx/'retrieved/output/s2x'/case/'completed.mat'
  manifest['staging'][i]=dict(role=name,source=xr+'\\output\\s2x\\'+case+'\\completed.mat',target=root+'\\inputs\\'+name+'_completed.mat',sha256=sha(p),bytes=p.stat().st_size)
 (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 entry=(out/'entry.m').read_text();start=entry.index('try\n')+4;end=entry.index('for q=1:numel(reviewed_names)')
 head='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')) if p.name!='entry.m')+'\n'
 head+="reviewed_names={"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')) if p.name!='entry.m')+",'entry.m'};\n"
 entry=entry[:start]+head+entry[end:]
 entry=entry.replace('S04-E011-S2X-r1','S04-E011-S2I-r1').replace("'raw',e011_raw_equivalence())","'raw',e011_raw_equivalence(),'isolation',e011_s2i_selftest())").replace("cfg.output_identity='s2x'","cfg.output_identity='s2i'").replace("'output','s2x'","'output','s2i'").replace('run_s04_e011_s2x(cfg,options)','run_s04_e011_s2i(cfg,options)')
 (out/'entry.m').write_text(entry)
 launch=(out/'launch_wmi.ps1').read_text();begin=launch.index("if((Get-FileHash ($root+");end=launch.index('$manifest=')
 checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'Snapshot changed: {p.name}'}}" for p in sorted(out.iterdir()) if p.name!='launch_wmi.ps1')+'\n'
 launch=launch[:begin]+checks+launch[end:];launch=launch.replace('pf_s04e011_s2x_20261016_v1','pf_s04e011_s2i_20261016_v1')
 (out/'launch_wmi.ps1').write_text(launch)
 files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())]
 return dict(source_commit=commit,remote_root=root,protocol_revision='S04-E011-S2I-r1',files=files,staging=manifest['staging'],bytes=sum(r['bytes'] for r in files),source_prior=str(prior),source_s2x=str(priorx))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prior',type=Path,required=True);ap.add_argument('--priorx',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--root',required=True);ap.add_argument('--commit',required=True);a=ap.parse_args();m=build(a.prior,a.priorx,a.out,a.root,a.commit);(a.out.parent/'package_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
