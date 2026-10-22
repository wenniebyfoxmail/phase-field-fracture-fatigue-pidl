import importlib.util
from pathlib import Path
import unittest
import torch

spec=importlib.util.spec_from_file_location('numerical_checks',Path(__file__).resolve().parents[1]/'source/numerical_checks.py')
checks=importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)


class CertificateFiniteTests(unittest.TestCase):
    def test_later_nan_cannot_be_hidden_by_finite_float32(self):
        for bad in (float('nan'),float('inf'),-float('inf')):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                checks.finite_max(1e-5,bad)

    def test_positive_infinity_is_not_log_domain_certificate(self):
        for bad in (0.,-1.,float('inf'),float('nan')):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                checks.require_positive_energy(torch.tensor(bad,dtype=torch.float64))
        checks.require_positive_energy(torch.tensor(.1))

    def test_double_gradient_nonfinite_is_rejected(self):
        for bad in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                checks.require_finite(torch.zeros(2),torch.tensor([0.,bad],dtype=torch.float64))

if __name__=='__main__': unittest.main()
