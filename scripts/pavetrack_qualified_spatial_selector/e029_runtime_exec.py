"""System-stdlib seal check before executing ANY prepared runtime Python."""
import argparse,hashlib,json,os,sys
from pathlib import Path

def sha(path,parent=None):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):
            if parent is not None and os.getppid()!=parent:raise RuntimeError('parent disappeared during runtime seal check')
            h.update(b)
    return h.hexdigest()

def verify(lock_path,expected,parent=None):
    if sha(lock_path,parent)!=expected:raise ValueError('trusted runtime lock changed; self-rehash not accepted')
    lock=json.loads(Path(lock_path).read_text());root=Path(lock['prefix'])
    if lock['state']!='built_from_frozen_artifacts' or root.is_symlink() or not root.is_absolute():raise ValueError('runtime prefix/state')
    actual={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
    if set(actual)!=set(lock['files']):raise ValueError('runtime exact sealed inventory')
    for name,p in actual.items():
        if Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink() or not p.resolve().is_relative_to(root) or sha(p,parent)!=lock['files'][name]:raise ValueError('runtime sealed file changed')
    if parent is not None and os.getppid()!=parent:raise RuntimeError('parent disappeared before runtime exec')
    return lock

def main():
    p=argparse.ArgumentParser();p.add_argument('--lock',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();cmd=a.command
    if cmd and cmd[0]=='--':cmd=cmd[1:]
    parent=int(os.environ['E029_PARENT_PID']);lock=verify(a.lock,a.expected_sha256,parent)
    exe=Path(cmd[0]);expected=Path(lock['prefix'])/'bin/python3.12'
    if exe!=expected or not exe.is_file():raise ValueError('exact sealed Python command')
    os.execve(str(exe),cmd,dict(os.environ,E029_RUNTIME_LOCK_SHA256=a.expected_sha256))
if __name__=='__main__':main()
