"""Read-only, explicit-allowlist inventory and saved-state provenance checks.

No model imports, PT deserialization, source mutation, solver or optimizer.
Use miniconda3 Python (h5py/scipy/numpy) on this Mac. Raw output is external.
"""
from pathlib import Path
import csv
import hashlib
import json
import zipfile
import argparse
import numpy as np
import h5py

PROJECT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
ARCHIVE = PROJECT / 'local_archive'
RUNS = ARCHIVE / 'experiments/S04-E011/runs'
WT = PROJECT / '.codex/worktrees'
CURRENT = WT / 'fem-synthetic-augmentation-design-20261017'
CLOUD = Path('/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith')
PAIR = RUNS / 'pf_s04e011_pidl_pair_ad749c8_20261008T0912Z'
MCS = RUNS / 'pf_s04e011_mcs_20261017_v1'
C1 = RUNS / 'pf_s04e011_c1_commit_20261016_v4_r1'
TIGHT = RUNS / 'pf_s04e011_tightcouple_137cb03_20261019T122720Z_production'
states, fields, checks, files = [], [], [], []


def js(p):
    return json.loads(Path(p).read_text())


def write_csv(p, rows):
    if not rows:
        raise ValueError(f'empty table: {p}')
    names = list(dict.fromkeys(k for row in rows for k in row))
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=names)
        w.writeheader()
        w.writerows(rows)


def raw_step(c, q):
    if c < 1 or q not in range(1, 6):
        raise ValueError('not a cyclic five-substep state')
    return 1 + 5*(c-1) + q-1


def check(name, passed, detail, source, kind='saved_data'):
    checks.append(dict(check=name, status='verified' if passed else 'mismatch',
                       detail=detail, source=str(source), evidence_kind=kind))


def state(package, family, c, q, label, source, role, timing, level='metadata', **extra):
    umax=extra.pop('umax',.12)
    row = dict(package=package, family=family, cycle=c, substep=q,
               umax=umax,trajectory=extra.pop('trajectory',family+':Umax='+str(umax)),
               recovery_offset_raw_step=raw_step(c, q) if c and q else '',
               export_label=label, source=str(source), role=role, timing=timing,
               verification=level, **extra)
    states.append(row)
    return row


def field(row, name, location, support, timing, counterpart='', meaning='', level=None):
    fields.append(dict(package=row['package'], family=row['family'], cycle=row['cycle'],
                       umax=row['umax'],trajectory=row['trajectory'],
                       substep=row['substep'], state_label=row['export_label'],
                       field=name, location=location, support=support, timing=timing,
                       counterpart=counterpart, meaning=meaning,
                       verification=level or row['verification']))


def record_file(path, role, expected=None):
    path = Path(path)
    row = dict(path=str(path), role=role, exists=path.is_file(),
               bytes=path.stat().st_size if path.is_file() else '', identity_check='not_requested')
    if expected:
        digest = hashlib.sha256()
        with path.open('rb') as f:
            for b in iter(lambda: f.read(1024*1024), b''):
                digest.update(b)
        row.update(sha256=digest.hexdigest(), identity_check='verified' if
                   row['bytes'] == expected['bytes'] and digest.hexdigest() == expected['sha256'] else 'mismatch')
        check('locked identity: '+role, row['identity_check']=='verified',
              dict(actual_bytes=row['bytes'], expected_bytes=expected['bytes']), path)
    files.append(row)


def hread(h, name):
    return np.asarray(h[name])


def scalar(h, name):
    return hread(h, name).item()


def npz_headers(p):
    rows = []
    with zipfile.ZipFile(p) as z:
        for name in z.namelist():
            if not name.endswith('.npy'):
                continue
            with z.open(name) as f:
                version = np.lib.format.read_magic(f)
                shape, fortran, dtype = np.lib.format._read_array_header(f, version)
            rows.append(dict(name=name[:-4], shape=shape, dtype=str(dtype)))
    return rows


