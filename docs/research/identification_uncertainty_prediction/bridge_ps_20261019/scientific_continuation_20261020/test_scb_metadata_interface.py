"""Synthetic metadata ONLY, not SCB subjects, measurements or forecasts."""
import unittest
from scb_metadata_interface import audit_metadata,cost_counts

def fixture():
 t={n:[] for n in ('entities','frame_load_join','response_catalog','reference_catalog','origins','splits')}
 for i in range(3):
  test='ARTIFICIAL_TEST_'+str(i);t['entities'].append(dict(study_id='ARTIFICIAL_ONLY_NOT_SCB_COUNTS',road_section_id='fixture',core_id='FAKE_CORE_'+str(i),specimen_id='FAKE_SPEC_'+str(i),test_id=test,entity_source_asset_id='fixture-provenance'))
  for n in (0,10,20):
   t['frame_load_join'].append(dict(test_id=test,pair_id=str(n),left_frame_id='L'+str(n),right_frame_id='R'+str(n),left_asset_id='fixture-L',right_asset_id='fixture-R',cycle=n,phase_fraction=.25,roi_id='fixture-roi',registration_id='fixture-common-calibration',machine_source_asset_id='fixture-load',sync_source_asset_id='fixture-sync'))
   t['response_catalog'].append(dict(test_id=test,cycle=n,phase_fraction=.25,roi_id='fixture-roi',feature_source_max_cycle=n,response_asset_id='fixture-response',geometry_asset_id='fixture-current-geometry',geometry_unit='mm',feature_pipeline_id='fixture-origin-only-pipeline'))
  t['reference_catalog'].append(dict(reference_id=test+'reference',test_id=test,cycle=30,roi_id='fixture-roi',unit='mm',independent_of_dic=True,reference_source_asset_id='fixture-reference-provenance',reference_resolution_mm=None))
  t['origins'].append(dict(test_id=test,origin_cycle=20,history_cycles=[0,10,20],phase_fraction=.25,roi_id='fixture-roi',load_plan_known_at_cycle=20,load_plan_until_cycle=30,load_plan_asset_id='fixture-known-plan'))
  t['splits'].append(dict(fold_id='ARTIFICIAL_OUTER_FOLD',test_id=test,role='evaluation' if i==0 else 'development'))
 return t

class MetadataTests(unittest.TestCase):
 def test_join_and_grouping_without_scientific_payloads(self):
  r=audit_metadata(fixture(),[10],.01);self.assertEqual(r['counts_verified']['origin_horizon_pairs'],3);self.assertFalse(r['scientific_values_opened']);self.assertEqual(r['status'],'METADATA_CONSISTENT_NOT_EXECUTION_AUTHORITY')
 def test_empty_actual_tables_are_unknown_not_six_independent_cores(self):
  r=audit_metadata({},[],None);self.assertIsNone(r['counts_verified']);self.assertEqual(len(r['missing_tables']),6)
 def test_mother_core_leakage_rejected(self):
  t=fixture();t['entities'][1]['core_id']=t['entities'][0]['core_id']
  with self.assertRaises(ValueError):audit_metadata(t,[10],.01)
 def test_camera_sampling_cannot_supply_missing_phase_or_sync(self):
  for change in ('phase','source'):
   t=fixture()
   if change=='phase':t['response_catalog'][0]['phase_fraction']=.5
   else:t['frame_load_join'][0]['sync_source_asset_id']=''
   with self.assertRaises(ValueError):audit_metadata(t,[10],.01)
 def test_future_response_or_realized_load_leak_rejected(self):
  t=fixture();t['response_catalog'][0]['feature_source_max_cycle']=20
  with self.assertRaises(ValueError):audit_metadata(t,[10],.01)
  t=fixture();t['origins'][0]['load_plan_known_at_cycle']=30
  with self.assertRaises(ValueError):audit_metadata(t,[10],.01)
 def test_independent_reference_and_same_roi_required(self):
  for change in ('dic','roi'):
   t=fixture()
   if change=='dic':t['reference_catalog'][0]['independent_of_dic']=False
   else:t['reference_catalog'][0]['roi_id']='other-roi'
   with self.assertRaises(ValueError):audit_metadata(t,[10],.01)
 def test_missing_measurement_repeat_or_resolution_not_blanket_point_forecast_block(self):
  r=audit_metadata(fixture(),[10],.01);self.assertFalse(r['reference_effect_tolerance_ready']);self.assertFalse(r['full_R_Q_identification_required_for_state_contrast']);self.assertEqual(r['measurement_repeat_status'],'not asserted by this interface')
 def test_payload_and_terminal_normalization_forbidden_in_mechanical_interface(self):
  for k in ('future_length_mm','N_over_Nf','final_crack_path'):
   t=fixture();t['origins'][0][k]='artificial-forbidden'
   with self.assertRaises(ValueError):audit_metadata(t,[10],.01)
 def test_unknown_runtime_not_inferred_from_old_1800s(self):
  r=cost_counts({});self.assertIsNone(r['total_wall_seconds']);self.assertFalse(r['scientific_run_authorized'])
  r=cost_counts(dict(cores=3,horizon_count=2,origin_horizon_pairs=18,source_bytes=1000,dic_processing_seconds_per_pair=0,reference_hours=0));self.assertEqual(r['total_closed_form_fits'],42);self.assertEqual(r['distribution_forecasts_and_CRPS_rows'],108);self.assertIsNone(r['total_wall_seconds'])

if __name__=='__main__':unittest.main()
