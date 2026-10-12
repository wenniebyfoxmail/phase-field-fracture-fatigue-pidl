import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from aa2024_patch_mechanics import rectangular_mesh, solve_patch, sample_regular_mesh


class SyntheticPatchTests(unittest.TestCase):
    def setUp(self):
        self.xy,self.tri,self.bd = rectangular_mesh(7,5,6.,4.)
        self.damage = .4*np.exp(-np.sum(self.xy**2,axis=1))
        self.affine = np.c_[.01*self.xy[:,0]+.003*self.xy[:,1],
                            .02*self.xy[:,1]-.005*self.xy[:,0]]

    def solve(self,values,damage=None,E=1.):
        return solve_patch(self.xy,self.tri,self.bd,values,
                           self.damage if damage is None else damage,E=E)[0]

    def test_intact_affine_patch(self):
        u = self.solve(self.affine[self.bd],np.zeros(len(self.xy)))
        np.testing.assert_allclose(u,self.affine,atol=1e-12)

    def test_uniform_stiffness_scale_cancels(self):
        np.testing.assert_allclose(self.solve(self.affine[self.bd],E=1.),
                                   self.solve(self.affine[self.bd],E=72000.),atol=1e-12)

    def test_load_homogeneity_and_rigid_superposition(self):
        u = self.solve(self.affine[self.bd])
        np.testing.assert_allclose(self.solve(2.1*self.affine[self.bd]),2.1*u,atol=1e-12)
        r = [.03,-.02]+.002*np.c_[-self.xy[:,1],self.xy[:,0]]
        np.testing.assert_allclose(self.solve(self.affine[self.bd]+r[self.bd]),u+r,atol=1e-12)

    def test_localized_damage_changes_nonrigid_response(self):
        u = self.solve(self.affine[self.bd])
        intact = self.solve(self.affine[self.bd],np.zeros(len(self.xy)))
        self.assertGreater(np.linalg.norm(u-intact),1e-5)

    def test_interpolation_affine_and_domain(self):
        p = np.array([[.4,.7],[-1.1,.8],[2.7,-1.8]])
        expected = np.c_[.01*p[:,0]+.003*p[:,1],.02*p[:,1]-.005*p[:,0]]
        np.testing.assert_allclose(sample_regular_mesh(self.affine,p,nx=7,ny=5,width=6.,height=4.),expected,atol=1e-14)
        with self.assertRaises(ValueError):
            sample_regular_mesh(self.affine,[[10,0]],nx=7,ny=5,width=6.,height=4.)


if __name__ == "__main__":
    unittest.main()
