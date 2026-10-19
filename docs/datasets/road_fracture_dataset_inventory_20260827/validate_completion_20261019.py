"""Read-only checks for ID coverage, recovery identity, archive links and sample provenance."""
import csv
import hashlib
import json
from pathlib import Path
import re

BASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
HERE=Path(__file__).resolve().parent
VAULT=Path('/Users/wenxiaofang/obsidian')
RAW=BASE/'local_archive/open_data/dataset_completion_20261019'

def main():
    details=json.loads((HERE/'completion_details_20261019.json').read_text())
    with (HERE/'dataset_inventory.csv').open(newline='') as f: original=list(csv.DictReader(f))
    with (HERE/'dataset_hq_crosswalk_20261019.csv').open(newline='') as f: current=list(csv.DictReader(f))
    assert len(original)==len(details)==len(current)==18
    assert [r['dataset_id'] for r in original]==[r['dataset_id'] for r in current]
    source=json.loads((RAW/'source_receipts.json').read_text())
    assert set(r['dataset_id'] for r in source)==set(details)
    result={'date':'2026-10-19','ids_in_order':18,'notes':0,'official_snapshots':0,'missing_links':[], 'ambiguous_basenames':[], 'historical_files_match':{}, 'image_embeds':0}
    roadmap=(VAULT/'01 Research Tracks/000 research note/Road crack prediction/0 Roadmap.md').read_text()
    basenames={}
    for p in VAULT.rglob('*.md'): basenames.setdefault(p.name,[]).append(str(p))
    for k,d in details.items():
        p=VAULT/d['note']; s=p.read_text(); marker=f'## 2026-10-19 统一资料复核（`{k}`）'
        assert s.count(marker)==1,k
        section=s[s.index(marker):]
        assert all(label in section for label in ['元数据字段','文件格式与体量','本地资产和样本','缺口与下一决定']),k
        assert f'[[{p.stem}]]' in roadmap,k
        result['notes']+=1
        if len(basenames.get(p.name,[]))!=1: result['ambiguous_basenames'].append(p.name)
        for target in re.findall(r'\]\(<([^>]+)>\)',section):
            if target.startswith('/') and not Path(target).exists(): result['missing_links'].append(target)
        for embed in re.findall(r'!\[\[([^]|]+)',section):
            matches=list(VAULT.rglob(Path(embed).name))
            assert len(matches)==1,embed
            result['image_embeds']+=1
        assert any((RAW/k).glob('official_metadata.*')),k
        result['official_snapshots']+=1
    for f in ['dataset_inventory.csv','route_test_audit.csv','report-source.md']:
        canonical=BASE/'upload code/docs/datasets/road_fracture_dataset_inventory_20260827'/f
        assert canonical.read_bytes()==(HERE/f).read_bytes(),f
        result['historical_files_match'][f]=True
    for rec in json.loads((RAW/'patch_sample_receipts.json').read_text()):
        if rec['dataset_id']=='multitemporal_concrete':
            split=json.loads((RAW/'multitemporal_concrete/train_val_test_split.json').read_text())
            assert '0000' in split['train']
            assert len(rec['samples'])==2
            assert all(s['zip_crc_checked'] and Path(s['file']).exists() for s in rec['samples'])
            result['new_raw_sample_pairs']=1
    assert not result['missing_links'] and not result['ambiguous_basenames']
    result['scientific_qualification']='not upgraded by documentation checks'
    result['new_model_experiments']=0
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
