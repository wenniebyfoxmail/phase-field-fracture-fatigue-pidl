"""E028 production-only frozen spatial qualification; never connects a selector."""
import time
START=time.monotonic()
import argparse,hashlib,importlib.util,io,json,ntpath,os,shutil,sys,threading
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


source=module('e028_reviewed_e027',ROOT/'scripts/pavetrack_spatial_source/run.py')
geom=module('e028_geometry',Path(__file__).with_name('geometry.py'))
metrics=module('e028_metrics',Path(__file__).with_name('evaluate.py'))
sha=source.sha;write=source.write


class Guard:
    def __init__(self,cfg,out,memory=None):
        self.cfg,self.out=cfg,out;self.counts=dict(source_image_decodes=0,native_tiles=0,cached_forwards=0)
        self.rss=self.allocated=self.reserved=0;self.gpu=lambda:(0,0)
        if memory is None:
            import psutil
            process=psutil.Process()
            def memory():
                own=[process]+process.children(recursive=True)+[p for p in process.parents() if p.name().lower().startswith('python')]
                return sum(getattr(p.memory_info(),'peak_wset',p.memory_info().rss) for p in own)
        self.memory=memory
    def take(self,key):
        self.counts[key]+=1
        cap=self.cfg['budget']['source_image_decodes'] if key=='source_image_decodes' else self.cfg['counts'][key]
        if self.counts[key]>cap:raise RuntimeError('counter cap '+key)
        if sum(self.counts.values())%32==0:self.check()
        if sum(self.counts.values())%128==0:write(self.out/'progress.json',dict(counts=self.counts.copy(),elapsed_seconds=time.monotonic()-START))
    def check(self):
        self.rss=max(self.rss,int(self.memory()));a,r=self.gpu();self.allocated=max(self.allocated,int(a));self.reserved=max(self.reserved,int(r))
        b=self.cfg['budget']
        if time.monotonic()-START>b['wall_seconds']:raise TimeoutError('3600s wall cap')
        if self.rss>b['RSS_bytes'] or self.allocated>b['GPU_allocated_bytes'] or self.reserved>b['GPU_reserved_bytes']:raise MemoryError('4GiB memory cap')
        if sum(p.stat().st_size for p in self.out.rglob('*') if p.is_file())>b['output_bytes']:raise RuntimeError('6GiB output cap')
    def receipt(self):
        return dict(elapsed_seconds=time.monotonic()-START,peak_RSS_bytes=self.rss,peak_GPU_allocated_bytes=self.allocated,peak_GPU_reserved_bytes=self.reserved,counts=self.counts,model_fits=0,updates=0,E003_loaded=False,selector=False,OOF=None)


def validate_config(cfg):
    expected=dict(contexts=12238,images=338,pixels=700876800,native_tiles=13520,cached_forwards=12238,total_forwards=25758)
    budget=dict(wall_seconds=3600,RSS_bytes=4*1024**3,GPU_allocated_bytes=4*1024**3,GPU_reserved_bytes=4*1024**3,output_bytes=6*1024**3,archive_bytes=6*1024**3,minimum_free_disk_bytes=16*1024**3,source_image_decodes=338,models=1,model_fits=0,updates=0,selector=False,OOF=False)
    if cfg['protocol']!='S01-E028-v1' or cfg['run_id']!='S01-E028-R001' or cfg['counts']!=expected or cfg['budget']!=budget:raise ValueError('frozen identity/count/budget')
    if cfg['sites']!=['24','1638','2027'] or cfg['qual_locations']!=[['1638','2027'],['24','2027'],['24','1638']]:raise ValueError('frozen site pairs')
    if cfg['candidate']!=dict(input='native_image',pool='max',reference='any') or cfg['threshold']!=.5 or cfg['margin']!=1e-6 or cfg['private_inputs']!=9:raise ValueError('candidate/criteria')
    if cfg['tile']!=dict(input=512,stride=256,halo=128,padding='reflect',batch=1):raise ValueError('frozen tile')
    if cfg['checkpoint']!=json.loads((ROOT/'docs/research/S01/S01-E027/run_config.json').read_text())['checkpoint']:raise ValueError('fixed E027 source')


