#!/usr/bin/env python3
"""Prepare local Stage A overlay/config payloads; never contact or launch a host.

support creates an overlay and a read-only PowerShell inventory script.
finalize consumes actual retrieved preparation/build/inventory receipts and
creates one mode's exact manifest/config/entry. It never invents binary hashes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import zipfile

MODES = ('disabled', 'frozen_c1', 'frozen_c20', 'frozen_c60', 'frozen_c83')
NATIVE_COMMIT = '862992a60edc7f59335365beacb5c71fc8592a7a'
CHOLMOD_PATH = 'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB/cholmod2.mexw64'
CHOLMOD_SHA = '86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329'
FUNCTIONS = (
    'phase_field.System', 'phase_field.StressState', 'phase_field.init.ElementType',
    'phase_field.init.material_characteristic', 'phase_field.init.dofs',
    'phase_field.init.quadrature', 'phase_field.init.stiffness_matrix',
    'phase_field.init.elastic_stiffness_matrix', 'phase_field.init.boundary_conditions',
    'phase_field.fem.bc.set_boundaries', 'phase_field.fem.solver.params',
    'phase_field.fem.solver.newton_raphson', 'phase_field.fem.solver.step.params',
    'phase_field.fem.solver.step.pre_iter_update', 'phase_field.fem.solver.stag.params',
    'phase_field.fem.solver.stag.vars', 'phase_field.fem.solver.stag.post_iter_update',
    'phase_field.fem.crack.params', 'phase_field.fem.quadrature.fe_quadrature',
    'phase_field.fem.shape_functions.shape_fcts', 'specimen.external.abaqus_import',
    'compatiblity.r2020b.mustBeA', 'compatiblity.r2020b.mustBeTextScalar',
    'compatiblity.r2020b.mustBeNonzeroLengthText',
)
EXISTING_MEX = (
    'phase_field.mex.fem.assembly.equilibrium.initial',
    'phase_field.mex.fem.processing.fracture_energy',
    'phase_field.mex.fem.processing.D_tract_assembly',
)
FRESH_MEX = {'AMOR':'phase_field.mex.fem.assembly.equilibrium.AMOR',
             'AT1_PENALTY_FATIGUE':'phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE'}
IMPORTER_PATH = 'Sources/+specimen/+external/abaqus_import.m'
IMPORTER_ORIGINAL_SHA = '30c5e305c14f38424157b6a8c27428762d06b61a567ed094115dca1570d2f639'
IMPORTER_REPAIRED_SHA = 'd8c6bc885f9f34759f9f1b0f9daa49ffb855e646efe9c5de0cc3ee1cd6470667'
IMPORTER_REPAIR = dict(schema='e036-e011-importer-repair-v1', original_path=IMPORTER_PATH,
    original_sha256=IMPORTER_ORIGINAL_SHA, repaired_sha256=IMPORTER_REPAIRED_SHA,
    base_overlay='overlay_02',
    base_overlay_receipt_sha256='9e5b7f23c7119671802df63c44e59351e5c308c5efdccf774af1199a89280baf',
    operation='remove_round4_and_derive_nel_from_connectivity')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, *, wrapped=False):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if wrapped and 'stdout' in value:
        if value.get('exit_code') != 0:
            raise ValueError('cannot use a failed inventory operation')
        value = json.loads(value['stdout'])
    return value


def win(path):
    return PureWindowsPath(path).as_posix()


def relative(path, root):
    return PureWindowsPath(path).relative_to(PureWindowsPath(root)).as_posix()


def checked_rel(path):
    value = PurePosixPath(path)
    if value.is_absolute() or '..' in value.parts or ':' in path or '\\' in path:
        raise ValueError(f'unsafe relative path: {path}')
    return value.as_posix()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, indent=2, allow_nan=False)+'\n')


def archive(folder, name):
    files = {p.relative_to(folder).as_posix():p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}
    path = folder.parent/name
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as output:
        for member,data in files.items():
            output.writestr(checked_rel(member),data)
    with zipfile.ZipFile(path) as output:
        for member,data in files.items():
            if output.read(member) != data:
                raise ValueError('ZIP byte readback mismatch')
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size,
                files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})


def overlay_support(support_dir, root):
    """Select the original overlay or the one exact E011 importer repair."""
    metadata=read(support_dir/'support.json')
    if (metadata.get('schema')!='e036-native-support-v1' or metadata.get('source_commit')!=NATIVE_COMMIT
            or win(metadata['run_root']).lower()!=win(root).lower()):
        raise ValueError('overlay support belongs to another task/source')
    name=metadata.get('overlay')
    if name not in ('overlay_02','overlay_03'):
        raise ValueError('only the original overlay or declared importer repair is supported')
    overlay=support_dir/name;receipt=read(overlay/'overlay_receipt.json')
    repair=metadata.get('mesh_importer_repair')
    if name=='overlay_02':
        if repair is not None:
            raise ValueError('original overlay cannot declare a repair')
    else:
        if repair!=IMPORTER_REPAIR or sha(overlay/'overlay_receipt.json')!=IMPORTER_REPAIR['base_overlay_receipt_sha256']:
            raise ValueError('require the exact declared importer repair and unchanged base receipt')
        local=Path(__file__).with_name('importer_e011')/'abaqus_import.m'
        if sha(overlay/IMPORTER_PATH)!=IMPORTER_REPAIRED_SHA or sha(local)!=IMPORTER_REPAIRED_SHA:
            raise ValueError('full-precision importer differs from the exact E011 byte patch')
    expected={checked_rel(p) for p in receipt['files']}|{'overlay_receipt.json'}
    if repair is not None:
        expected.add(IMPORTER_PATH)
    actual={p.relative_to(overlay).as_posix() for p in overlay.rglob('*') if p.is_file()}
    if actual!=expected:
        raise ValueError('unexpected/missing overlay file')
    return name,overlay,receipt,repair


def support(args):
    output = args.output;output.mkdir(parents=False,exist_ok=False)
    spec = importlib.util.spec_from_file_location('e036_text_overlay',Path(__file__).with_name('build_overlay.py'))
    builder = importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    builder.build(args.audited_source_dir,output/'overlay_02')
    root = win(args.run_root)
    # This script only hashes existing task files. It starts no MATLAB/Python.
    ps = """$ErrorActionPreference='Stop'