def normgap(a, b):
    if a.shape != b.shape:
        return dict(equal=False, shapes=[a.shape,b.shape], maxabs=None)
    finite=np.isfinite(a)&np.isfinite(b)
    return dict(equal=bool(np.array_equal(a,b,equal_nan=True)),
                maxabs=float(np.max(np.abs(a[finite]-b[finite]))) if finite.any() else None,
                nonfinite_a=int((~np.isfinite(a)).sum()),nonfinite_b=int((~np.isfinite(b)).sum()),
                comparison='equal_nan numerical identity; opaque H is not certified as a physical channel')


def manifest_packages():
    """Only existing public package manifests; never read their MAT arrays."""
    for name in ['hard5_fixed_calendar_exposure_states_20260824_v3',
                 'hard5_u012_exact_peak_native_q4_c76_c82_c83_20260824_v2.1']:
        root = CLOUD/name
        m = js(root/'manifest.json')
        record_file(root/'manifest.json', 'package manifest')
        for s in m['states']:
            c,q = int(s['cycle']),int(s['substep'])
            p = root/s.get('source_snapshot',s['file'])
            row=state(name,'Hard5_original',c,q,f'c{c}s{q}',p,'analysis_snapshot_not_restart',s['state_timing'],
                      umax=s.get('umax',.12), effective_load_factor=s['effective_load_factor'],
                      payload_present=p.is_file(), origin='manifest only; no new field evaluation')
            schema=m.get('field_schema',[])
            if not schema:
                sf=root/'amendment/gate0_field_schema.csv'
                if sf.is_file():
                    schema=list(csv.DictReader(sf.open()))
            for f in schema:
                n=f.get('name',f.get('export_field',f.get('field',f.get('field_name','UNKNOWN'))))
                field(row,n,str(p)+'::request28_snapshot/'+n,str(f.get('support',f.get('shape','native declared'))),
                      f.get('state_timing',s['state_timing']),meaning=f.get('solver_variable_or_expression',f.get('origin','manifest schema'))+'; '+f.get('notes',''))
    root=CLOUD/'hard5_first_detect_state_semantics_export_20260817'
    for s in csv.DictReader((root/'state_index.csv').open()):
        c,q=int(s['source_cycle']),int(s['source_substep'])
        p=root/s['array_file'].replace('\\','/')
        row=state(root.name,'Hard5_original',c,q,s['output_id'],p,s['semantic_class'],
                  'post_commit per export name; detailed fields not re-opened',payload_present=p.is_file(),
                  umax=float(s['output_id'].split('_')[0][1:])/100)
        for n in ['u_node','d_node','alpha_bar_gp','psi_eff_prev_gp','f_alpha_gp']:
            field(row,n,str(p)+'::request28_snapshot/'+n,'native node or GP4','post_commit',level='schema_not_rechecked')


