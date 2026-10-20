"""Observation-only full-profile receipts. No models, AD, solvers or launchers.

An event JSON is committed only after its arrays have been atomically written,
fsynced and hashed. New folders/files are exclusive; failed attempts stay intact.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import numpy as np


def json_value(value):
    if isinstance(value,np.generic):return json_value(value.item())
    if value is None or isinstance(value,(str,bool,int)):return value
    if isinstance(value,float):return value if math.isfinite(value) else {'nonfinite':repr(value)}
    if isinstance(value,Path):return str(value)
    if isinstance(value,dict):return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_value(v) for v in value]
    return {'unsupported_type':type(value).__name__}


def file_ref(path):
    path=Path(path)
    if not path.is_file():return {'path':str(path),'available':False}
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1048576),b''):digest.update(part)
    return {'path':str(path),'available':True,'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def _commit(path,write):
    """Never replace a prior event; temp files are not completion evidence."""
    path=Path(path)
    if path.exists():raise FileExistsError(path)
    # These exact disappearing temp names are recognized by bytes_under.
    # Arrays are serialized per recorder/folder; O_EXCL rejects stale/concurrent
    # files rather than deleting or overwriting someone else's temp.
    name=('.profile_audit_npy' if path.suffix=='.npy' else path.name)+'.'+str(os.getpid())+'.tmp'
    tmp=path.with_name(name)
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'wb') as stream:
            write(stream);stream.flush();os.fsync(stream.fileno())
        # Hard-link publishes an exclusive final name atomically; no overwrite.
        os.link(tmp,path)
        dfd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass


def atomic_json(path,data):
    payload=(json.dumps(json_value(data),indent=2,allow_nan=False)+'\n').encode()
    _commit(path,lambda stream:stream.write(payload))


def note_record_failure(primary,secondary):
    """Keep the scientific/rollback exception primary if logging also fails."""
    note='profile receipt error: '+type(secondary).__name__+': '+str(secondary)
    if hasattr(primary,'add_note'):primary.add_note(note)
    primary.profile_receipt_error=note


class ProfileCheckRecorder:
    def __init__(self,folder,context):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=False)
        self.number=0;self.context=json_value(context)
        self('context',self.context)
    def __call__(self,event,data=None,arrays=None):
        self.number+=1;prefix=f'{self.number:03d}_{event}'
        refs={}
        for name,array in (arrays or {}).items():
            if not isinstance(array,np.ndarray) or array.dtype.hasobject:
                refs[name]={'available':False,'unsupported_type':type(array).__name__};continue
            value=np.array(array,copy=True,order='C');path=self.folder/(prefix+'_'+name+'.npy')
            _commit(path,lambda stream,value=value:np.save(stream,value,allow_pickle=False))
            refs[name]={**file_ref(path),'dtype':str(value.dtype),'shape':list(value.shape),'finite':bool(np.isfinite(value).all()) if np.issubdtype(value.dtype,np.number) else None}
        atomic_json(self.folder/(prefix+'.json'),{'event':event,'sequence':self.number,'data':data or {},'arrays':refs})


def trial_metadata(out):
    """Exclude heavyweight mutable candidate objects, bind their saved files."""
    keys=['E','Ru','rank','actual_nn','full_current_basis','persisted_actual_phi','frozen_state','fixed_state','rolled_back','head_gradient_inf','realization_maxabs','finite','boundary_maxabs','folder','actual_readout','actual_weights']
    meta={k:out[k] for k in keys if k in out}
    if out.get('folder'):
        root=Path(out['folder'])
        meta['saved_contract_files']={name:file_ref(root/name) for name in ['basis/metadata.json','basis/transform.npy','head/solver.json','head/accepted.json','head/conditioned_candidate.npz','rollback.json','profile_rollback_audit.json','adapter_failure.json']}
    readout=out.get('actual_readout',{}).get('path')
    if readout:
        root=Path(readout)
        meta['actual_head_readout_files']={suffix:file_ref(root.with_name(root.stem+suffix))
            for suffix in ['_actual.json','_actual_projected_gradient.npy']}
    return meta