$root=__ROOT__; $native=Join-Path $root 'native'
if(-not (Test-Path -LiteralPath $native -PathType Container)){throw 'Missing native snapshot'}
$files=@(Get-ChildItem -LiteralPath $native -Recurse -File | Where-Object {$_.Extension -in '.m','.f90','.mexw64'} | ForEach-Object {
 @{path=$_.FullName.Substring($native.Length+1).Replace('\\','/');sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower();bytes=$_.Length}
})
$r=@{schema='e036-native-snapshot-inventory-v1';native_snapshot=$native;files=$files;scope='read-only hashes; no MATLAB or scientific execution'}
$r|ConvertTo-Json -Depth 5
""".replace('__ROOT__',"'"+root.replace("'","''")+"'")
    write(output/'native_inventory_02.ps1',ps)
    write(output/'support.json',dict(schema='e036-native-support-v1',run_root=root,
        source_commit=NATIVE_COMMIT,overlay='overlay_02',overlay_builder_sha256=sha(Path(__file__).with_name('build_overlay.py')),
        generator_sha256=sha(__file__),scope='local text preparation; no remote deployment or native execution'))
    receipt = archive(output,output.name+'.zip')
    write(output.parent/(output.name+'_receipt.json'),receipt)
    print(json.dumps(receipt,indent=2))


def finalize(args):
    output=args.output
    if output.exists():
        raise FileExistsError(output)
    if not re.fullmatch('[a-z0-9_]+',args.label):
        raise ValueError('explicit fresh watchdog label required')
    cfg=read(args.prepare_config);root=win(cfg['run_root']);native=win(cfg['native_snapshot'])
    if relative(native,root) != 'native':
        raise ValueError('expected existing native snapshot')
    inventory=read(args.inventory,wrapped=True);snapshot=read(args.snapshot_receipt,wrapped=True)
    prepared=read(args.prepare_result);built=read(args.build_receipt);completion=read(args.build_completion)
    if inventory.get('schema')!='e036-native-snapshot-inventory-v1' or win(inventory['native_snapshot']).lower()!=native.lower():
        raise ValueError('inventory belongs to another native snapshot')
    if snapshot['source_commit']!=NATIVE_COMMIT or win(snapshot['snapshot']).lower()!=native.lower():
        raise ValueError('wrong original snapshot receipt')
    if (prepared.get('status')!='prepared_build_and_mock_completed_no_native_call' or
            prepared.get('mock',{}).get('status')!='passed' or prepared['mock'].get('cases')!=28):
        raise ValueError('actual 28-case preparation completion required')
    if prepared.get('config_sha256')!=sha(args.prepare_config) or prepared.get('manifest_sha256')!=cfg['manifest_sha256']:
        raise ValueError('preparation result belongs to another config or source manifest')
    if (completion.get('status')!='built_not_scientifically_verified' or
            completion.get('receipt_sha256')!=sha(args.build_receipt) or
            win(built['snapshot_root']).lower()!=native.lower() or
            win(built['build_root']).lower()!=win(cfg['build_root']).lower()):
        raise ValueError('fresh build receipt chain differs')
    # Each attempt receives a separately prepared authority, never the
    # preparation label's authority. This tool does not create approval.
    authority=read(args.authority_file)
    if not isinstance(authority,dict) or not {'global_deadline_utc','arm_wall_seconds'} <= authority.keys():
        raise ValueError('authority must explicitly supply global deadline and arm fields, including null')
    if (authority.get('schema')!='e036-stage-a-authority-v1' or authority.get('stage')!='A'
            or win(authority.get('run_root','')).lower()!=root.lower()
            or authority.get('producer_hostname')!='CITPC12'
            or authority.get('allowed_labels')!=[args.label]
            or not authority.get('authority_id') or not authority.get('human_authorization_ref')):
        raise ValueError('fresh authority must bind this exact task and one attempt label')
    threads=authority.get('max_compute_threads');wall=authority.get('per_job_wall_seconds')
    if type(threads) is not int or not 1<=threads<=4:
        raise ValueError('authority thread count must be an integer in [1,4]')
    if type(wall) not in (int,float) or not 0<wall<float('inf'):
        raise ValueError('authority needs a finite positive per-job hang limit')
    arm=authority.get('arm_wall_seconds')
    if args.mode=='disabled' and (type(arm) not in (int,float) or not 0<arm<=wall):
        raise ValueError('disabled control needs a finite positive arm limit within the job limit')
    authorized=authority.get('authorized_at_utc','')
    if not isinstance(authorized,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',authorized):
        raise ValueError('authority timestamp must match MATLAB UTC seconds format')
    dt.datetime.fromisoformat(authorized.replace('Z','+00:00'))
    deadline=authority.get('global_deadline_utc')
    if deadline is not None:
        if not isinstance(deadline,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',deadline):
            raise ValueError('authority deadline must be null or explicit UTC seconds')
        if dt.datetime.fromisoformat(deadline.replace('Z','+00:00'))<=dt.datetime.now(dt.timezone.utc):
            raise ValueError('authority global deadline already elapsed')
    entries={checked_rel(r['path']):r for r in inventory['files']}
    if len(entries)!=len(inventory['files']):
        raise ValueError('duplicate native inventory paths')
    records={}
    def add(path,digest):
        path=checked_rel(path)
        if not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('missing or invalid SHA256')
        if path.lower() in records and records[path.lower()]['sha256']!=digest:
            raise ValueError(f'conflicting hashes: {path}')
        records[path.lower()]=dict(path=path,sha256=digest)
    manifest=read(args.prepare_manifest)
    if sha(args.prepare_manifest)!=cfg['manifest_sha256']:
        raise ValueError('preparation source manifest differs')
    for item in manifest['files']:
        add(item['path'],item['sha256'])
    for item in entries.values():
        add('native/'+item['path'],item['sha256'])
    # Existing helper MEX bytes must remain exactly the copied snapshot bytes.
    old_binaries={win(r['relative_path']):r['sha256'] for r in snapshot['copied_binaries']}
    runtime=[]
    def bind(name,path):
        r=entries[path];runtime.append(dict(name=name,path=native+'/'+path,sha256=r['sha256']))
    def package(name,extension):
        parts=name.split('.')
        return 'Sources/'+'/'.join('+'+p for p in parts[:-1])+'/'+parts[-1]+extension
    for name in FUNCTIONS:
        bind(name,package(name,'.m'))
    bind('abaqusInpRead','Dependencies/abaqusInpRead.m')
    for name in EXISTING_MEX:
        path=package(name,'.mexw64')
        if entries[path]['sha256']!=old_binaries[path]:
            raise ValueError('existing support MEX changed since the original snapshot')
        bind(name,path)
    runtime.append(dict(name='cholmod2',path=CHOLMOD_PATH,sha256=CHOLMOD_SHA))
    binaries={r['name']:r for r in built['binaries']}
    if set(binaries)!=set(FRESH_MEX):
        raise ValueError('fresh build must contain exactly the reviewed kernel pair')
    for name,qualified in FRESH_MEX.items():
        r=binaries[name]
        if relative(r['path'],cfg['build_root'])!=package(qualified,'.mexw64'):
            raise ValueError('fresh binary path differs from expected package')
        runtime.append(dict(name=qualified,path=win(r['path']),sha256=r['sha256']))
        add(relative(r['path'],root),r['sha256'])
    overlay_name,overlay,overlay_receipt,importer_repair=overlay_support(args.support,root)
    for path,digest in overlay_receipt['files'].items():
        path=checked_rel(path)
        if sha(overlay/path)!=digest:
            raise ValueError('prepared overlay changed')
        add(overlay_name+'/'+path,digest)
        if path.startswith('Sources/'):
            local=Path(__file__).with_name(Path(path).name)
            if sha(local)!=digest:
                raise ValueError('overlay audit helper no longer matches current source')
    add(overlay_name+'/overlay_receipt.json',sha(overlay/'overlay_receipt.json'))
    if importer_repair is not None:
        if entries[IMPORTER_PATH]['sha256']!=IMPORTER_ORIGINAL_SHA:
            raise ValueError('original importer differs from the diagnosed native snapshot')
        matches=[r for r in runtime if r['name']=='specimen.external.abaqus_import']
        if len(matches)!=1 or matches[0]['sha256']!=IMPORTER_ORIGINAL_SHA:
            raise ValueError('original importer runtime binding is not unique/exact')
        matches[0].update(path=root+'/'+overlay_name+'/'+IMPORTER_PATH,sha256=IMPORTER_REPAIRED_SHA)
        add(overlay_name+'/'+IMPORTER_PATH,IMPORTER_REPAIRED_SHA)
    source_checks=[dict(path=r['path'],sha256=r['sha256']) for r in entries.values() if r['path'].endswith(('.m','.f90'))]
    inputs={PureWindowsPath(r['target']).name:r for r in snapshot['inputs']}
    def original_input(name):
        item=inputs[name]
        if relative(item['target'],root)!='inputs/'+name:
            raise ValueError('unexpected staged input path')
        add('inputs/'+name,item['sha256']);return item
    common=original_input('common_common_initial.mat')
    mesh=original_input('mesh_0e6db55abde58802_0e6db55abde58802_native_q4_original.inp')
    pairs=[]
    for cycle in (1,20,60,83):
        old=original_input(f'c{cycle:04d}_s003_post_commit.mat')
        target=original_input(f'c{cycle:04d}_s004_post_commit.mat')
        pairs.append(dict(cycle=cycle,trajectory='S04_E011_FEM_Q4_C120',
            predecessor_path=win(old['target']),predecessor_sha256=old['sha256'],
            target_path=win(target['target']),target_sha256=target['sha256']))
    authority_name=args.label+'_authority.json'
    add(authority_name,sha(args.authority_file))
    output.mkdir(parents=False,exist_ok=False)
    with (output/authority_name).open('xb') as stream:
        stream.write(args.authority_file.read_bytes())
    manifest_name=args.label+'_manifest.json';config_name=args.label+'_config.json';entry_name=args.label+'_entry.m'
    write(output/manifest_name,dict(schema='e036-stage-a-native-source-v1',files=sorted(records.values(),key=lambda x:x['path'])))
    cfg.update(overlay_root=root+'/'+overlay_name,overlay_solver_sha256=overlay_receipt['files']['Scripts/fatigue_fracture/solve_fatigue_fracture.m'],
        build_completion_sha256=sha(args.build_completion),prepare_result_path=win(cfg['output_dir'])+'/prepare_result.json',
        prepare_result_sha256=sha(args.prepare_result),runtime_bindings=runtime,source_checks=source_checks,
        common_file=win(common['target']),common_sha256=common['sha256'],mesh_file=win(mesh['target']),mesh_sha256=mesh['sha256'],
        pairs=pairs,output_dir=root+'/output/'+args.label,watchdog_id=args.label,execution_approved=True,
        authority_file=root+'/'+authority_name,authority_sha256=sha(output/authority_name),
        manifest_path=root+'/'+manifest_name,manifest_sha256=sha(output/manifest_name),
        provenance=dict(scope='same-state Stage A; no acceptance inferred from archive',
            original_native_source_commit=NATIVE_COMMIT,snapshot_receipt_sha256=sha(args.snapshot_receipt),
            inventory_receipt_sha256=sha(args.inventory),prepare_config_sha256=sha(args.prepare_config),
            build_receipt_sha256=sha(args.build_receipt),generator_sha256=sha(__file__),
            overlay_support_sha256=sha(args.support/'support.json'),mesh_importer_repair=importer_repair))
    write(output/config_name,cfg)
    quote=lambda x:"'"+x.replace("'","''")+"'"
    entry='addpath('+quote(win(cfg['code_root'])+'/tools/s04_e036_fem')+",'-begin');\n"
    entry+='e036_stage_a_native_driver('+','.join(map(quote,(root+'/'+config_name,sha(output/config_name),args.mode)))+');\n'
    write(output/entry_name,entry)
    receipt=archive(output,output.name+'.zip');write(output.parent/(output.name+'_receipt.json'),receipt)
    print(json.dumps(receipt,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    first=commands.add_parser('support');first.add_argument('--audited-source-dir',type=Path,required=True)
    first.add_argument('--run-root',required=True);first.add_argument('--output',type=Path,required=True)
    final=commands.add_parser('finalize')
    for name in ('support','inventory','snapshot-receipt','prepare-config','prepare-result','build-receipt','build-completion','prepare-manifest','authority-file','output'):
        final.add_argument('--'+name,type=Path,required=True)
    final.add_argument('--label',required=True);final.add_argument('--mode',choices=MODES,required=True)
    args=parser.parse_args();support(args) if args.command=='support' else finalize(args)


if __name__=='__main__':main()
