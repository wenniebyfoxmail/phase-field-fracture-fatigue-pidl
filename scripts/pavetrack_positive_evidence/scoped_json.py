"""Seekable JSON span reader: excluded records are skipped, never deserialized.

Hashing raw bytes is permitted. This parser materializes only allowlisted records;
keys/location identity strings are examined solely to decide inclusion.
"""
import json

class Cursor:
    def __init__(self, path, check=lambda: None):
        self.f = open(path, 'rb'); self.check = check; self.buf = b''; self.pos = 0; self.base = 0
    def close(self): self.f.close()
    def tell(self): return self.base + self.pos
    def seek(self, offset):
        self.f.seek(offset); self.buf = b''; self.pos = 0; self.base = offset
    def peek(self):
        if self.pos == len(self.buf):
            self.base += self.pos; self.pos = 0; self.buf = self.f.read(65536); self.check()
        return self.buf[self.pos] if self.buf else None
    def take(self):
        v = self.peek()
        if v is None: raise ValueError('unexpected JSON EOF')
        self.pos += 1; return v
    def ws(self):
        while self.peek() in (9,10,13,32): self.take()
    def expect(self, value):
        self.ws()
        if self.take() != ord(value): raise ValueError('JSON delimiter '+value)
    def skip(self):
        self.ws(); start = self.tell(); c = self.take()
        if c == 34:
            self.string_tail()
        elif c in (123,91):
            # No decoding of scalar contents while skipping disallowed payloads.
            stack = [125 if c == 123 else 93]
            while stack:
                c = self.take()
                if c == 34: self.string_tail()
                elif c in (123,91):
                    stack.append(125 if c == 123 else 93)
                    if len(stack)>64: raise ValueError('JSON nesting cap')
                elif c in (125,93):
                    if c != stack.pop(): raise ValueError('JSON bracket mismatch')
        else:
            while self.peek() is not None and self.peek() not in (9,10,13,32,44,93,125): self.take()
        return start,self.tell()
    def string_tail(self):
        while True:
            c=self.take()
            if c==34: return
            if c==92: self.take()
            elif c<32: raise ValueError('JSON control character')
    def decode(self, span, cap=8*1024*1024):
        a,b=span
        if b-a>cap: raise ValueError('selected JSON value size cap')
        offset=self.tell();self.seek(a);raw=self.f.read(b-a);self.seek(offset)
        return json.loads(raw)
    def fields(self, offset=0):
        self.seek(offset);self.expect('{');seen=set();self.ws()
        if self.peek()==125: self.take();return
        while True:
            key=self.decode(self.skip(),4096)
            if not isinstance(key,str) or key in seen: raise ValueError('duplicate/nonstring JSON key')
            seen.add(key);self.expect(':');span=self.skip();yield key,span
            self.ws();c=self.take()
            if c==125: break
            if c!=44: raise ValueError('JSON object comma')
    def items(self, offset):
        self.seek(offset);self.expect('[');self.ws()
        if self.peek()==93: self.take();return
        while True:
            yield self.skip()
            self.ws();c=self.take()
            if c==93: break
            if c!=44: raise ValueError('JSON array comma')
    def identity(self, span):
        # Nested iteration restores parent traversal position after probing.
        end=self.tell();fields=dict(self.fields(span[0]));result={}
        for name in ['reid','image_id','split']:
            if name in fields: result[name]=self.decode(fields[name],4096)
        self.seek(end);return result
    def selected_rows(self, span, locations):
        for item in self.items(span[0]):
            identity=self.identity(item)
            if str(identity.get('reid')) in locations:
                row=self.decode(item)
                if str(row['reid']) not in locations: raise ValueError('identity drift')
                yield row

def top_spans(path,check=lambda:None):
    c=Cursor(path,check)
    try: return dict(c.fields())
    finally: c.close()
