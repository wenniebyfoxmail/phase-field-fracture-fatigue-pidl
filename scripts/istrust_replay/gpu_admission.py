"""Verify physical CUDA identity before importing torch or allocating a tensor."""
import argparse, ctypes, importlib, json, os, re, uuid


class CUuuid(ctypes.Structure):
    _fields_ = [('bytes', ctypes.c_ubyte * 16)]


def pci_key(value):
    domain, bus, tail = value.split(':')
    device, function = tail.split('.')
    return tuple(int(x, 16) for x in [domain, bus, device, function])


def visible_ordinal(gpus, expected_uuid):
    """CUDA_DEVICE_ORDER=PCI_BUS_ID; do not assume the NVML index is a CUDA ordinal."""
    ordered = sorted(gpus, key=lambda g: pci_key(g['pci_bus_id']))
    if len({pci_key(g['pci_bus_id']) for g in ordered}) != len(ordered):
        raise ValueError('Ambiguous physical PCI identities')
    selected = [i for i, g in enumerate(ordered) if g['uuid'] == expected_uuid]
    if len(selected) != 1:
        raise ValueError('Expected GPU UUID not uniquely present')
    return selected[0]


def driver_identity(expected_uuid, driver=None):
    expected = 'GPU-' + str(uuid.UUID(expected_uuid.removeprefix('GPU-')))
    driver = driver if driver is not None else ctypes.CDLL('libcuda.so.1')
    def check(status, call):
        if status != 0:
            raise RuntimeError(f'{call} failed with CUDA driver status {status}')
    check(driver.cuInit(0), 'cuInit')
    count = ctypes.c_int()
    check(driver.cuDeviceGetCount(ctypes.byref(count)), 'cuDeviceGetCount')
    if count.value != 1:
        raise ValueError(f'Expected one visible CUDA device, got {count.value}')
    device, identity = ctypes.c_int(), CUuuid()
    check(driver.cuDeviceGet(ctypes.byref(device), 0), 'cuDeviceGet')
    check(driver.cuDeviceGetUuid(ctypes.byref(identity), device), 'cuDeviceGetUuid')
    actual = 'GPU-' + str(uuid.UUID(bytes=bytes(identity.bytes)))
    if actual != expected:
        raise ValueError(f'Physical GPU mismatch: expected {expected}, got {actual}')
    return {'driver_uuid': actual, 'driver_visible_count': count.value}


def smoke(expected_uuid, driver=None, load_torch=None):
    identity = driver_identity(expected_uuid, driver)
    print(json.dumps({'event': 'physical_identity_verified', **identity}), flush=True)
    torch = (load_torch or (lambda: importlib.import_module('torch')))()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError('PyTorch CUDA availability/count failed after physical identity verification')
    x = torch.zeros(1, device='cuda')
    torch.cuda.synchronize()
    result = dict(identity, torch=torch.__version__, cuda=torch.version.cuda,
                  gpu_name=torch.cuda.get_device_name(0), allocation=float(x.cpu()[0]),
                  model_forward=False, cuda_smoke_complete=True)
    print(json.dumps(result), flush=True)
    return result


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--expected-uuid', required=True); a = ap.parse_args()
    if os.getenv('CUDA_DEVICE_ORDER') != 'PCI_BUS_ID' or not re.fullmatch(r'\d+', os.getenv('CUDA_VISIBLE_DEVICES', '')):
        raise ValueError('Historical PyTorch requires a numeric mask with explicit PCI device ordering')
    smoke(a.expected_uuid)


if __name__ == '__main__': main()
