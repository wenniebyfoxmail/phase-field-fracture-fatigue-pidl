"""Reuse one scoped-parser byte window without caching resource measurements."""
import json

def cursor_type(base):
    class WindowCursor(base):
        def seek(self,offset):
            if self.base<=offset<=self.base+len(self.buf):
                self.pos=offset-self.base;return
            super().seek(offset)
        def decode(self,span,cap=8*1024*1024):
            a,b=span
            if b-a>cap:raise ValueError('selected JSON value size cap')
            if self.base<=a<=b<=self.base+len(self.buf):raw=self.buf[a-self.base:b-self.base]
            else:
                physical=self.f.tell()
                try:self.f.seek(a);raw=self.f.read(b-a)
                finally:self.f.seek(physical)
            if len(raw)!=b-a:raise ValueError('truncated JSON value')
            return json.loads(raw)
    return WindowCursor