def paired_trajectories():
    for topo in ['q4','t3']:
        j=js(PAIR/f'analysis/multicycle_cross_replay/pidl_nodal/pidl_{topo}_nodal_trajectory.json')
        pidl=PAIR/f'analysis/multicycle_cross_replay/pidl_nodal/pidl_{topo}_nodal_trajectory.npz'
        fem=PAIR/f'analysis/multicycle_cross_replay/fem_nodal/fem_{topo}_nodal_trajectory.mat'
        with np.load(pidl,allow_pickle=False) as z:
            pc, ps = z['cycles'].astype(int), z['steps'].astype(int)
        with h5py.File(fem) as h:
            fc=hread(h,'cycles').reshape(-1).astype(int)
            fshapes={n:str(h[n].shape) for n in ['u_node','v_node','d_node']}
        check(topo+' paired cycle set',np.array_equal(pc,fc),dict(pidl=pc.tolist(),fem=fc.tolist()),fem,'index')
        jc=np.array([int(r['cycle']) for r in j['records']])
        jt=np.array([int(r['step']) for r in j['records']])
        check(topo+' JSON versus NPZ cycle/step index',np.array_equal(pc,jc) and np.array_equal(ps,jt),
              dict(npz_cycles=pc.tolist(),npz_steps=ps.tolist(),json_cycles=jc.tolist(),json_steps=jt.tolist()),pidl,'index')
        check(topo+' actual NPZ raw step mapping',np.array_equal(ps,np.array([raw_step(int(c),4) for c in pc])),
              dict(cycles=pc.tolist(),steps=ps.tolist()),pidl,'index')
        check(topo+' unique ordered index',len(pc)==len(set(pc)) and bool(np.all(np.diff(pc)>0)) and len(ps)==len(pc),
              dict(cycles=pc.tolist(),steps=ps.tolist()),pidl,'index')
        nh={r['name']:r['shape'] for r in npz_headers(pidl)}
        with h5py.File(fem) as h:
            for n in ['u_node','v_node','d_node']:
                check(topo+' field state axis '+n,nh[n][0]==len(pc) and h[n].shape[0]==len(fc) and nh[n][1]==h[n].shape[1],
                      dict(pidl_shape=nh[n],fem_shape=h[n].shape),fem,'shape')
        for r in j['records']:
            c=int(r['cycle'])
            check(f'{topo} c{c} raw index',int(r['step'])==raw_step(c,4),r['step'],j['archive'],'index')
            row=state('E011_pair_'+topo,'E011_ad749c8_'+topo,c,4,f'c{c}s4',pidl,
                      'original_same_cycle_peak','post_fit/post_history_refresh; FEM counterpart peak',
                      level='indices_and_headers',pidl_raw_step=r['step'],fem_source=str(fem),
                      accepted_history='own solver histories, not common predecessor')
            for n in ['u_node','v_node','d_node']:
                field(row,n,str(pidl)+'::'+n,f'native {topo} node; stored float32',
                      'peak post_fit',str(fem)+'::'+n,
                      'index pairing checked; float64 accuracy cannot be inferred from float32 export')
        comp=PAIR/f'analysis/trajectory_error/raw/pidl_{topo}_trajectory_compact.npz'
        with np.load(comp,allow_pickle=False) as z:
            cycles=z['cycles'].astype(int)
        for c in cycles:
            row=state('E011_compact_'+topo,'E011_ad749c8_'+topo,int(c),4,f'c{c}s4',comp,
                      'retained_peak_diagnostic','same physical peak; raw/g/active channels distinct',
                      level='indices_and_headers')
            for n in ['raw_gp','g_gp','active_gp']:
                field(row,n,str(comp)+'::'+n,f'{topo} native GP', 'same peak',
                      meaning='active_gp = GP product g*raw; not product of element means')
        check(topo+' missing c84 peak',84 not in cycles,
              'No retained PIDL c84 diagnostic. Report transition interval (c83,c85], not exact c84 field jump.',comp,'coverage')
        with np.load(PAIR/f'pidl_selected/pidl_{topo}_reduced.npz',allow_pickle=False) as z:
            timing=str(z['state_timing'])
        checks.append(dict(check=topo+' reduced-channel warning',status='documented_semantic_defect',
                           detail='Original FEM reduced active_driver was raw; old -99.98% active comparison withdrawn. Corrected native-GP replay exists. PIDL timing: '+timing,
                           source=str(PAIR/'analysis/decision.md'),evidence_kind='existing_correction'))


