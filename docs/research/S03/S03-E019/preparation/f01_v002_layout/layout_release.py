"""F01 V002-L01 layout-only CLI. Real generate/verify/finish require approval.

Standard library only. No numerical arrays, plotting library, font manager or FEM.
Synthetic callers may exercise pure functions without opening any real assets.
"""
import time
START = time.monotonic()
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import threading
import types
import warnings
import xml.etree.ElementTree as ET
import pyexpat

NS = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', NS[1:-1])
REPO = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013')
HERE = Path(__file__).absolute().parent
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01')
OLD, NEW = BASE/'S03-E019-D03-F01-V001', BASE/'S03-E019-D03-F01-V002-L01'
MANIFEST = HERE/'source_manifest.json'
GUARD_PATH = REPO/'scripts/aa2024_runtime_guard.py'
THREADS = ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS')
SOURCE_NAMES = {'residuals.svg','residuals.md','square_ledger.svg','square_ledger.md',
                'runtime_guard_events.log','derived_receipt.json','derived_completion.json',
                'residuals.sidecar_s01.md','square_ledger.sidecar_s01.md','sidecar_mapping_s01.receipt.json'}
PAYLOAD_NAMES = ('residuals.svg','residuals.md','square_ledger.svg','square_ledger.md')
OUTPUT_NAMES = set(PAYLOAD_NAMES)|{'runtime_guard_events.log','layout_receipt.json','layout_completion.json'}
GUIDE = b'## How to read / Visual grammar / Panel guide\n\n'
RELATED = b'Same-directory derived_receipt.json; source files in provenance; no producer receipt recreated.'


