"""Boundary checks for future information and unknown outcomes."""
import unittest
from datetime import datetime, timedelta, timezone
from prepare_examples import history_features, outcome, status_at

T=datetime(2026,1,15,tzinfo=timezone.utc)

def event(due, report='taken', upload=None):
    return dict(scheduled_at=due.isoformat(), eventual_report=report,
                uploaded_at=upload.isoformat() if upload else '')

class PreparationTests(unittest.TestCase):
    def test_future_upload_is_unknown(self):
        e=event(T-timedelta(hours=4),'skipped',T+timedelta(hours=1))
        self.assertEqual(status_at(e,T),'not_confirmed')
        self.assertEqual(history_features([e],T)['skipped_reports_14d'],0)

    def test_history_boundaries_and_future_events(self):
        rows=[event(T-timedelta(days=14),'taken',T),
              event(T-timedelta(days=14,seconds=1),'taken',T),
              event(T,'skipped',T)]
        result=history_features(rows,T)
        self.assertEqual(result['scheduled_doses_14d'],1)
        self.assertEqual(result['taken_reports_14d'],1)

    def test_unknown_is_not_negative(self):
        self.assertEqual(outcome([event(T+timedelta(hours=8))],T),('unknown',''))
        self.assertEqual(outcome([],T),('unknown',''))

    def test_deadline_inclusive_but_later_report_ignored(self):
        due=T+timedelta(hours=8); deadline=T+timedelta(days=3)
        self.assertEqual(outcome([event(due,'taken',deadline)],T),('all_reported_taken',0))
        self.assertEqual(outcome([event(due,'taken',deadline+timedelta(seconds=1))],T),('unknown',''))

    def test_skip_wins_but_other_days_do_not(self):
        rows=[event(T+timedelta(hours=8),'skipped',T+timedelta(hours=9)),
              event(T+timedelta(hours=20))]
        self.assertEqual(outcome(rows,T),('reported_skip',1))
        self.assertEqual(outcome([event(T+timedelta(days=1),'skipped',T+timedelta(days=1))],T),('unknown',''))

if __name__=='__main__': unittest.main()
