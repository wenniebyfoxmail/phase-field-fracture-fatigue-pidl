"""Read-only D1 inventory and contract preflight; performs no model fitting."""
import argparse, json, zipfile
from pathlib import Path
import runner

def zip_inventory(path, split, excluded):
    with zipfile.ZipFile(path) as z:
        names=[Path(n) for n in z.namelist() if not n.endswith('/')]
    jpg={p.stem for p in names if p.suffix.lower()=='.jpg'};png={p.stem for p in names if p.suffix.lower()=='.png'}
    stems=sorted(s for s in jpg if (s+'_mask' in png)) if split=='testdata' else sorted(jpg & png)
    if split!='testdata': stems=[s for s in stems if runner.parent_id(s) not in excluded]
    groups={s if split=='testdata' else runner.parent_id(s) for s in stems}
    return len(stems),len(groups)

def main():
    p=argparse.ArgumentParser();p.add_argument('--trainzip',required=True);p.add_argument('--valzip',required=True);p.add_argument('--testzip',required=True);p.add_argument('--cfd',required=True);a=p.parse_args()
    lock=json.loads((Path(__file__).parent/'data_lock.json').read_text());checks={}
    for key,path in [('trainzip',a.trainzip),('valzip',a.valzip),('testzip',a.testzip)]:checks[key+'_sha256']=runner.sha256(path)==lock[key]['sha256']
    checks['train_inventory']=zip_inventory(a.trainzip,'traincrop',set(runner.PROTOCOL['crack500_excluded_train_parents']))==(1860,245)
    checks['val_inventory']=zip_inventory(a.valzip,'valcrop',set(runner.PROTOCOL['crack500_excluded_val_parents']))==(341,49)
    checks['test_inventory']=zip_inventory(a.testzip,'testdata',set())==(200,200)
    checks['cfd_lock']=runner.cfd_lock(Path(a.cfd))==lock['cfd_lock']
    checks['no_road420_cli']='road420' not in runner.main.__code__.co_varnames
    print(json.dumps(checks,indent=2));raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
