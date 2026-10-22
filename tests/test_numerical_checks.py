import importlib.util
from pathlib import Path
import unittest
import torch

spec=importlib.util.spec_from_file_location('numerical_checks',Path(__file__).resolve().parents[1]/'source/numerical_checks.py')
checks=importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)


class CertificateFiniteTests(unittest.TestCase):
    def test_cpu_constructor_is_not_admitted_to_non_cpu_input(self):
        # Meta checks device bookkeeping only; no actual network forward or solve.
        net=torch.nn.Linear(2,1)
        reference=torch.empty(2,2,device='meta')
        with self.assertRaises(ValueError): checks.require_parameter_contract(net,reference)
        net=net.to('meta')
        checks.require_parameter_contract(net,reference)

    def test_model_dtype_must_match_input(self):
        with self.assertRaises(ValueError):
            checks.require_parameter_contract(torch.nn.Linear(2,1),torch.zeros(2,2,dtype=torch.float64))
        checks.require_parameter_contract(torch.nn.Linear(2,1).double(),torch.zeros(2,2,dtype=torch.float64))

    def test_loading_weights_does_not_move_destination_parameters(self):
        net=torch.nn.Linear(2,1)
        state={k:v.clone() for k,v in net.state_dict().items()}
        net.load_state_dict(state)
        self.assertEqual(next(net.parameters()).device.type,'cpu')
        with self.assertRaises(ValueError): checks.require_parameter_contract(net,torch.empty(2,2,device='meta'))

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
