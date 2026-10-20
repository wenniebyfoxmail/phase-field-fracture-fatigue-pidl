"""New four-arm algebra/control fixtures only; no project model or physics."""
import unittest
import numpy as np
from profiled_residual_branch_measurement import residual_target,comparison,inverse_bound,Meter


class FourArmFixtures(unittest.TestCase):
    def test_target_is_not_physical_gradient(self):
        target=np.array([3e-11,-2e-11]);np.testing.assert_array_equal(residual_target(target,target),[0.,0.])
        self.assertGreater(np.max(abs(target)),0)
    def test_zero_root_chain_includes_moving_basis(self):
        # q=x*a+(B0+x*B1)*z ; fixed zstar changes partial J.
        a=np.array([1.,-2.]);B0=np.array([[1.],[2.]]);B1=np.array([[3.],[-1.]]);zs=np.array([.4]);K=np.diag([2.,3.])
        J=a+B1@zs;R=K@(B0@zs);C=B1.T@R;H=B0.T@K@B0;U=B0.T@K@J+C
        Q=J-B0@np.linalg.solve(H,U)
        omitted=a-B0@np.linalg.solve(H,B0.T@K@a+C)
        self.assertGreater(np.linalg.norm(Q-omitted),.1)
    def test_each_target_matches_its_own_implicit_path(self):
        a=np.array([1.,-2.]);q0=np.array([.2,.7]);B0=np.array([[1.],[2.]]);B1=np.array([[3.],[-1.]]);K=np.diag([2.,3.])
        for target in [B0.T@K@q0,np.zeros(1)]:
            def field(t):
                B=B0+t*B1;qraw=q0+t*a;z=np.linalg.solve(B.T@K@B,target-B.T@K@qraw)
                return qraw+B@z,z
            qs,zs=field(0.);J=a+B1@zs;C=B1.T@K@qs;H=B0.T@K@B0
            Q=J-B0@np.linalg.solve(H,B0.T@K@J+C)
            fd=(field(1e-6)[0]-field(-1e-6)[0])/2e-6
            np.testing.assert_allclose(Q,fd,rtol=1e-7,atol=1e-9)
    def test_frozen_full_field_retains_lift(self):
        K=np.array([[2.,.2],[.2,3.]]);q0=np.array([.1,.5]);delta=np.array([-.2,.1]);R0=K@q0
        self.assertAlmostEqual(.5*(q0+delta)@K@(q0+delta),.5*q0@K@q0+R0@delta+.5*delta@K@delta)
        self.assertNotAlmostEqual(.5*(q0+delta)@K@(q0+delta),.5*delta@K@delta)
    def test_inverse_enclosure_is_matrix_only(self):
        H=np.diag([2.,.5]);row=inverse_bound(H,np.diag([.5,2.]))
        self.assertTrue(row['matrix_bound_available']);self.assertGreaterEqual(row['stored_matrix_inverse_norm2_upper'],2.)
        self.assertFalse(row['finite_root_bound'])
    def test_inverse_invalid_no_claim(self):
        row=inverse_bound(np.eye(2),np.zeros((2,2)));self.assertFalse(row['matrix_bound_available']);self.assertIsNone(row['stored_matrix_inverse_norm2_upper'])
    def test_fd_gate_unchanged(self):
        Q=np.array([1.,2.]);h=1e-6;row,_,_=comparison(Q,h*Q,-h*Q,h);self.assertTrue(row['passed']);self.assertAlmostEqual(row['tolerance'],1e-10+1e-4*np.linalg.norm(Q))
    def test_combined_K_and_field_cap(self):
        class Guard:
            counts={'energy_force_field':499,'native_tangent':1}
            def charge(self,k):self.counts[k]+=1
            def stop(self,m):raise RuntimeError(m)
        with self.assertRaisesRegex(RuntimeError,'combined_field_K_500'):Meter(Guard()).action('native_tangent')

if __name__=='__main__':unittest.main()
