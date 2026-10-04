"""Process-local platform metadata fallback for restricted Condor job accounts.

CPython platform.py already falls back from WMI to environment/Win32 data on
OSError. Avoid spawning the failing WMI query at all in this explicitly Windows
x86_64 runtime; no OS permissions or solver mathematics are changed.
See https://github.com/python/cpython/issues/125315 and issue112278.
"""
import os
import platform
import sys


def configure():
    if sys.platform != 'win32':
        return
    if sys.maxsize <= 2**32:
        raise RuntimeError('Expected 64-bit Windows runtime')
    os.environ.setdefault('PROCESSOR_ARCHITECTURE', 'AMD64')
    def unavailable(*args):
        raise OSError('WMI unavailable in this restricted Condor process; use standard fallback')
    platform._wmi_query = unavailable
