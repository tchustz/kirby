"""Alert safeguards, denominators, and persistent human decisions."""
import copy
from pathlib import Path
import tempfile
import unittest
from learning_monitor import read_settings,prepare,build_metrics,detect,update_register,success_metrics,guide_view,run

class LearningMonitorChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=read_settings();cls.cfg['product_grouping']='family'
        cls.data,_=prepare(cls.cfg)
        cls.op,cls.base,cls.sample,cls.qa,cls.fb=build_metrics(cls.data,cls.cfg)
        cls.flags,cls.ev=detect(cls.data,cls.cfg,cls.op,cls.base,cls.sample,cls.qa,cls.fb)
    def detect_with(self,cfg=None,op=None,sample=None):
        return detect(self.data,cfg or self.cfg,op if op is not None else self.op,self.base,
                      sample if sample is not None else self.sample,self.qa,self.fb)[0]
    def test_population_and_sample_denominators(self):
        a=self.sample[self.sample.Product.eq('All')&self.sample.Reason.eq('All')]
        self.assertEqual(a.sample_n.sum(),20000)
        row=self.op[self.op.Queue.eq('General Care')&self.op.week.eq('2026-09-21')].iloc[0]
        d=self.data['ops'];d=d[d.Queue.eq('General Care')&d.Date.between('2026-09-21','2026-09-27')]
        self.assertAlmostEqual(row.AHT_min,(d['Answered contacts']*d['Average handle minutes']).sum()/d['Answered contacts'].sum())
        self.assertAlmostEqual(row.abandonment,d['Abandoned contacts'].sum()/d['Offered contacts'].sum())
    def test_known_signals_and_unavailable_path(self):
        self.assertTrue(((self.flags.queue=='General Care')&(self.flags.signal=='Queue handling time increase')).any())
        self.assertTrue((self.flags.reason=='Connectivity').any())
        self.assertFalse(((self.flags.queue=='General Care')&(self.flags.signal=='Eligible calls using generic troubleshooting')).any())
        self.assertTrue((self.ev.Status=='INSUFFICIENT / STALE').any())
    def test_one_week_is_not_sustained(self):
        op=self.op.copy();latest=op[op.Queue.eq('General Care')&op.complete_week].week.max()
        op.loc[op.Queue.eq('General Care')&op.week.eq(latest),'AHT_min']=self.base.loc['General Care','AHT_min']
        f=self.detect_with(op=op)
        self.assertFalse(((f.queue=='General Care')&(f.signal=='Queue handling time increase')).any())
    def test_missing_latest_week_suppresses_flags(self):
        op=self.op.copy();latest=op[op.Queue.eq('General Care')&op.complete_week].week.max()
        op.loc[op.Queue.eq('General Care')&op.week.eq(latest),'complete_week']=False
        self.assertFalse(self.detect_with(op=op).queue.eq('General Care').any())
    def test_stale_sources_suppress_new_flags(self):
        cfg=copy.deepcopy(self.cfg);cfg['as_of']='2026-11-06'
        self.assertTrue(self.detect_with(cfg=cfg).empty)
    def test_small_samples_do_not_trigger_sample_flags(self):
        s=self.sample.copy();s['sample_n']=0;s['eligible_n']=0
        f=self.detect_with(sample=s)
        self.assertFalse(f.evidence_type.eq('Sampled calls').any())
        self.assertTrue(f.evidence_type.eq('Full daily population').any())
    def test_log_deduplication_and_preserved_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'issues.csv';f=self.flags.head(1)
            log,_=update_register(f,path);log.loc[0,'owner']='Agreed owner';log.loc[0,'notes']='Needs Product review'
            first=log.loc[0,'first_detected_at'];log.to_csv(path,index=False)
            f=f.copy();f['observed_at']='2026-11-07T12:00:00Z'
            log,_=update_register(f,path)
            self.assertEqual(len(log),1);self.assertEqual(log.loc[0,'first_detected_at'],first)
            self.assertEqual(log.loc[0,'owner'],'Agreed owner');self.assertEqual(log.loc[0,'notes'],'Needs Product review')
            log.to_csv(path,index=False);log,register=update_register(f.iloc[0:0],path)
            self.assertEqual(log.loc[0,'status'],'Needs investigation')
            self.assertIn('Not flagged',register.loc[0,'Signal this run'])
    def test_success_requires_validated_pilot_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            log,_=update_register(self.flags.head(1),Path(tmp)/'log.csv')
            self.assertTrue(success_metrics(log).Result.eq('Not measurable yet').all())
            log.loc[0,['mode','first_detected_at','validated_onset_at','escalated_at','intervention_agreed_at']]=[
                'pilot','2026-10-05','2026-10-02','2026-10-07','2026-10-09']
            m=success_metrics(log)
            self.assertEqual(m.iloc[0].Result,'3.0 median days');self.assertEqual(m.iloc[1].Result,'4.0 median days')
            self.assertEqual(m.iloc[2].Result,'100%')
            log.loc[0,'validated_onset_at']='2026-10-06'
            self.assertEqual(success_metrics(log).iloc[0]['Invalid date order'],1)
    def test_guides_default_off(self):
        self.assertTrue(guide_view(self.data,self.cfg).empty)
    def test_bad_config_does_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=copy.deepcopy(self.cfg);cfg['output_folder']=str(Path(tmp)/'out');cfg['consecutive_weeks']=0
            with self.assertRaises(ValueError):run(cfg)
            self.assertFalse(Path(cfg['output_folder']).exists())
if __name__=='__main__':unittest.main()