def mcs_metadata():
    cases=js(MCS/'analysis_v2/cases.json')
    for c in cases:
        name=c['case']
        p=MCS/'retrieved/output/mcs'/name/f"outer_{int(c['last_complete']):02d}.mat"
        if not p.exists():
            p=MCS/'retrieved/output/mcs'/name/f"outer_{int(c['last_complete'])}.mat"
        row=state('E011_MCS','E011_conditional_re_solve',int(c['cycle']),int(c['substep']),name,p,
                  'conditional_endpoint' if c['strict_accepted'] else 'budget_stop_not_accepted',
                  'fresh same-field outer audit; history trial only, 0 commits',
                  outer=c['last_complete'],accepted=c['strict_accepted'],anchor=c['anchor'],
                  history_commits=0, predecessor='own frozen original prior, not previous MCS case',
                  payload_present=p.is_file())
        if p.is_file():
            with h5py.File(p) as h:
                for key,value in [('controls/physical_cycle',c['cycle']),('controls/substep',c['substep']),('outer',c['last_complete'])]:
                    check(name+' endpoint scalar '+key,scalar(h,'point/'+key)==value,
                          dict(declared=value,stored=scalar(h,'point/'+key)),p,'index')
                for n in ['u','d','raw','ru','rd','history234']:
                    key='point/'+n
                    if key in h:
                        field(row,n,str(p)+'::'+key,str(h[key].shape),
                              'same-field fresh trial; not committed trajectory state',meaning='history234 channels A, current active driver, fatigue f')
        check(name+' published metadata consistency',bool(c['strict_accepted'])==(c['strict_stop']=='policy_tolerance'),
              dict(accepted=c['strict_accepted'],stop=c['strict_stop']),MCS/'analysis_v2/cases.json','published_result')


def c20_identity():
    lock=js(CURRENT/'docs/research/S04/S04-E027/data_lock.json')
    paths={k:Path(lock['root'])/v['relative'] for k,v in lock['payloads'].items()}
    for k,p in paths.items(): record_file(p,k,lock['payloads'][k])
    with h5py.File(paths['predecessor']) as old,h5py.File(paths['case']) as case,h5py.File(paths['reference']) as ref,h5py.File(paths['mesh']) as mesh:
        for k,v in [('cycle',20),('substep',3),('damage_committed',1),('history_committed',1)]:
            check('c20 predecessor '+k,scalar(old,'request28_snapshot/'+k)==v,v,paths['predecessor'])
        for k,v in [('physical_cycle',20),('substep',4)]:
            check('c20 endpoint '+k,scalar(ref,'point/controls/'+k)==v,v,paths['reference'])
        for a,b,label in [('pre/lower','request28_snapshot/d_node','immutable damage lower'),
                          ('pre/history','request28_snapshot/history_vars_old','immutable prior history')]:
            g=normgap(hread(case,a),hread(old,b));check(label,g['equal'],g,paths['case'])
        for n in ['u','d','raw','ru','rd','history234']:
            g=normgap(hread(case,'current/'+n),hread(ref,'point/'+n))
            check('current equals outer18: '+n,g['equal'],g,paths['reference'])
        check('c20 no physical history commit',scalar(case,'result/history_commits')==0,scalar(case,'result/history_commits'),paths['case'])
        checks.append(dict(check='c20 reference qualification',status='conditional_reference',
                           detail=f"outer18 policy_pass={int(scalar(ref,'point/policy_pass'))}; original archived reference/pass={int(scalar(case,'reference/pass'))}; not a native original trajectory replacement",
                           source=str(paths['case']),evidence_kind='saved_data'))
        for label,group,c,q,role,timing in [('prior','pre',20,3,'immutable_accepted_prior','post_commit c20s3'),
                                           ('trial','current',20,4,'conditional_same_state_endpoint','fresh trial; zero physical commits')]:
            row=state('E027_E034_sources','E011_conditional_re_solve',c,q,label,paths['case'],role,timing,level='identity_verified',
                      outer=18 if q==4 else '', history_commits=0 if q==4 else 'already_committed_prior',
                      current_conditional_solve_history_commits=0)
            for n in ['u','d','raw','history' if q==3 else 'history234']:
                field(row,n,str(paths['case'])+'::'+group+'/'+n,'native nodes/GP4',timing)
        row=state('E027_initializer','E011_ad749c8_q4',20,3,'trained_1NN_98',lock['initializer']['local_path'],
                  'warm_start_not_target','c20s3 weights; evaluated/refit for c20s4',level='source_lock',pidl_raw_step=98)
        for n in ['network_u','network_v','network_d']:
            field(row,n,lock['initializer']['local_path'],'network','warm start; not output target',meaning='PT not deserialized in this audit')


