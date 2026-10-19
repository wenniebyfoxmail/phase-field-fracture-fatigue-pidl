"""Read small named public samples. Range reads abort if unsupported; never bulk mirrors."""
import importlib.util
import io
import json
from pathlib import Path
import urllib.request
import zipfile
import hashlib

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/dataset_completion_20261019')

class RemoteZip(io.RawIOBase):
    def __init__(self,url,size):
        self.url,self.size,self.pos,self.used=url,size,0,0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        return self.pos
    def read(self,n=-1):
        if n<0: n=self.size-self.pos
        n=min(n,self.size-self.pos)
        if n<=0: return b''
        if n>32_000_000 or self.used+n>64_000_000: raise ValueError(f'range metadata budget exceeded: request={n}, used={self.used}')
        req=urllib.request.Request(self.url,headers={'Range':f'bytes={self.pos}-{self.pos+n-1}','User-Agent':'Wennie-research-data-audit/1.0'})
        with urllib.request.urlopen(req,timeout=40) as r:
            if r.status!=206: raise ValueError('server ignored Range; bulk acquisition declined')
            expected=f'bytes {self.pos}-{self.pos+n-1}/{self.size}'
            if r.headers.get('Content-Range')!=expected: raise ValueError('Content-Range mismatch')
            b=r.read(n+1)
            if len(b)!=n: raise ValueError('range length mismatch')
        self.pos+=n; self.used+=n
        return b

def fetch(url,path,limit=4_000_000):
    with urllib.request.urlopen(url,timeout=35) as r:
        data=r.read(limit+1)
        if len(data)>limit: raise ValueError('sample budget exceeded')
    path.write_bytes(data)
    return {'file':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def main():
    results=[]
    # Mendeley has already been fully acquired elsewhere; obtain no duplicate bulk files.
    listing=json.loads((ROOT/'mendeley_dic_fatigue/file_listing_api.json').read_text())
    for obj in ([] if '--zip-only' in __import__('sys').argv else listing):
        if obj['size']<100_000:
            rec={'dataset_id':'mendeley_dic_fatigue','url':obj['content_details']['download_url']}
            try:
                rec.update(fetch(rec['url'],ROOT/'mendeley_dic_fatigue'/obj['filename']))
                rec['published_sha256_matches']=rec['sha256']==obj['content_details']['sha256_hash']
            except Exception as e: rec['error']=str(e)
            results.append(rec)
    for key,filename in [('multitemporal_concrete','crackseq_dataset_multi_mono_patches.zip')]:
        files=json.loads((ROOT/key/'official_metadata.json').read_text())['files']
        obj=next(f for f in files if f.get('key',f.get('name'))==filename)
        url=obj.get('links',{}).get('self',obj.get('download_url')); size=obj['size']
        rec={'dataset_id':key,'archive_url':url,'archive_bytes':size,'selection':'lexicographically first public development/train image and its same-name label when available; no model scores'}
        try:
            remote=RemoteZip(url,size)
            with zipfile.ZipFile(remote) as z:
                names=z.namelist()
                (ROOT/key/'patch_archive_member_list.json').write_text(json.dumps(names,ensure_ascii=False,indent=2))
                split_name='data/train_val_test_split.json'
                if split_name in names:
                    split_data=z.read(split_name)
                    (ROOT/key/'train_val_test_split.json').write_bytes(split_data)
                    rec['split_preview']=str(json.loads(split_data))[:1500]
                train_ids=set(json.loads(split_data)['train']) if split_name in names else set()
                candidates=sorted(n for n in names if n.lower().endswith(('.jpg','.png','.jpeg','.tif','.tiff','.npy')) and '__MACOSX' not in n and not Path(n).name.startswith('.') and Path(n).stem.rsplit('_',1)[-1] in train_ids and '/mono-temporal/images/' in n)
                rec['image_name_preview']=[n for n in names if '/images/' in n and not Path(n).name.startswith('.')][:6]
                selected=candidates[:1]
                if selected:
                    target=selected[0].replace('/images/','/targets/').replace('mono_image_','mono_target_')
                    if target in names: selected.append(target)
                rec['samples']=[]
                for name in selected:
                    info=z.getinfo(name)
                    if info.file_size>12_000_000 or info.compress_size>7_000_000:
                        rec['samples'].append({'member':name,'status':'too large for bounded sample'})
                        continue
                    data=z.read(info) # ZIP CRC checked by zipfile.
                    dest=ROOT/key/('sample_'+str(len(rec['samples']))+'_'+Path(name).name)
                    dest.write_bytes(data)
                    detail={'member':name,'file':str(dest),'bytes':len(data),'zip_crc_checked':True}
                    if name.lower().endswith(('.png','.jpg','.jpeg','.tif','.tiff')):
                        try:
                            from PIL import Image
                            with Image.open(io.BytesIO(data)) as image:
                                image.load(); detail.update(dimensions=list(image.size),mode=image.mode)
                        except ImportError: detail['decode']='PIL unavailable in this interpreter'
                    rec['samples'].append(detail)
                rec.update(member_count=len(names),range_bytes_read=remote.used)
        except Exception as e: rec['error']=str(e)
        results.append(rec)
    (ROOT/'patch_sample_receipts.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
