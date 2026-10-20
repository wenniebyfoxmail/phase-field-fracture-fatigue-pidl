"""Read distribution metadata only; no scientific package import or file writes.

This is a separately approved preparation action, not producer admission. The
existing guarded Agg render and exact execution-card review remain mandatory.
"""
import argparse
import getpass
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import resource
import socket
import sys
from time import perf_counter, time

PACKAGES = ('numpy', 'scipy', 'torch', 'osqp', 'h5py', 'psutil', 'matplotlib')


def collect(dependency_root):
    start = perf_counter()
    dependency_root = Path(dependency_root)
    if not dependency_root.is_absolute() or not dependency_root.is_dir():
        raise RuntimeError('exact retained dependency directory is unavailable')
    versions, origins, errors = {}, {}, {}
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(dependency_root))
        for name in PACKAGES:
            try:
                dist = metadata.distribution(name)
                versions[name] = dist.version
                origins[name] = str(dist.locate_file(''))
            except metadata.PackageNotFoundError:
                versions[name] = None
                errors[name] = 'distribution metadata not found'
    finally:
        sys.path[:] = old_path
    # Reading metadata must not become an implicit torch/CUDA/science import.
    imported = [n for n in PACKAGES if n in sys.modules]
    if imported:
        raise RuntimeError('unexpected scientific import: ' + ','.join(imported))
    return dict(schema='hybrid-runtime-metadata-v1', observed_epoch=time(),
                hostname=socket.gethostname(), account=getpass.getuser(),
                python=platform.python_version(), executable=sys.executable,
                dependency_root=str(dependency_root), runtime_metadata=versions,
                metadata_origins=origins, metadata_errors=errors,
                wall_seconds=perf_counter()-start,
                cpu_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime +
                            resource.getrusage(resource.RUSAGE_SELF).ru_stime,
                scientific_imports=[], scientific_states_opened=False,
                numerical_seconds=0., gpu_seconds=0.,
                scope='metadata only; no write/install/render/solve/fit/admission')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependency-root', required=True, type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux':
        raise RuntimeError('inventory execution is selected Linux host only')
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (256*2**20, 256*2**20))
    print(json.dumps(collect(args.dependency_root), allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
