#!/usr/bin/env python3
"""Prepare a reviewed frozen-history multicycle native diagnostic; never launch."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def build(prior, inventory, out, root, commit):
    assert not out.exists()
    out.mkdir(parents=True)
    old=prior/'retrieved'
    for p in old.glob('*.m'):
        if p.name not in ['entry.m','run_s04_e011_s2uj.m']:
            (out/p.name).write_bytes(p.read_bytes())
    # Change only case identity, actual substep and boundary assertions; all
    # numerical controller/mechanical/damage helpers remain byte-identical.
    case=(old/'e011_s2uj_case.m').read_text()
    case=case.replace('e011_s2uj_case(bits,','e011_mcs_case(cycle,substep,',1)
    case=case.replace('frozen=pre;U=bits(1);J=bits(2);R=1;', 'frozen=pre;bits=[1 1];U=1;J=1;R=1;')
    case=case.replace('pre_iter_update(2,sys,start.u,par.step)', 'pre_iter_update(substep,sys,start.u,par.step)')
    case=case.replace("predictor=struct('u',predicted,'r',r,'d',start.d);assert(all(D_RHS==0));", """predictor=struct('u',predicted,'r',r,'d',start.d);assert(all(D_RHS==0));
 n=sys.MESH.num_node;top=find(abs(sys.MESH.node(:,2)-max(sys.MESH.node(:,2)))<1e-12);
 assert(ismember(substep,[2 4]) && cycle>=1 && fix(cycle)==cycle);
 assert(max(abs(start.u(n+top)-par.previous_u))<1e-12,'E011:PreviousBoundary','Previous load differs');
 assert(max(abs(predicted(n+top)-par.target_u))<1e-12,'E011:TargetBoundary','Target load differs');""")
    case=case.replace("result=struct('U',U,", "result=struct('physical_cycle',cycle,'substep',substep,'target_u',par.target_u,'U',U,")
    case=case.replace("point.controls=struct('U',U,", "point.controls=struct('physical_cycle',cycle,'substep',substep,'target_u',par.target_u,'U',U,")
    assert 'pre_iter_update(2,' not in case and 'pre_iter_update(substep,' in case
    (out/'e011_mcs_case.m').write_text(case)
    driver=(old/'run_s04_e011_s2uj.m').read_text()
    driver=driver[:driver.index('assert(string(options.topology)=="q4" && ~SOL_STEP_PAR.line_search);')]
    driver=driver.replace('function result = run_s04_e011_s2uj', 'function result = run_s04_e011_mcs',1)
    driver+='''assert(string(options.topology)=="q4" && ~SOL_STEP_PAR.line_search);
m=options.manifest;z=load(m.staging(1).target,'node_coords','connectivity','free_dof_u','free_dof_d');
assert(isequal(z.node_coords,sys.MESH.node(:,1:2)) && isequal(z.connectivity,sys.MESH.elem(:,1:4)));
assert(isequal(z.free_dof_u,sys.DOFS.active_dof) && isequal(z.free_dof_d,sys.DOFS.active_dof_pf));clear z
ref=load(m.staging(3).target,'pre','start','current','predictor');
par=struct('step',SOL_STEP_PAR,'previous_u',.02999988,'target_u',.05999988);
[anchor,~,~]=e011_mcs_case(1,2,ref.pre,ref.start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'c1_common_anchor'),ref,[],ref.predictor);
assert(anchor.reference.pass);clear ref
cases=struct();
for cycle=[1 20 60 80 83]
 for substep=[2 4]
  previous_step=substep-1;role=sprintf('c%d_s%d',cycle,previous_step);
  idx=find(strcmp({m.staging.role},role));assert(isscalar(idx));
  z=load(m.staging(idx).target,'request28_snapshot');z=z.request28_snapshot;
  assert(z.cycle==cycle && z.substep==previous_step && z.history_committed && z.damage_committed);
  assert(isequal(z.node_coords,sys.MESH.node(:,1:2)) && isequal(z.connectivity,sys.MESH.elem(:,1:4)));
  assert(isequal(size(z.u_node),[sys.MESH.num_node 2]) && isequal(size(z.d_node),[sys.MESH.num_node 1]));
  assert(isequal(size(z.history_vars_old),[sys.MESH.num_elem 4 4]));
  pre=struct('u',z.u_node(:),'d',z.d_node,'lower',z.d_node,'raw',z.psi_raw_gp,'history',z.history_vars_old,'version',5*(cycle-1)+previous_step);
  start=struct('u',pre.u,'d',pre.d);
  par.previous_u=cfg.effective_load_factor(previous_step)*.12;par.target_u=cfg.effective_load_factor(substep)*.12;
  assert(abs(z.load_factor*.12-par.previous_u)<1e-12);clear z
  label=sprintf('c%d_s%d',cycle,substep);
  [one,~,~]=e011_mcs_case(cycle,substep,pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,label),[],[],[]);
  cases.(label)=one;
 end
end
result=struct('status','completed','history_commits',0,'recovery_calls',0,'shared_setup_initial_assemblies',1, ...
 'anchor',anchor,'cases',cases,'source_commit',m.source_commit,'scope','independent frozen-predecessor local restarts, not propagated trajectory');
fid=fopen(fullfile(work_dir,'result.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
fprintf('[E011_MCS_DONE] natural_cases=10 anchor=1 history_commits=0\\n');
end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''
    (out/'run_s04_e011_mcs.m').write_text(driver)
    previous=json.loads((old/'input_manifest.json').read_text())
    prior_remote=r'C:\Users\xw436\jobs\E011_S2UJ_20261017_v1'
    staging=[]
    for t in previous['staging'][:2]:
        t=t.copy();leaf=Path(t['target'].replace('\\','/')).name
        t.update(source=prior_remote+'\\inputs\\'+leaf,target=root+'\\inputs\\'+leaf)
        staging.append(t)
    anchor=old/'output/s2uj/U1J1/case.mat'
    staging.append(dict(role='anchor',source=prior_remote+r'\output\s2uj\U1J1\case.mat',target=root+r'\inputs\anchor_case.mat',bytes=anchor.stat().st_size,sha256=sha(anchor)))
    snapshots=json.loads(inventory.read_text())
    assert len(snapshots)==20 and {(x['cycle'],x['substep']) for x in snapshots}=={(c,s) for c in [1,20,60,80,83] for s in [1,2,3,4]}
    for t in snapshots:
        assert not t.get('missing')
        leaf=Path(t['path'].replace('\\','/')).name
        p=inventory.parent/'snapshot_inputs'/leaf
        assert p.stat().st_size==t['bytes'] and sha(p)==t['sha256']
        staging.append(dict(role=f"c{t['cycle']}_s{t['substep']}",source=t['path'],target=root+'\\inputs\\'+leaf,bytes=t['bytes'],sha256=t['sha256']))
    keys=['role','source','target','sha256','bytes']
    staging=[{k:x[k] for k in keys} for x in staging]
    previous.update(staging=staging,source_commit=commit,protocol_revision='S04-E011-MCS-r1')
    (out/'input_manifest.json').write_text(json.dumps(previous,indent=2)+'\n')
    oldentry=(old/'entry.m').read_text()
    entry=oldentry.split('try\n')[0].replace(prior_remote,root)+'try\n'
    entry+='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')))+'\n'
    entry+="reviewed_names={"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')))+",'entry.m'};\n"
    tail=oldentry[oldentry.index('for q=1:numel(reviewed_names)'):]
    tail=tail.replace('S04-E011-S2UJ-r1','S04-E011-MCS-r1').replace('numel(manifest.staging)==7','numel(manifest.staging)==23').replace('for k=1:7','for k=1:23').replace("'unique_inputs',7","'unique_inputs',23")
    tail=tail.replace("cfg.output_identity='s2uj';cfg.requested_cycles=1;cfg.defer_stop_until_cycle=1;", "cfg.output_identity='mcs';cfg.requested_cycles=[1 20 60 80 83];cfg.defer_stop_until_cycle=83;")
    tail=tail.replace("'output','s2uj'","'output','mcs'").replace("'max_cycle',1,","'max_cycle',83,").replace('run_s04_e011_s2uj(cfg,options)','run_s04_e011_mcs(cfg,options)')
    entry+=tail
    (out/'entry.m').write_text(entry)
    launch=(old/'launch_wmi.ps1').read_text().replace(prior_remote,root).replace('$stageRows.Count -ne 7','$stageRows.Count -ne 23').replace('Expected seven inputs','Expected23inputs')
    start=launch.index("if((Get-FileHash ($root+");end=launch.index('$manifest=')
    checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'Snapshot changed: {p.name}'}}" for p in sorted(out.iterdir()))+'\n'
    launch=launch[:start]+checks+launch[end:]
    launch=launch.replace('pf_s04e011_s2uj_20261017_v1','pf_s04e011_mcs_20261017_v1').replace(previous.get('original_producer_commit','383a77827d3f60be6bcc0326c6923451df94a96d'),commit)
    (out/'launch_wmi.ps1').write_text(launch)
    files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())]
    assert len(staging)==23 and 'pre_iter_update(substep,' in case and 'pre_iter_update(2,' not in case
    return dict(source_commit=commit,protocol_revision='S04-E011-MCS-r1',remote_root=root,files=files,staging=staging,bytes=sum(x['bytes'] for x in files),staging_bytes=sum(x['bytes'] for x in staging),source_prior=str(prior),cases=11)


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for key in ['prior','inventory','out']:ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--root',required=True);ap.add_argument('--commit',required=True)
    args=ap.parse_args();z=build(args.prior,args.inventory,args.out,args.root,args.commit)
    (args.out.parent/'package_manifest.json').write_text(json.dumps(z,indent=2)+'\n')
    print(json.dumps({k:v for k,v in z.items() if k not in ['files','staging']},indent=2))