def c1_chain():
    root=C1/'retrieved/output/c1_commit'
    for arm in ['original','repaired']:
        prior=root/'common_initial.mat'; prior_group='common'
        for q in range(1,6):
            p=root/arm/f's{q}/accepted_commit.mat'
            with h5py.File(p) as h,h5py.File(prior) as prev:
                check(f'c1 {arm} s{q} cycle/substep',scalar(h,'event/cycle')==1 and scalar(h,'event/substep')==q,
                      [scalar(h,'event/cycle'),scalar(h,'event/substep')],p)
                check(f'c1 {arm} s{q} commit count',scalar(h,'event/commits')==1 and scalar(h,'event/pre_version')==q-1 and scalar(h,'event/post_version')==q,
                      [scalar(h,'event/commits'),scalar(h,'event/pre_version'),scalar(h,'event/post_version')],p)
                for n in ['u','d','lower','history','raw']:
                    gap=normgap(hread(h,'pre/'+n),hread(prev,prior_group+'/'+n))
                    check(f'c1 {arm} s{q} chain '+n,gap['equal'],gap,p)
                for n in ['history','lower']:
                    gap=normgap(hread(h,'proof/'+n),hread(h,'pre/'+n))
                    check(f'c1 {arm} s{q} proof old '+n,gap['equal'],gap,p)
                for n in ['u','d','raw']:
                    gap=normgap(hread(h,'proposed/'+n),hread(h,'proof/'+n))
                    check(f'c1 {arm} s{q} committed '+n,gap['equal'],gap,p)
                gap=normgap(hread(h,'proposed/lower'),hread(h,'proposed/d'))
                check(f'c1 {arm} s{q} committed lower',gap['equal'],gap,p)
                gh=hread(h,'proposed/history')
                gap=normgap(gh[1:4],hread(h,'proof/history234'))
                check(f'c1 {arm} s{q} committed trial history',gap['maxabs'] is not None and gap['maxabs']<=1e-10 and gap['nonfinite_a']==gap['nonfinite_b']==0,gap,p)
                gap=normgap(hread(h,'post/history'),gh)
                check(f'c1 {arm} s{q} post audit history input',gap['equal'],gap,p)
                gap=normgap(hread(h,'post/history234'),gh[1:4])
                check(f'c1 {arm} s{q} post audit trial idempotence',gap['maxabs'] is not None and gap['maxabs']<=1e-10 and gap['nonfinite_a']==gap['nonfinite_b']==0,gap,p)
                row=state('E011_c1_'+arm,'E011_'+arm+'_own_chain',1,q,f'c1s{q}',p,
                          'committed_own_chain','proof=fresh precommit; proposed=accepted durable state; post=fresh diagnostic after commit',
                          level='chain_identity_verified',accepted_version=q,
                          original_joint_pass=bool(scalar(h,'event/precommit_joint_pass')),
                          displacement=scalar(h,'event/uy'))
                for group,timing in [('pre','immutable previous accepted state'),('proof','fresh certificate using old history'),
                                     ('proposed','post_commit durable accepted state'),('post','fresh diagnostic using committed history; no extra commit')]:
                    for n,o in h[group].items():
                        if isinstance(o,h5py.Dataset):
                            field(row,group+'.'+n,str(p)+'::'+group+'/'+n,str(o.shape),timing,
                                  meaning='next step reads proposed; history slot1 opaque, slot2 A, slot3 active previous r, slot4 f')
            prior=p; prior_group='proposed'


