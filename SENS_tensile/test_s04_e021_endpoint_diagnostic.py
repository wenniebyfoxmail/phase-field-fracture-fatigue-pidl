"""Deterministic, parameter-free checks of streamed diagnostic reductions."""
import copy
import unittest
import numpy as np
import torch
from torch import nn
from diagnose_s04_e021_endpoints import measure, spectrum
from s04_e019_frozen_residual import FrozenResidualUV, state_digest
from s04_e021_residual_coordinates import CoordinateResidualUV, RULE
from s04_e018_global_local import NeuralNet, PADDING, DAMAGE_THRESHOLD


class DiagnosticChecks(unittest.TestCase):
    def fixture(self,mapped=False):
        torch.set_default_dtype(torch.float64)
        with torch.random.fork_rng():
            torch.manual_seed(24)
            net=NeuralNet(2,2,2,5,'TrainableReLU',1.)
            base=nn.Linear(2,2)
        with torch.no_grad():net.activations[0].coeff.fill_(-.7)
        g=dict(lower=[-.2,-.2],upper=[.2,.2],center=[0.,0.],scale=[.2+PADDING,.2+PADDING],padding=PADDING,damage_threshold=DAMAGE_THRESHOLD)
        model=CoordinateResidualUV(base,net,g,dict(rule=RULE,local_center=[.01,-.01],local_scale=[.1,.15])) if mapped else FrozenResidualUV(base,net,'localized',g)
        xy=np.array([[-.3,0],[-.1,0],[0,.1],[.15,-.1],[.3,.1],[.05,.12],[.02,-.05],[-.32,-.2]])
        baseline=np.zeros((len(xy),2))
        with torch.no_grad():saved=model.correction_physical(torch.tensor(xy)).numpy()
        target=saved+np.column_stack([np.linspace(-.00003,.00001,len(xy)),np.linspace(.00002,-.00001,len(xy))])
        data=dict(xy=xy,mass=np.arange(1,len(xy)+1,dtype=float),damage=np.array([.3,.4,0,.5,0,0,.2,0]),equilibrated_uv=target)
        return model,data,baseline,saved

    def test_chunk_and_mapping_invariance(self):
        for mapped in (False,True):
            m,d,b,s=self.fixture(mapped);before=state_digest(m)
            a=measure(m,d,b,s,2);c=measure(m,d,b,s,7)
            self.assertEqual(before,state_digest(m))
            self.assertEqual(a['model_digest_before'],a['model_digest_after'])
            self.assertEqual(a['parameter_updates'],0)
            np.testing.assert_allclose(a['full_rms'],c['full_rms'],atol=1e-14,rtol=0)
            for x,y in zip(a['head'],c['head']):
                np.testing.assert_allclose(x['gradient_norm'],y['gradient_norm'],atol=1e-12,rtol=1e-10)
                self.assertLess(x['autodiff_max_error'],1e-12)
            self.assertEqual(a['gradients'][0]['outside_background_norm'],0.)
            self.assertIsNone(a['head'][2]['scaled_normal_residual'])
            self.assertLess(a['activations'][0]['coeff'],0)
            self.assertTrue(all(p.grad is None for p in m.parameters()))

    def test_reject_changed_saved_field(self):
        m,d,b,s=self.fixture();s=s.copy();s[1,0]+=.001
        with self.assertRaises(AssertionError):measure(m,d,b,s,4)

    def test_zero_spectrum_and_relative_rank(self):
        self.assertEqual(spectrum(np.zeros((3,3)))['rank_relative_1e_8'],0)
        self.assertEqual(spectrum(np.diag([2.,1.,0.]))['rank_relative_1e_8'],2)


if __name__=='__main__':unittest.main()
