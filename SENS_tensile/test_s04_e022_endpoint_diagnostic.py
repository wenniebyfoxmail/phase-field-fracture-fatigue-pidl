"""No optimizer or parameter updates: verify leaky diagnostic algebra."""
import unittest
import numpy as np
import torch
from test_s04_e021_endpoint_diagnostic import DiagnosticChecks
from diagnose_s04_e021_endpoints import measure
from s04_e022_screen import LastHiddenLeakyReLU
from s04_e019_frozen_residual import state_digest

class LeakyDiagnosticChecks(unittest.TestCase):
    def test_actual_leaky_negative_coefficient_and_chunk_invariance(self):
        m,d,b,_=DiagnosticChecks().fixture(mapped=True)
        m.residual.activations[-1]=LastHiddenLeakyReLU(m.residual.activations[-1].coeff)
        with torch.no_grad():
            m.residual.activations[-1].coeff.fill_(-.6)
            saved=m.correction_physical(torch.tensor(d['xy'])).numpy()
        before=state_digest(m)
        a=measure(m,d,b,saved,2);c=measure(m,d,b,saved,7)
        for x,y in zip(a['head'],c['head']):
            np.testing.assert_allclose(x['gradient_norm'],y['gradient_norm'],rtol=1e-10,atol=1e-12)
            self.assertLess(x['autodiff_max_error'],1e-12)
        self.assertEqual(before,state_digest(m));self.assertTrue(all(p.grad is None for p in m.parameters()))
        self.assertLess(a['activations'][-3]['coeff'],0)
        self.assertEqual(a['gradients'][0]['outside_background_norm'],0.)
        self.assertEqual(a['parameter_updates'],0)

    def test_saved_relu_field_rejected_under_leaky_behavior(self):
        m,d,b,s=DiagnosticChecks().fixture(mapped=True)
        with torch.no_grad():m.residual.activations[-1].coeff.fill_(-1.)
        with torch.no_grad():s=m.correction_physical(torch.tensor(d['xy'])).numpy()
        m.residual.activations[-1]=LastHiddenLeakyReLU(m.residual.activations[-1].coeff)
        with self.assertRaises(AssertionError):measure(m,d,b,s,4)

if __name__=='__main__':unittest.main()
