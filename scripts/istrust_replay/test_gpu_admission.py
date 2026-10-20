"""CPU-only CUDA-driver mocks. No real driver initialization, tensor or model use."""
from pathlib import Path
import ctypes, sys, unittest, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpu_admission as admission

EXPECTED = 'GPU-01234567-89ab-cdef-0123-456789abcdef'


class FakeDriver:
    def __init__(self, identity=EXPECTED, count=1, error=0):
        self.identity, self.count, self.error = identity, count, error
    def cuInit(self, flags): return self.error
    def cuDeviceGetCount(self, out):
        ctypes.cast(out, ctypes.POINTER(ctypes.c_int))[0] = self.count; return 0
    def cuDeviceGet(self, out, ordinal):
        ctypes.cast(out, ctypes.POINTER(ctypes.c_int))[0] = ordinal; return 0
    def cuDeviceGetUuid(self, out, device):
        ctypes.memmove(out, uuid.UUID(self.identity[4:]).bytes, 16); return 0


class AdmissionTests(unittest.TestCase):
    def no_torch(self): self.fail('Torch must not be imported before physical identity passes')
    def test_numeric_ordinal_follows_pci_order_instead_of_nvml_index(self):
        gpus=[{'index':5,'pci_bus_id':'00000000:41:00.0','uuid':EXPECTED},
              {'index':7,'pci_bus_id':'0000:01:00.0','uuid':'other'}]
        self.assertEqual(admission.visible_ordinal(gpus,EXPECTED),1)
    def test_driver_uuid_is_verified(self):
        self.assertEqual(admission.driver_identity(EXPECTED, FakeDriver())['driver_uuid'],EXPECTED)
    def test_wrong_physical_gpu_stops_before_torch_import(self):
        with self.assertRaises(ValueError):
            admission.smoke(EXPECTED, FakeDriver('GPU-ffffffff-ffff-ffff-ffff-ffffffffffff'), self.no_torch)
    def test_multiple_visible_devices_stop_before_torch_import(self):
        with self.assertRaises(ValueError): admission.smoke(EXPECTED, FakeDriver(count=2), self.no_torch)
    def test_driver_error_stops_before_torch_import(self):
        with self.assertRaises(RuntimeError): admission.smoke(EXPECTED, FakeDriver(error=999), self.no_torch)


if __name__ == '__main__': unittest.main()
