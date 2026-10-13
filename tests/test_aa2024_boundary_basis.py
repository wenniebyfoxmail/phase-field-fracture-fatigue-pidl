import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import hashlib
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import aa2024_boundary_basis as m
import aa2024_boundary_basis_view as view

def receipt(root,mode):
    m.write_json(root/'execution_receipt.json',dict(mode=mode,execution_status='succeeded',
        runner_sha256=m.sha(m.__file__),dependencies_sha256=m.sources(),
        artifacts_sha256={p.name:m.sha(p) for p in root.iterdir() if p.is_file() and p.name!='execution_receipt.json'}))

class BoundaryBasis(unittest.TestCase):
    def test_synthetic_prepare_never_parses_held_body(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);archive=base/'source.zip';out=base/'prep';out.mkdir()
            xy,tri,_=m.rectangular_mesh(nx=49,ny=33,width=48.,height=32.)
            schema='# ID; x_undef [mm]; y_undef [mm]; z_undef [mm]; u [mm]; v [mm]; w [mm]; epsx [%]; epsy [%]; epsxy [1]; epseqv [%]\n'
            with zipfile.ZipFile(archive,'w') as z:
                for stage,force in ((10,1),(11,2),(12,3)):
                    header=f'# current_stage_index: {stage}\n# reference_stage_index: 1\n# cycles: 225211.5\n# force: {force}\n'+schema
                    body='\n'.join(f'{i+1};{x};{y};0;{force*x*.001};{force*y*.001};0;0;0;0;0' for i,(x,y) in enumerate(xy)) if stage!=12 else '1;BAD;BAD;BAD;HELD;HELD;HELD;HELD;HELD;HELD;HELD'
                    z.writestr(f'global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt',header+body)
                connection='Type;Element #;Node 1;Node 2;Node 3\n'+'\n'.join(f'3;{i};{a};{b};{c}' for i,(a,b,c) in enumerate(tri))
                z.writestr('global_3d_dic/Connections/global_3d_dic_results_1_10_connections.txt',connection)
            md5=hashlib.md5(archive.read_bytes()).hexdigest()
            with patch.object(m,'EXPECTED_SIZE',archive.stat().st_size),patch.object(m,'EXPECTED_MD5',md5),patch.object(m,'parse_nodemap',wraps=m.parse_nodemap) as parser:
                m.prepare(archive,out);self.assertEqual(parser.call_count,2)
            a=m.load(out/'prepared.npz');self.assertEqual(len(a['B1_mesh']),1421)
            np.testing.assert_allclose(a['train_v'],.001*a['xy'],atol=1e-15)
            self.assertTrue(np.all(a['weights']>0))
            meta=json.loads((out/'preparation.json').read_text())
            self.assertLessEqual(meta['assets']['B1']['fourth_neighbour_max_mm'],2)
            self.assertEqual(float(a['alpha']),2)

    def test_nested_grid_and_bounds(self):
        self.assertEqual(m.PAIRS.shape,(126,2));self.assertTrue(np.all(m.PAIRS[:21,1]==0))
        for r,l in m.PAIRS:
            d=m.damage(np.array([0,.4,1]),np.array([.8,.5,1]),np.array([1,.8,.5]),r,l)
            self.assertTrue(np.all((d>=0)&(d<=1)))
        self.assertEqual(len(m.ARMS),9)

    def test_domain_spacing_and_common_sampling(self):
        points=np.array([[0.,0.],[5.,3.],[-16.,-7.]])
        for p in m.DOMAINS.values():
            xy,t,bd=m.rectangular_mesh(**p)
            self.assertLessEqual(len(xy),1421)
            self.assertAlmostEqual(p['width']/(p['nx']-1),.9)
            self.assertAlmostEqual(p['height']/(p['ny']-1),.9)
            values=np.column_stack((1+2*xy[:,0]-xy[:,1],xy[:,1]+3))
            expect=np.column_stack((1+2*points[:,0]-points[:,1],points[:,1]+3))
            np.testing.assert_allclose(m.sample_regular_mesh(values,points,**p),expect,atol=1e-13)

    def test_headers_do_not_convert_response(self):
        h=m.headers('# current_stage_index: 12\n# reference_stage_index: 1\n# cycles: 225211.5\n# force: 3\n# ID;x\n1;NOT_A_NUMBER\n')
        self.assertEqual(m.identity(h,12),3)
        with self.assertRaises(ValueError):m.identity(h,11)

    def test_contrast_definition(self):
        x=m.contrasts(dict(B0K0=4,B1K0=3,B0K1=2,B1K1=1,secant=2))
        self.assertEqual(x['primary_boundary_only_minus_basis_only_mm'],1)
        self.assertEqual(x['boundary_mean_gain_mm'],1)
        self.assertEqual(x['basis_mean_gain_mm'],2)
        self.assertEqual(x['interaction_mm'],0)
        self.assertEqual(x['descriptive_single_lever'],'basis_capacity_larger_single_gain')
        additive=m.contrasts(dict(B0K0=3,B1K0=2.8,B0K1=2.8,B1K1=2.6,secant=2.5))
        self.assertAlmostEqual(additive['interaction_mm'],0)
        self.assertEqual(additive['descriptive_single_lever'],'equal_improving_single_changes')
        self.assertTrue(additive['no_selected_factorial_arm_beats_secant'])

    def test_soft_budget_at_boundary_and_overrun(self):
        with patch.object(m.time,'monotonic',return_value=599.999):m.check_budget(0)
        for elapsed in (600,601):
            with patch.object(m.time,'monotonic',return_value=elapsed):
                with self.assertRaises(TimeoutError):m.check_budget(0)

    def test_fit_overrun_before_and_after_solver(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root,_,a=self.synthetic_fit(base)
            for values,expected in (([0,600],0),([0,599,600],1)):
                out=base/str(expected);out.mkdir()
                def fake(xy,t,bd,bc,d):return .001*xy,1e-15
                with patch.object(m.time,'monotonic',side_effect=values),patch.object(m,'solve_patch',side_effect=fake) as s:
                    with self.assertRaises(TimeoutError):m.fit(root,out)
                    self.assertEqual(s.call_count,expected)
                self.assertFalse((out/'fit.json').exists())

    def test_main_serialization_overrun_has_failed_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root,_,a=self.synthetic_fit(base);out=base/'overrun'
            late=[False];original=m.write_json
            def writing(path,x):
                original(path,x)
                if path.name=='profiles.json':late[0]=True
            def fake(xy,t,bd,bc,d):return .001*xy,1e-15
            args=['driver','fit','--input',str(root),'--output',str(out),'--source-commit','synthetic','--run-id','synthetic']
            with patch.object(sys,'argv',args),patch.object(m.socket,'gethostname',return_value='GPUServer8'),patch.object(m.time,'monotonic',side_effect=lambda:600 if late[0] else 0),patch.object(m,'solve_patch',side_effect=fake),patch.object(m,'write_json',side_effect=writing):
                with self.assertRaises(TimeoutError):m.main()
            r=json.loads((out/'execution_receipt.json').read_text())
            self.assertEqual(r['execution_status'],'failed');self.assertFalse((out/'fit.json').exists())

    def test_final_receipt_clock_overrun_downgrades_status(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root,_,a=self.synthetic_fit(base);out=base/'final_overrun'
            args=['driver','fit','--input',str(root),'--output',str(out),'--source-commit','synthetic','--run-id','synthetic']
            def pretend_fit(inp,output,**kwargs):(output/'forensic.txt').write_text('synthetic partial artifact')
            with patch.object(sys,'argv',args),patch.object(m.socket,'gethostname',return_value='GPUServer8'),patch.object(m.time,'monotonic',side_effect=[0,599.999,600]),patch.object(m,'fit',side_effect=pretend_fit):
                with self.assertRaises(TimeoutError):m.main()
            r=json.loads((out/'execution_receipt.json').read_text())
            self.assertEqual(r['execution_status'],'failed');self.assertEqual(r['elapsed_seconds'],600)
            self.assertEqual(r['artifacts_sha256']['forensic.txt'],m.sha(out/'forensic.txt'))

    def synthetic_fit(self,base):
        root=base/'prep';root.mkdir();out=base/'fit';out.mkdir()
        xy=np.array([[-3.,-2.],[-1.,-2.],[1.,-2.],[3.,-2.],[-3.,2.],[-1.,2.],[1.,2.],[3.,2.],[-2.,1.],[2.,1.],[-2.,-1.],[2.,-1.]])
        a=dict(ids=np.arange(1,13),xy=xy,weights=np.linspace(1,2,12),train_v=.001*xy,u10=np.zeros((12,2)),alpha=2.)
        for b,p in m.DOMAINS.items():
            mesh,t,bd=m.rectangular_mesh(**p);d0,br=m.candidate_basis(mesh)
            for k,v in dict(mesh=mesh,tri=t,boundary=bd,bc=.001*mesh[bd],d0=d0,br=br,
                bl=np.exp(-((mesh[:,0]+9)**2+mesh[:,1]**2)/18)).items():a[b+'_'+k]=v
        np.savez_compressed(root/'prepared.npz',**a)
        m.write_json(root/'preparation.json',dict(held_member_sha256='placeholder',forces=[1,2,3],cycle='225211.5'))
        receipt(root,'prepare')
        def fake(xy,t,bd,bc,d):return .001*xy+np.column_stack((d,d*d))*.0001,1e-15
        with patch.object(m,'solve_patch',side_effect=fake) as solve:
            m.fit(root,out);self.assertEqual(solve.call_count,254)
        receipt(out,'fit')
        return root,out,a

    def test_mock_fit_complete_and_nested_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root,out,a=self.synthetic_fit(Path(td))
            p=json.loads((out/'profiles.json').read_text());f=m.load(out/'candidate_fields.npz')
            for b in m.DOMAINS:
                self.assertEqual(f[b].shape,(126,12,2))
                loss=[x['train_MAE_mm'] for x in p[b]['profile']]
                self.assertLessEqual(min(loss),min(loss[:21]))
                self.assertEqual(p[b]['selected']['K0'],int(np.argmin(loss[:21])))
            self.assertTrue(np.isfinite(m.load(out/'frozen_predictions.npz')['B1K1']).all())

    def test_failed_receipt_blocks_before_target_access(self):
        with tempfile.TemporaryDirectory() as td:
            root,out,a=self.synthetic_fit(Path(td))
            r=json.loads((out/'execution_receipt.json').read_text());r['execution_status']='failed'
            m.write_json(out/'execution_receipt.json',r)
            with patch.object(m,'parse_nodemap',side_effect=AssertionError('held accessed')) as parser:
                with self.assertRaises(ValueError):m.validate(out,Path(td)/'nonexistent',Path(td))
                parser.assert_not_called()

    def test_tampered_profile_and_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root,out,a=self.synthetic_fit(Path(td));(out/'profiles.json').write_text('{}')
            with self.assertRaises(ValueError):m.completed(out,'fit',('profiles.json',))
            receipt(out,'fit');r=json.loads((out/'execution_receipt.json').read_text())
            r['dependencies_sha256']={};m.write_json(out/'execution_receipt.json',r)
            with self.assertRaises(ValueError):m.completed(out,'fit',('profiles.json',))

    def test_validate_common_support_and_z_missingness(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root,out,a=self.synthetic_fit(base)
            h=dict(ids=a['ids'],xyz=np.column_stack((a['xy'],np.zeros(12))),u=np.column_stack((2*a['train_v'],np.zeros(12))),
                headers=dict(current_stage_index='12',reference_stage_index='1',cycles='225211.5',force='3'))
            high=base/'high.txt';high.write_text('bounded synthetic source')
            meta=json.loads((out/'fit.json').read_text());meta['held_member_sha256']=m.sha(high)
            m.write_json(out/'fit.json',meta);receipt(out,'fit')
            v1=base/'v1';v1.mkdir()
            with patch.object(m,'parse_nodemap',return_value=h):m.validate(out,high,v1)
            h['xyz'][:,2]=np.nan;h['u'][:,2]=np.nan;v2=base/'v2';v2.mkdir()
            with patch.object(m,'parse_nodemap',return_value=h):m.validate(out,high,v2)
            self.assertEqual(json.loads((v1/'metrics.json').read_text()),json.loads((v2/'metrics.json').read_text()))
            h['u'][0,0]=np.nan;v3=base/'v3';v3.mkdir()
            with patch.object(m,'parse_nodemap',return_value=h):m.validate(out,high,v3)
            f=m.load(v3/'validation_fields.npz')
            for arm in m.ARMS:self.assertEqual(f[arm].shape,(11,2))
            self.assertEqual(json.loads((v3/'metrics.json').read_text())['missing_ids'],[1])

    def test_view_rejects_unreceipted_tampered_and_mixed(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);root,out,a=self.synthetic_fit(base)
            h=dict(ids=a['ids'],xyz=np.column_stack((a['xy'],np.zeros(12))),u=np.column_stack((2*a['train_v'],np.zeros(12))),
                headers=dict(current_stage_index='12',reference_stage_index='1',cycles='225211.5',force='3'))
            high=base/'high.txt';high.write_text('synthetic')
            meta=json.loads((out/'fit.json').read_text());meta['held_member_sha256']=m.sha(high)
            m.write_json(out/'fit.json',meta);receipt(out,'fit');v=base/'validation';v.mkdir();fig=base/'fig';fig.mkdir()
            with patch.object(m,'parse_nodemap',return_value=h):m.validate(out,high,v)
            with self.assertRaises(FileNotFoundError):view.results(out,v,fig)
            receipt(v,'validate');original=json.loads((v/'metrics.json').read_text())
            changed=json.loads(json.dumps(original));changed['MAE_mm']['B0K0']=123
            m.write_json(v/'metrics.json',changed)
            with self.assertRaises(ValueError):view.results(out,v,fig)
            receipt(v,'validate')
            with self.assertRaisesRegex(ValueError,'metric/residual'):view.results(out,v,fig)
            changed=json.loads(json.dumps(original));changed['source_fit']['receipt_sha256']='wrong'
            m.write_json(v/'metrics.json',changed);receipt(v,'validate')
            with self.assertRaisesRegex(ValueError,'mixed fit'):view.results(out,v,fig)
            self.assertEqual(list(fig.iterdir()),[])

if __name__=='__main__':unittest.main()