class Stop(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Stop(reason)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def strict_json(value):
    def pairs(items):
        out = {}
        for key, item in items:
            need(key not in out, 'duplicate JSON key')
            out[key] = item
        return out
    def bad(value):
        raise Stop('nonfinite JSON '+value)
    return json.loads(value, object_pairs_hook=pairs, parse_constant=bad)


def json_bytes(value):
    return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


class Budget:
    def __init__(self, start=START, clock=time.monotonic, guard=None):
        self.start, self.clock, self.guard = start, clock, guard
    def check(self):
        if self.guard is not None:
            self.guard.check()
        need(self.clock()-self.start < 60, 'soft60s incomplete; no retry')
    def remaining(self):
        self.check()
        return 60-(self.clock()-self.start)


def safe(path, regular=False):
    need(path.is_absolute(), 'absolute path')
    for parent in path.parents:
        need(stat.S_ISDIR(parent.lstat().st_mode), 'symlink/non-directory ancestor '+str(parent))
    need(not path.is_symlink(), 'symlink leaf '+str(path))
    if regular:
        need(stat.S_ISREG(path.lstat().st_mode), 'regular file '+str(path))


def authorize(source, output):
    need(source == OLD and output == NEW, 'exact input/output authority')


def resize(root, width, before, after):
    need(root.get('viewBox') == f'0 0 {width} {before}' and root.get('height') == str(before), 'source canvas')
    bg = [e for e in root if e.tag == NS+'rect' and e.get('x') == '0' and e.get('y') == '0'
          and e.get('fill') == 'white' and e.get('height') == str(before)]
    need(len(bg) == 1, 'one background')
    root.set('viewBox',f'0 0 {width} {after}'); root.set('height',str(after)); bg[0].set('height',str(after))


def residual_layout(source, points=648):
    root = copy.deepcopy(source)
    resize(root,1460,730,820)
    children, moving = list(root), []
    for e in children:
        if e.tag == NS+'circle' and e.get('data-panel','').startswith('1:'):
            moving.append(e)
        elif e.tag == NS+'rect' and e.get('stroke') == '#555555' and float(e.get('y')) > 350:
            moving.append(e)
        elif e.tag == NS+'text' and 377 <= float(e.get('y')) <= 613 and float(e.get('x')) < 1300:
            moving.append(e)
    need(sum(e.tag == NS+'circle' for e in moving) == 4*points, 'V-row point selection')
    need(sum(e.tag == NS+'rect' for e in moving) == 4 and sum(e.tag == NS+'text' for e in moving) == 28, 'V-row frame/label selection')
    first = min(children.index(e) for e in moving)
    group = ET.Element(NS+'g',{'id':'f01-v-row-layout','transform':'translate(0 70)'})
    for e in moving:
        root.remove(e); group.append(e)
    root.insert(first,group)
    footer = [e for e in root if e.tag == NS+'text' and e.get('y') == '695']
    need(len(footer) == 1,'residual footer'); footer[0].set('y','785')
    for e in root:
        if e.tag == NS+'text' and e.get('y') == '665':
            e.set('y','755')
    return root


def ledger_layout(source):
    root = copy.deepcopy(source)
    resize(root,1020,660,720)
    footer = [e for e in root if e.tag == NS+'text' and e.get('y') == '620']
    need(len(footer) == 1,'ledger footer'); footer[0].set('y','690')
    for arm, y in zip(('old','proxy','intact'),('585','607','629')):
        bars = [e for e in root if e.tag == NS+'rect' and e.get('data-arm') == arm and e.get('data-quantity') == 'J_Q_mm2']
        need(len(bars) == 1 and bars[0].get('data-value') is not None,'one saved J_Q bar '+arm)
        label = ET.SubElement(root,NS+'text',{'x':'100','y':y,'font-size':'14','text-anchor':'start',
                             'fill':'#0072B2','data-layout-only':'saved-JQ-label'})
        label.text = arm+': saved J_Q = '+bars[0].get('data-value')+' mm^2 (literal saved value)'
    note = ET.SubElement(root,NS+'text',{'x':'100','y':'660','font-size':'12','text-anchor':'start','data-layout-only':'no-height-inflation'})
    note.text = 'Blue bands retain their original height; labels do not inflate the bars.'
    return root


def parse_svg(value):
    need(b'<!DOCTYPE' not in value.upper() and b'<!ENTITY' not in value.upper(),'XML declarations')
    root = ET.fromstring(value)
    need(root.tag == NS+'svg','SVG root')
    for e in root.iter():
        need(e.tag in {NS+t for t in ('svg','g','title','desc','metadata','rect','text','circle','path')},'SVG tag')
        need(all(not k.lower().startswith('on') and not k.lower().endswith('href') and 'url(' not in v.lower() for k,v in e.attrib.items()),'active/external SVG')
    return root


def companion(value, stem):
    need(value.count(GUIDE) == 1 and value.count(RELATED) == 1,'companion section cardinality')
    note = ('V002-L01 layout-only derivative of the source V001 SVG. The inherited provenance block remains source provenance, not a new numerical run. '
            + ('V row moved down 70 SVG units; canvas height 820. All saved point attributes and colour-scale content unchanged. ' if stem == 'residuals' else
               'Canvas height 720. Blue J_Q bars retain original height; added labels copy the literal saved data-value strings, without scaling or rounding. '))
    related = ('This figure and its same-stem explanation are bound by layout_receipt.json and layout_completion.json in this directory. '
               'Source V001 receipt: '+str(OLD/'derived_receipt.json')+'. Source S01 mapping: '+str(OLD/'sidecar_mapping_s01.receipt.json')+'. '
               'B003 files named in the inherited provenance are referenced only, not reopened; no source producer receipt is recreated.')
    return value.replace(GUIDE,GUIDE+note.encode()+b'\n\n',1).replace(RELATED,related.encode(),1)


def payloads(source, points=648):
    out = {}
    for stem, transform in (('residuals',lambda r:residual_layout(r,points)),('square_ledger',ledger_layout)):
        tree = transform(parse_svg(source[stem+'.svg']))
        ET.SubElement(tree,NS+'metadata',{'id':'f01-layout-source'}).text = json.dumps({
            'kind':'layout_only_derivative_not_new_numerical_run','source_run':OLD.name,
            'source_svg_sha256':sha(source[stem+'.svg']),'layout_run':NEW.name},sort_keys=True)
        out[stem+'.svg'] = ET.tostring(tree,encoding='utf-8')
        out[stem+'.md'] = companion(source[stem+'.sidecar_s01.md'],stem)
    return out


def mapping(source_hashes, outputs):
    return [{'source_svg':str(OLD/(s+'.svg')),'source_svg_sha256':source_hashes[s+'.svg'],
             'source_companion':str(OLD/(s+'.sidecar_s01.md')),'source_companion_sha256':source_hashes[s+'.sidecar_s01.md'],
             'figure':str(NEW/(s+'.svg')),'figure_sha256':sha(outputs[s+'.svg']),
             'sidecar':str(NEW/(s+'.md')),'sidecar_sha256':sha(outputs[s+'.md'])} for s in ('residuals','square_ledger')]


def exclusive_write(path, value, budget, exists=os.path.lexists, opener=open, reader=None):
    budget.check(); need(not exists(path),'output exists; no overwrite')
    with opener(path,'xb') as stream:
        need(stream.write(value) == len(value),'short write')
    if reader is None:
        safe(path,True); reader = lambda p:p.read_bytes()
    need(reader(path) == value,'output readback')
    budget.check()


def read_set(root, names, budget):
    safe(root); need(root.is_dir() and {p.name for p in root.iterdir()} == set(names),'exact directory members')
    data, fingerprints = {}, {}
    for name in sorted(names):
        budget.check(); path = root/name; safe(path,True); before = path.stat()
        data[name] = path.read_bytes(); after = path.lstat()
        key = lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        need(key(before) == key(after) and stat.S_ISREG(after.st_mode),'file changed while reading')
        fingerprints[name] = key(after)
    return data,fingerprints


def match_set(root, data, fingerprints, budget):
    current, current_fp = read_set(root,set(data),budget)
    need(current == data and current_fp == fingerprints,'source/output identity changed')


def git_identity(snapshot, budget):
    def git(*args):
        budget.check()
        return subprocess.check_output(['git',*args],cwd=REPO,text=True,timeout=budget.remaining()).strip()
    need(re.fullmatch('[0-9a-f]{40}',snapshot) is not None,'snapshot hex')
    head = git('rev-parse','HEAD'); need(not git('status','--porcelain'),'clean worktree')
    git('merge-base','--is-ancestor',snapshot,head)
    need(all(p.startswith('docs/') for p in git('diff','--name-only',snapshot,head).splitlines()),'only docs successors')
    return head


def verified_setup(args, budget):
    safe(Path(__file__).absolute(),True)
    need(sha(Path(__file__).read_bytes()) == args.self_sha,'CLI source SHA')
    safe(MANIFEST,True); raw = MANIFEST.read_bytes(); need(sha(raw) == args.manifest_sha,'manifest SHA')
    manifest = strict_json(raw)
    need(manifest['schema'] == 'F01-L01-source-v1' and manifest['source_root'] == str(OLD) and manifest['output_root'] == str(NEW),'manifest authority')
    need(set(manifest['source_sha256']) == SOURCE_NAMES,'manifest ten files')
    code, guard_bytes = {}, None
    for relative, expected in manifest['code_sha256'].items():
        need(relative in ('docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_release.py',
                         'docs/research/S03/S03-E019/preparation/f01_v002_layout/test_layout_release.py',
                         'docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_draft.py',
                         'scripts/aa2024_saved_svg.py',
                         'scripts/aa2024_runtime_guard.py'),'code whitelist')
        path = REPO/relative; safe(path,True); value = path.read_bytes(); code[relative] = sha(value); need(code[relative] == expected,'code SHA '+relative)
        if path == GUARD_PATH:
            guard_bytes = value
    need(len(code) == 5 and guard_bytes is not None and code[str(Path(__file__).relative_to(REPO))] == args.self_sha,'five code identities')
    return manifest,code,raw,guard_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('generate','verify','finish'),required=True)
    parser.add_argument('--manifest-sha',required=True); parser.add_argument('--self-sha',required=True)
    parser.add_argument('--snapshot',required=True)
    args = parser.parse_args()
    warnings.simplefilter('error')
    need(all(os.environ.get(k) == '1' for k in THREADS) and os.environ.get('CUDA_VISIBLE_DEVICES') == '','single CPU environment')
    need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,'Python flags')
    budget = Budget(); setup = verified_setup(args,budget)
    manifest,code,manifest_bytes,guard_bytes = setup
    guard_module = types.ModuleType('f01_existing_g01')
    guard_module.__file__ = str(GUARD_PATH)
    exec(compile(guard_bytes,str(GUARD_PATH),'exec'),guard_module.__dict__)
    guard = guard_module.install_cli(); budget.guard = guard
    authorize(OLD,NEW); initial_head = git_identity(args.snapshot,budget)
    if args.mode == 'generate':
        safe(NEW); need(not os.path.lexists(NEW),'fresh output directory before source access')
    source, source_fp = read_set(OLD,SOURCE_NAMES,budget)
    source_hashes = {n:sha(v) for n,v in source.items()}
    need(source_hashes == manifest['source_sha256'],'ten frozen source hashes')
    expected = payloads(source)
    expected_map = mapping(source_hashes,expected)
    if args.mode == 'generate':
        safe(NEW); need(not os.path.lexists(NEW),'fresh output directory')
        budget.check(); NEW.mkdir(mode=0o700,exist_ok=False); guard.bind_events(NEW)
        for name in PAYLOAD_NAMES:
            exclusive_write(NEW/name,expected[name],budget)
        match_set(OLD,source,source_fp,budget)
        need(git_identity(args.snapshot,budget) == initial_head,'runtime HEAD changed')
        assets = {n:sha((NEW/n).read_bytes()) for n in (*PAYLOAD_NAMES,'runtime_guard_events.log')}
        need(assets['runtime_guard_events.log'] == sha(b''),'empty guard event')
        receipt = {'schema':'F01-L01-layout-v1','status':'layout_generated_pending_independent_semantic_and_visual_acceptance',
                   'source_root':str(OLD),'output_root':str(NEW),'source_sha256':source_hashes,
                   'code_sha256':code,'source_manifest_sha256':sha(manifest_bytes),'runtime_head':initial_head,
                   'snapshot':args.snapshot,'mapping':expected_map,'artifacts_sha256':assets,
                   'runtime_guard':guard.receipt_state(),'thread_env':{k:os.environ[k] for k in THREADS},
                   'hostname':socket.gethostname(),'pid':os.getpid(),'command':sys.argv,
                   'actual_svd':0,'actual_qr':0,'scientific_recomputation':False,
                   'source_status':'incomplete_unaccepted_synthetic','visual_acceptance':False,
                   'elapsed_before_receipt':time.monotonic()-START}
        exclusive_write(NEW/'layout_receipt.json',json_bytes(receipt),budget)
        match_set(OLD,source,source_fp,budget)
        exclusive_write(NEW/'layout_completion.json',json_bytes({'layout_receipt_sha256':sha(json_bytes(receipt))}),budget)
        final, final_fp = read_set(NEW,OUTPUT_NAMES,budget)
        need(all(final[n] == expected[n] for n in PAYLOAD_NAMES) and final['runtime_guard_events.log'] == b'' and
             final['layout_receipt.json'] == json_bytes(receipt) and strict_json(final['layout_completion.json']) ==
             {'layout_receipt_sha256':sha(final['layout_receipt.json'])},'final generated payload/receipt identity')
        match_set(OLD,source,source_fp,budget)
        need(git_identity(args.snapshot,budget) == initial_head,'final HEAD changed')
        guard.check('generated_stdout')
        print(json.dumps({'status':'LAYOUT_GENERATED_NOT_ACCEPTED','elapsed_before_print':time.monotonic()-START}),flush=True)
    else:
        derived, derived_fp = read_set(NEW,OUTPUT_NAMES,budget)
        for name in PAYLOAD_NAMES:
            need(derived[name] == expected[name],'only approved layout/sidecar changes '+name)
        receipt = strict_json(derived['layout_receipt.json'])
        need(strict_json(derived['layout_completion.json']) == {'layout_receipt_sha256':sha(derived['layout_receipt.json'])},'completion binding')
        need(receipt['schema'] == 'F01-L01-layout-v1' and receipt['status'] == 'layout_generated_pending_independent_semantic_and_visual_acceptance','receipt identity')
        need(receipt['source_root'] == str(OLD) and receipt['output_root'] == str(NEW) and receipt['source_sha256'] == source_hashes,'source mapping')
        need(receipt['code_sha256'] == code and receipt['source_manifest_sha256'] == sha(manifest_bytes) and receipt['snapshot'] == args.snapshot,'code/manifest identity')
        need(re.fullmatch('[0-9a-f]{40}',receipt['runtime_head']) is not None,'saved HEAD')
        subprocess.check_call(['git','merge-base','--is-ancestor',receipt['runtime_head'],initial_head],cwd=REPO,timeout=budget.remaining())
        need(receipt['mapping'] == expected_map and receipt['artifacts_sha256'] == {n:sha(derived[n]) for n in (*PAYLOAD_NAMES,'runtime_guard_events.log')},'payload/mapping hashes')
        need(derived['runtime_guard_events.log'] == b'' and receipt['runtime_guard']['healthy'] is True and receipt['runtime_guard']['fatal_seen'] is False,'generation guard')
        need(receipt['actual_svd'] == 0 and receipt['actual_qr'] == 0 and receipt['scientific_recomputation'] is False and receipt['visual_acceptance'] is False and receipt['source_status'] == 'incomplete_unaccepted_synthetic','claim boundary')
        need(receipt['thread_env'] == {k:'1' for k in THREADS},'generation thread environment')
        if args.mode == 'verify':
            for name in ('residuals.md','square_ledger.md'):
                print('SIDECAR '+name+' BEGIN\n'+derived[name].decode()+'\nSIDECAR '+name+' END')
        match_set(OLD,source,source_fp,budget); match_set(NEW,derived,derived_fp,budget)
        need(git_identity(args.snapshot,budget) == initial_head,'review HEAD changed')
        print(json.dumps({'status':'PENDING_REAL_VISUAL_QA' if args.mode == 'verify' else 'FINAL_IDENTITY_ONLY_NOT_VISUAL_VERDICT',
                          'sha256':{n:sha(v) for n,v in derived.items()},'runtime_head':initial_head,
                          'elapsed_before_print':time.monotonic()-START}),flush=True)
    need(verified_setup(args,budget) == setup,'final code/manifest identity')
    budget.check(); guard.check('stdout_done')


if __name__ == '__main__':
    main()
