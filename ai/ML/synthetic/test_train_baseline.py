import csv
import tempfile
import unittest
from pathlib import Path
from prepare_examples import FEATURES
from train_baseline import load_development

class TrainingInputTests(unittest.TestCase):
    def write_rows(self, folder, rows):
        path=Path(folder)/'input.csv'
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        return path

    def rows(self):
        rows=[]
        for split in ['train','validation']:
            for label in [0,1]:
                rows.append(dict(patient_id=f'{split}-{label}',split=split,target_day='2026-01-15',
                    is_synthetic='True',eligible_for_training='True',target_reported_skip=str(label),
                    outcome='reported_skip' if label else 'all_reported_taken',
                    **{f:'1' for f in FEATURES}))
        return rows

    def test_test_labels_and_features_not_used(self):
        rows=self.rows()
        rows.append(dict(rows[0],patient_id='heldout',split='test',target_reported_skip='INVALID',
                         **{f:'INVALID' for f in FEATURES}))
        with tempfile.TemporaryDirectory() as d:
            groups,_=load_development(self.write_rows(d,rows))
            self.assertEqual(len(groups['train']),2)
            self.assertEqual(len(groups['validation']),2)

    def test_patient_overlap_rejected(self):
        rows=self.rows(); rows[2]['patient_id']=rows[0]['patient_id']
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'multiple splits'):
                load_development(self.write_rows(d,rows))

    def test_unknown_excluded_not_imputed(self):
        rows=self.rows()
        rows.append(dict(rows[0],target_day='2026-01-16',eligible_for_training='False',
                         outcome='unknown',target_reported_skip=''))
        with tempfile.TemporaryDirectory() as d:
            groups,unknown=load_development(self.write_rows(d,rows))
            self.assertEqual(len(groups['train']),2)
            self.assertEqual(unknown['train'],1)

if __name__=='__main__': unittest.main()
