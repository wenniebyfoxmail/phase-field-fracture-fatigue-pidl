#!/usr/bin/env python3
"""Preserve only our verified D01 files from a colliding shared archive."""
import json
from pathlib import Path
import shutil

from d01_directional_scale_repeatability import crc32_file

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments')
SOURCE=ROOT/'S03-E011/runs/S03-E011-R001'
TARGET=ROOT/'S03-E012-D01'
if TARGET.exists():
    raise FileExistsError('fresh canonical archive required')
acquisition=json.loads((SOURCE/'acquisition_receipt.json').read_text())
selection=json.loads((SOURCE/'selected_sequences_before_pixel_access.json').read_text())
if len(acquisition)!=14 or sorted(len(x) for x in selection['groups'].values())!=[4,4,6]:
    raise ValueError('D01 selection identity mismatch')
lookup={r['saved_as']:r['entry'] for rows in selection['groups'].values() for r in rows}
for item in acquisition:
    relative=item['saved_as']
    entry=lookup[relative]
    path=SOURCE/'raw_images'/relative
    if path.stat().st_size!=entry['uncompressed_bytes'] or crc32_file(path)!=entry['crc32']:
        raise ValueError(f'D01 file changed: {path}')
    target=TARGET/'acquired_sources'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)
failed=TARGET/'failed_initial_launch'
failed.mkdir(parents=True)
for name in ('acquisition_receipt.json','selected_sequences_before_pixel_access.json'):
    shutil.copy2(SOURCE/name,failed/name)
receipt=json.loads((SOURCE/'run_receipt.json').read_text())
if receipt['commit']!='280764509ad610aa815faff64c48d503b60367ff' or receipt['pid']!=73507:
    raise ValueError('initial receipt no longer identifies our failed launch')
receipt.update(execution='failed',retrieval='verified_inputs_only',
               failure='NameError: warp_image import missing; no forecast scores produced',
               canonical_successor_experiment='S03-E012-D01',
               foreign_payload_excluded='data_audit.json (342-stage empirical headers, not D01)')
(failed/'run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Preserved 14 verified D01 sources and failed launch metadata; shared archive untouched')
