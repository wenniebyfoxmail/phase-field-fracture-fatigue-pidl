"""UNEXECUTED F01 layout draft. No output/writer/generation CLI.

Transformation functions are proposed XML-layout edits, not a numerical producer.
The only CLI is a future read-only comparison against separately approved files.
"""
import time
STARTED = time.monotonic()
import argparse
import copy
import hashlib
import json
import logging
import os
from pathlib import Path
import stat
import sys
import warnings
import xml.etree.ElementTree as ET
import pyexpat

NS = '{http://www.w3.org/2000/svg}'
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01')
OLD = BASE/'S03-E019-D03-F01-V001'
NEW = BASE/'S03-E019-D03-F01-V002-L01'
SOURCE_SHA = {'residuals.svg':'8228c9b7b8e2f247f0ce9fb764c5ea9863be2b96a4eb3cbf8add39803b07893f',
              'square_ledger.svg':'210aeb0aaa3ea03a51c6cd6a0575ed223f62828044e212ec69a5c8cd6a7772a5'}


def need(ok, reason):
    if not ok:
        raise RuntimeError('STOP_F01_LAYOUT_DRAFT_NO_RETRY: '+reason)


def resize(root, width, before, after):
    need(root.get('viewBox') == f'0 0 {width} {before}' and root.get('height') == str(before), 'source canvas')
    backgrounds = [e for e in root if e.tag == NS+'rect' and e.get('x') == '0' and e.get('y') == '0'
                   and e.get('fill') == 'white' and e.get('height') == str(before)]
    need(len(backgrounds) == 1, 'one source background')
    root.set('viewBox', f'0 0 {width} {after}')
    root.set('height', str(after))
    backgrounds[0].set('height', str(after))


def proposed_residual(source):
    """Copy only; V-row group translation leaves all point attributes untouched."""
    root = copy.deepcopy(source)
    resize(root, 1460, 730, 820)
    children = list(root)
    moving = []
    for e in children:
        if e.tag == NS+'circle' and e.get('data-panel', '').startswith('1:'):
            moving.append(e)
        elif e.tag == NS+'rect' and e.get('stroke') == '#555555' and float(e.get('y')) > 350:
            moving.append(e)
        elif e.tag == NS+'text' and 377 <= float(e.get('y')) <= 613 and float(e.get('x')) < 1300:
            moving.append(e)
    need(sum(e.tag == NS+'circle' for e in moving) == 2592, 'V-row moving point scope')
    need(sum(e.tag == NS+'rect' for e in moving) == 4, 'V-row moving frames')
    need(sum(e.tag == NS+'text' for e in moving) == 28, 'V-row moving labels')
    index = min(children.index(e) for e in moving)
    group = ET.Element(NS+'g', {'id':'f01-v-row-layout', 'transform':'translate(0 70)'})
    for e in moving:
        root.remove(e)
        group.append(e)
    root.insert(index, group)
    footer = [e for e in root if e.tag == NS+'text' and e.get('y') == '695']
    need(len(footer) == 1, 'one residual footer')
    footer[0].set('y', '785')
    for e in root:
        if e.tag == NS+'text' and e.get('y') == '665':
            e.set('y', '755')
    return root


def proposed_ledger(source):
    """Preserve every bar/dot; copy saved literal J_Q strings into labels."""
    root = copy.deepcopy(source)
    resize(root, 1020, 660, 720)
    footer = [e for e in root if e.tag == NS+'text' and e.get('y') == '620']
    need(len(footer) == 1, 'one ledger footer')
    footer[0].set('y', '690')
    for arm, y in zip(('old','proxy','intact'), ('585','607','629')):
        bars = [e for e in root if e.tag == NS+'rect' and e.get('data-arm') == arm
                and e.get('data-quantity') == 'J_Q_mm2']
        need(len(bars) == 1, 'one unchanged saved J_Q bar '+arm)
        label = ET.SubElement(root, NS+'text', {'x':'100','y':y,'font-size':'14',
                              'text-anchor':'start','fill':'#0072B2','data-layout-only':'saved-JQ-label'})
        label.text = arm+': saved J_Q = '+bars[0].get('data-value')+' mm^2 (literal saved value)'
    note = ET.SubElement(root, NS+'text', {'x':'100','y':'660','font-size':'12',
                         'text-anchor':'start','data-layout-only':'no-height-inflation'})
    note.text = 'Blue bands retain their original height; labels do not inflate the bars.'
    return root


def signature(element):
    return (element.tag, tuple(sorted(element.attrib.items())), element.text, element.tail,
            tuple(signature(child) for child in element))


def check_only():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', required=True)
    parser.parse_args()
    warnings.simplefilter('error')
    factory = logging.getLogRecordFactory()
    def log_factory(*args, **kwargs):
        need(type(args[1]) is int and args[1] < logging.WARNING, 'logging warning/error')
        return factory(*args, **kwargs)
    logging.setLogRecordFactory(log_factory)
    def budget():
        need(time.monotonic()-STARTED < 60, 'soft60s exceeded')
    threads = ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
               'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS')
    need(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and all(os.environ.get(k) == '1' for k in threads), 'single CPU environment')
    paths = [directory/name for directory in (OLD, NEW) for name in SOURCE_SHA]
    allowed = {str(p) for p in paths}
    for path in paths:
        for parent in path.parents:
            need(stat.S_ISDIR(parent.lstat().st_mode), 'directory/symlink '+str(parent))
        need(stat.S_ISREG(path.lstat().st_mode), 'regular non-symlink '+str(path))
    def audit(event, args):
        if event == 'open':
            p, mode, flags = args
            need(isinstance(p, (str,bytes,os.PathLike)) and os.fsdecode(p) in allowed, 'open outside four SVGs')
            need(not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND), 'writes forbidden')
        need(not event.startswith(('subprocess.','socket.')) and event not in ('os.system','os.mkdir','os.remove','os.rename','os.rmdir','os.link','os.symlink'), 'side effect '+event)
        if event == 'import':
            need(args[0].split('.')[0] not in ('numpy','scipy','matplotlib') and not args[0].startswith('aa2024_'), 'forbidden import')
    sys.addaudithook(audit)
    raw, before = {}, {}
    for path in paths:
        budget()
        before[path] = path.stat()
        raw[path] = path.read_bytes()
        need(b'<!DOCTYPE' not in raw[path].upper() and b'<!ENTITY' not in raw[path].upper(), 'XML declarations')
    result = {}
    for name, transform in (('residuals.svg', proposed_residual), ('square_ledger.svg', proposed_ledger)):
        need(hashlib.sha256(raw[OLD/name]).hexdigest() == SOURCE_SHA[name], 'frozen source SHA '+name)
        source = ET.fromstring(raw[OLD/name])
        candidate = ET.fromstring(raw[NEW/name])
        need(signature(candidate) == signature(transform(source)), 'only proposed layout edits '+name)
        result[name] = hashlib.sha256(raw[NEW/name]).hexdigest()
    for path in paths:
        budget()
        after = path.lstat()
        need(stat.S_ISREG(after.st_mode) and (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) ==
             (before[path].st_dev,before[path].st_ino,before[path].st_size,before[path].st_mtime_ns)
             and path.read_bytes() == raw[path], 'file changed '+str(path))
    budget()
    print(json.dumps({'status':'PENDING_LAYOUT_VISUAL_QA_ONLY','candidate_sha256':result,
                      'original_sha256':SOURCE_SHA,'actual_svd':0,'actual_qr':0,
                      'elapsed_before_print':time.monotonic()-STARTED},sort_keys=True),flush=True)
    budget()


if __name__ == '__main__':
    check_only()
