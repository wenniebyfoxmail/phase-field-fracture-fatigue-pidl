"""Per-process exact-file capabilities; no GT objects in held input schema."""
import os,sys
from pathlib import Path

def norm(p):return os.path.normcase(os.path.realpath(os.fsdecode(p)))

class Files:
    def __init__(self,read_files=(),write_roots=(),code_roots=()):
        self.reads={norm(p) for p in read_files};self.writes=[norm(p)+os.sep for p in write_roots]
        self.code=[norm(p)+os.sep for p in code_roots]
    def allow(self,path,write=False):
        p=norm(path)
        if write:return any((p+os.sep).startswith(r) for r in self.writes)
        return p in self.reads or any((p+os.sep).startswith(r) for r in self.code+self.writes)
    def hook(self,event,args):
        if event=='open' and not isinstance(args[0],int):
            mode=args[1];flags=args[2] if len(args)>2 else 0
            write=bool(isinstance(mode,str) and any(c in mode for c in 'wax+')) or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
            if not self.allow(args[0],write):raise PermissionError('role file capability denied: '+str(args[0]))
        if event in ('os.system','subprocess.Popen'):raise PermissionError('worker cannot spawn subprocess')

def inference_payload(value,fold,arm,held,source_digest):
    if set(value)!={'fold','arm','held_locations','source_digest','heads','threshold'} or type(value['fold']) is not int or value['fold']!=fold or value['arm']!=arm or value['held_locations']!=held or value['source_digest']!=source_digest:raise ValueError('fold/arm/model key or GT-bearing model payload')
    if set(value['heads'])!={'Q','N','A'} or any(set(h)!={'coefficients','columns','verified'} for h in value['heads'].values()):raise ValueError('numeric inference heads only')
    return value

def request(value,role,fold=None):
    if set(value)!={'role','fold','manifest','run_id','input_freezes'} or value['role']!=role or value['fold']!=fold or value['run_id']!='S01-E029-R001':raise ValueError('role request identity')
    if role not in ['bank','spatial','fit','held','evaluate','render']:raise ValueError('unknown phase')
    if role in ['fit','held'] and (type(fold) is not int or type(value['fold']) is not int or fold not in range(3)):raise ValueError('fold range')
    if role not in ['fit','held'] and fold is not None:raise ValueError('global phase fold')
    return value