def current_outputs():
    contract=js(TIGHT/'retrieved/root/contract.json')
    for s in contract['states']:
        c,q=s['cycle'],s['substep']
        check('tightcouple declared raw step',s['step']==raw_step(c,q),s['step'],TIGHT/'retrieved/root/contract.json','index')
    root=TIGHT/'retrieved/archive/output/c20_s4'
    paths=[root/'fields.npz']+sorted((root/'checkpoints').glob('*/fields.npz'))+sorted((root/'readouts').glob('*.npz'))
    for p in paths:
        row=state('E011_tightcouple','E011_fixed_c20s4',20,4,str(p.relative_to(root)),p,
                  'optimization_snapshot_not_physical_acceptance','fixed c20s4; 0 history commits; mechanics uses external FEM d',
                  level='contract_and_header',history_commits=contract['history_commits'])
        for f in npz_headers(p):
            meaning=('NN output damage, can vary with hidden updates; NOT damage used in mechanical residual/energy'
                     if f['name']=='d' else 'NPZ alone is not a complete restart state; no independent A/r/f/lower/identity')
            field(row,f['name'],str(p)+'::'+f['name'],str(f['shape']),row['timing'],
                  meaning=meaning)
        field(row,'d_mechanics',str(contract['states'][0]['input'])+'::external FEM damage','native Q4 nodes',
              'fixed external FEM damage for all optimization readouts',meaning='not the NPZ d network output; source runner explicitly distinguishes both',level='source_contract')
    for e in range(27,35):
        p=CURRENT/f'docs/research/S04/S04-E{e:03d}/data_lock.json'
        if not p.exists(): continue
        lock=js(p)
        row=state(f'S04-E{e:03d}','E011_fixed_c20s4',20,4,f'E{e:03d} endpoint',p,
                  'single_exposed_state_horizon0','source lock; own optimization iterations are not physical cycles',level='protocol_lineage')
        for n,meaning in [('u/v','trained or corrected at same load'),('d','E030 external physical damage inherited from E031 onward; read owning protocol'),
                          ('A/r/f','fixed original predecessor / declared reference coefficient; not autonomous history')]:
            field(row,n,str(p),'native node/GP4',row['timing'],meaning=meaning)


def self_checks():
    for c in [1,20,83,89,90,120]:
        for q in range(1,6):
            s=raw_step(c,q)
            assert (1+(s-1)//5,1+(s-1)%5)==(c,q)
    assert raw_step(20,3)==98 and raw_step(20,4)==99
    assert raw_step(89,4)==444 and raw_step(90,2)==447
    check('index sentinel examples',True,'98=c20s3; 99=c20s4; 444=c89s4; 447=c90s2, never c92',__file__,'synthetic_index_check')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise FileExistsError('fresh audit output required')
    args.out.mkdir(parents=True,exist_ok=True)
    self_checks();manifest_packages();paired_trajectories();mcs_metadata();c20_identity();c1_chain();current_outputs()
    keys=[(r['package'],r['trajectory'],r['umax'],r['cycle'],r['substep'],r['export_label']) for r in states]
    check('compound state identity unique',len(keys)==len(set(keys)),dict(rows=len(keys),unique=len(set(keys))),__file__,'index')
    write_csv(args.out/'state_map.csv',states);write_csv(args.out/'field_map.csv',fields)
    write_csv(args.out/'checks.csv',checks);write_csv(args.out/'file_inventory.csv',files)
    summary=dict(date='2026-10-20',state_rows=len(states),field_rows=len(fields),
                 check_count=len(checks),statuses={s:sum(r['status']==s for r in checks) for s in sorted({r['status'] for r in checks})},
                 coverage='explicit package manifests, retained paired peaks, MCS published endpoints, c1 saved commit chain, current c20 lineage',
                 excluded='closed holdout fields; remote data; PT/model deserialization; unretained complete original time histories; fresh scientific evaluation',
                 fresh_solver_calls=0,model_forward_calls=0)
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__': main()
