"""Peak RSS with one persistent Windows ctypes API/type binding.

Do not define Structure/POINTER types per sample: ctypes retains pointer types
in its process-wide cache, so high-frequency sampling can itself leak memory.
"""
import ctypes
import functools
import os
import sys

def make_windows_probe(kernel,psapi):
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_uint32),('PageFaultCount',ctypes.c_uint32)]+[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_uint32]
    psapi.GetProcessMemoryInfo.restype=ctypes.c_int
    def probe():
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb): raise OSError('cannot measure peak RSS')
        return int(counters.PeakWorkingSetSize)
    probe.counter_type=Counters
    return probe

@functools.lru_cache(maxsize=1)
def windows_probe():
    return make_windows_probe(ctypes.WinDLL('kernel32',use_last_error=True),ctypes.WinDLL('psapi',use_last_error=True))

def peak_rss():
    if os.name=='nt': return windows_probe()()
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