def validate_scope(scope,identities,contexts,extraction,cfg):
    rows=scope['rows'];images=scope['images'];sites=cfg['sites']
    wanted=[i for i,r in enumerate(identities['rows']) if r['location'] in sites]
    if [r['index'] for r in rows]!=wanted or len(set(wanted))!=len(rows):raise ValueError('scope exact candidate indices')
    expected_images={k:v for k,v in extraction['images'].items() if v['location'] in sites}
    if images!=expected_images or len(images)!=cfg['counts']['images'] or len(rows)!=cfg['counts']['contexts']:raise ValueError('scope exact image inventory')
    for row in rows:
        r=identities['rows'][row['index']]
        if row['image_id']!=r['image_id'] or row['location']!=r['location'] or row['context']!=contexts['rows'][row['index']]:raise ValueError('scope row identity')
        if any(images[row['image_id']][k]!=r[k] for k in ['prepared_image','prepared_image_sha256','width','height','location']):raise ValueError('image source identity')
        x1,y1,x2,y2=row['context'];im=images[row['image_id']]
        if not all(isinstance(v,int) for v in row['context']) or not (0<=x1<x2<=im['width'] and 0<=y1<y2<=im['height']):raise ValueError('integer context geometry')
    cases=[]
    for loc in sites:
        ims=sorted(im for im,rec in images.items() if rec['location']==loc)
        for im in [ims[0],ims[-1]]:cases.append(min(r['index'] for r in rows if r['image_id']==im))
    if scope['cases']!=cases:raise ValueError('fixed case selection')
    if sum(v['width']*v['height'] for v in images.values())!=cfg['counts']['pixels'] or sum(((v['width']+255)//256)*((v['height']+255)//256) for v in images.values())!=cfg['counts']['native_tiles']:raise ValueError('native pixel/tile counts')


def execute_predictions(scope,cache,out,engine,guard,decode):
    (out/'native').mkdir();(out/'cases').mkdir()
    n=len(scope['rows']);a=np.lib.format.open_memmap(out/'cached_pass0.npy',mode='w+',dtype=np.float32,shape=(n,128,128))
    for j,row in enumerate(scope['rows']):
        guard.take('cached_forwards');a[j]=engine.predict(np.asarray(cache[row['index']]));geom.validate_probability(a[j],(128,128))
    a.flush();del a
    for k,im in enumerate(sorted(scope['images'])):
        rec=scope['images'][im];guard.take('source_image_decodes');rgb=decode(rec)
        if rgb.shape!=(3,rec['height'],rec['width']) or rgb.dtype!=np.uint8:raise ValueError('decoded native image')
        p=geom.native_predict(rgb,engine.predict,guard.take);np.save(out/f'native/{k:04d}.npy',p)
        for row in scope['rows']:
            if row['image_id']==im and row['index'] in scope['cases']:
                x1,y1,x2,y2=row['context'];np.save(out/f'cases/{row["index"]}_rgb.npy',rgb[:,y1:y2,x1:x2])
        del rgb,p;guard.check()
    digest=engine.verify_unchanged()
    write(out/'prediction_freeze.json',dict(files={str(p.relative_to(out)).replace(os.sep,'/'):sha(p) for p in out.rglob('*.npy')},state_digest=digest,counts=guard.counts.copy(),all_predictions_before_reference_decode=True,model_fits=0,updates=0))


def load_references(inp,scope,out):
    if not (out/'prediction_freeze.json').exists():raise PermissionError('references before all predictions freeze')
    if json.loads((out/'prediction_freeze.json').read_text()).get('all_predictions_before_reference_decode') is not True:raise PermissionError('invalid prediction barrier')
    from PIL import Image,ImageDraw,__version__
    if __version__!='12.3.0':raise ValueError('pinned polygon raster Pillow12.3.0')
    annotations=json.loads((inp/'annotations.json').read_text());by={im:[] for im in scope['images']}
    if len(annotations['rows'])!=850:raise ValueError('old annotation container identity')
    for r in annotations['rows']:
        im=r['image_id']
        if im not in by:continue
        rec=scope['images'][im]
        if any(r[k]!=rec[k] for k in ['location','width','height']):raise ValueError('reference image identity')
        if r['category'] not in ['Alligator Crack','Transverse Crack','Patch','Pothole']:raise ValueError('reference class')
        by[im].append(r)
    with np.load(inp/'legacy_center.npz',allow_pickle=False) as z:
        if str(z['source_run'])!='S01-E025-R001' or z['row_indices'].dtype!=np.int64 or not np.array_equal(z['row_indices'],[r['index'] for r in scope['rows']]):raise ValueError('legacy row identity')
        legacy=z['masks']
    if legacy.shape!=(len(scope['rows']),32,32) or legacy.dtype!=np.uint8:raise ValueError('legacy center shape/dtype')
    n=len(scope['rows']);refs={key:np.empty((n,32,32),np.float32 if key=='area' else np.uint8) for key in ['center','any','area']}
    for im,rec in scope['images'].items():
        if not by[im]:raise ValueError('missing reference rows')
        mask=Image.new('L',(rec['width'],rec['height']),0);draw=ImageDraw.Draw(mask)
        for r in by[im]:
            if r['category'] in ['Alligator Crack','Transverse Crack']:
                pts=np.asarray(r['polygon'],dtype=float)
                if pts.ndim!=2 or pts.shape[1]!=2 or len(pts)<3 or not np.isfinite(pts).all() or (pts<0).any() or (pts[:,0]>rec['width']).any() or (pts[:,1]>rec['height']).any():raise ValueError('reference polygon')
                draw.polygon([tuple(p) for p in pts],fill=1)
        arr=np.asarray(mask,dtype=np.uint8)
        for j,row in enumerate(scope['rows']):
            if row['image_id']==im:
                center,any_,area=geom.reference(arr,row['context'])
                if not np.array_equal(center,legacy[j]):raise ValueError('old E025 center reference mismatch')
                refs['center'][j]=center;refs['any'][j]=any_;refs['area'][j]=area
        mask.close()
    return refs


def projections(scope,out):
    n=len(scope['rows']);maps={key:np.empty((n,32,32),np.float32) for key in ['cached_mean','cached_max','native_mean','native_max']}
    cached=np.load(out/'cached_pass0.npy',mmap_mode='r')
    for j in range(n):
        grid=cached[j].reshape(32,4,32,4)
        maps['cached_mean'][j]=grid.mean((1,3));maps['cached_max'][j]=grid.max((1,3))
    for k,im in enumerate(sorted(scope['images'])):
        field=np.load(out/f'native/{k:04d}.npy',mmap_mode='r')
        for j,row in enumerate(scope['rows']):
            if row['image_id']==im:maps['native_mean'][j],maps['native_max'][j]=geom.reduce(field,row['context'])
    return maps


def finish_evaluation(scope,out,cfg,reference_loader):
    if not (out/'prediction_freeze.json').exists():raise PermissionError('prediction barrier')
    freeze=json.loads((out/'prediction_freeze.json').read_text())
    if freeze.get('all_predictions_before_reference_decode') is not True:raise PermissionError('invalid prediction freeze')
    for name,digest in freeze['files'].items():
        if sha(out/name)!=digest:raise ValueError('prediction changed before references '+name)
    refs=reference_loader();maps=projections(scope,out)
    np.savez(out/'references.npz',**refs);np.savez(out/'projections.npz',**maps)
    support=[]
    for site in cfg['sites']:
        ids=[j for j,row in enumerate(scope['rows']) if row['location']==site]
        for name,field in {**maps,**{f'reference_{k}':refs[k] for k in ['center','any']}}.items():
            support.append(dict(site=site,field=name,total_contexts=len(ids),nonempty_contexts=int((field[ids]>=.5).any((1,2)).sum())))
    write(out/'support_summary.json',dict(rows=support,meaning='fixed.5 response or envelope-presence counts, not crack pixel truth'))
    result=metrics.compare(maps,refs,scope['rows'],cfg);write(out/'result.json',result)
    return result



def path_auditor(scope,run):
    normalize=lambda p:ntpath.normcase(ntpath.abspath(os.fsdecode(p)))
    allowed={normalize(r['prepared_image']) for r in scope['images'].values()}
    own=normalize(str(run)).rstrip('\\')+'\\'
    def audit(event,values):
        if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
            p=normalize(values[0])
            if '\\pavetrack_runs\\' in p and not p.startswith(own) and p not in allowed:
                raise PermissionError('unscoped old run/source/holdout')
    return audit

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--reviewed-commit',required=True);parser.add_argument('--manifest-sha256',required=True);args=parser.parse_args()
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());validate_config(cfg)
    source.prior.runtime.production_environment(cfg) # Producer check precedes torch/data/model use.
    manifest=ROOT/'docs/research/S01/S01-E028/source_manifest.json'
    if sha(manifest)!=args.manifest_sha256:raise ValueError('manifest identity')
    for n,h in json.loads(manifest.read_text())['files'].items():
        if sha(ROOT/n)!=h:raise ValueError('source binding '+n)
    if str(args.run.resolve()).casefold()!=r'C:\Users\xw436\pavetrack_runs\S01-E028-R001'.casefold():raise ValueError('fixed fresh run')
    if shutil.disk_usage(args.run.parent).free<cfg['budget']['minimum_free_disk_bytes']:raise OSError('16GiB free disk required')
    lock=json.loads((ROOT/'docs/research/S01/S01-E028/data_lock.json').read_text())
    if len(lock['files'])!=cfg['private_inputs']:raise ValueError('frozen private input count')
    if set(p.name for p in args.input.iterdir())!=set(lock['files']):raise ValueError('nine input inventory')
    for n,r in lock['files'].items():
        p=args.input/n
        if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('input identity '+n)
    scope=json.loads((args.input/'scope.json').read_text());validate_scope(scope,*[json.loads((args.input/n).read_text()) for n in ['candidate_identity.json','pixel_contexts.json','spatial_extraction_receipt.json']],cfg)
    args.run.mkdir(parents=True,exist_ok=False);guard=Guard(cfg,args.run);stop=threading.Event()
    def watchdog():
        while not stop.wait(.25):
            if time.monotonic()-START>3600 or guard.memory()>4*1024**3:
                write(args.run/'watchdog_stop.json',dict(reason='wall/RSS cap',counts=guard.counts.copy(),elapsed_seconds=time.monotonic()-START));os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    sys.addaudithook(path_auditor(scope,args.run))
    try:
        import PIL
        if PIL.__version__!='12.3.0':raise ValueError('Pillow12.3.0 required')
        t,identity=source.prior.production_checks(cfg,guard);engine=source.Engine(t,cfg,args.input)
        write(args.run/'launch.json',dict(reviewed_commit=args.reviewed_commit,manifest_sha256=args.manifest_sha256,identity=identity,checkpoint=cfg['checkpoint'],model_fits=0,updates=0))
        shutil.copyfile(args.input/'scope.json',args.run/'scope.json')
        cache=np.load(args.input/'rgb_contexts.npy',mmap_mode='r')
        if cache.shape!=(31156,3,128,128) or cache.dtype!=np.uint8:raise ValueError('old RGB cache shape/dtype')
        def decode(rec):
            from PIL import Image
            raw=Path(rec['prepared_image']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=rec['prepared_image_sha256']:raise ValueError('source image SHA')
            with Image.open(io.BytesIO(raw)) as im:
                if im.size!=(rec['width'],rec['height']):raise ValueError('source image dimensions')
                with im.convert('RGB') as rgb:return np.asarray(rgb,dtype=np.uint8).transpose(2,0,1).copy()
        execute_predictions(scope,cache,args.run,engine,guard,decode);del cache
        expected=dict(source_image_decodes=338,native_tiles=13520,cached_forwards=12238)
        if guard.counts!=expected:raise ValueError('exact model-call counts')
        finish_evaluation(scope,args.run,cfg,lambda:load_references(args.input,scope,args.run))
        analyze=module('e028_plots',Path(__file__).with_name('analyze.py'));analyze.render(args.run)
        guard.check();write(args.run/'resource.json',guard.receipt());write(args.run/'status.json',dict(state='completed',counts=guard.counts,model_fits=0,updates=0))
        write(args.run/'output_receipt.json',dict(files={str(p.relative_to(args.run)).replace(os.sep,'/'):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in args.run.rglob('*') if p.is_file()}));guard.check()
    except BaseException as exc:
        write(args.run/'status.json',dict(state='stopped',reason=repr(exc),scientific='inconclusive_if_validity_failure',counts=guard.counts));write(args.run/'resource.json',guard.receipt());raise
    finally:stop.set()


if __name__=='__main__':main()
