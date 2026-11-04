import 'package:carelink_patient/connected/models/day_summary.dart';
import 'package:carelink_patient/connected/utils/care_format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('daily counts keep unanswered and future doses separate from skipped reports', () {
    final summary = DaySummary([
      {'status': 'not_confirmed'},
      {'status': 'upcoming'},
      {'status': 'taken'},
      {'status': 'skipped'},
      {
        'status': 'not_confirmed',
        'pending': true,
        'report': {'outcome': 'taken'},
      },
    ]);
    expect(summary.total, 5);
    expect(summary.taken, 2);
    expect(summary.skipped, 1);
    expect(summary.unconfirmed, 1);
    expect(summary.upcoming, 1);
    expect(summary.reported, 3);
    expect(summary.pending, 1);
  });
  test('patients see readable dates, times and relative update text', () {
    final now = DateTime(2026, 11, 4, 8, 5);
    expect(CareFormat.clock('08:00'), '8:00 AM');
    expect(CareFormat.clock('20:30'), '8:30 PM');
    expect(
      CareFormat.stamp(now.toIso8601String(), now: now),
      'Today · 8:05 AM',
    );
    expect(
      CareFormat.updated(
        now.subtract(const Duration(minutes: 12)).toIso8601String(),
        now: now,
      ),
      'Updated 12 min ago',
    );
    expect(CareFormat.condition(''), 'Your personal care space');
  });
  test('initials preserve complete Unicode characters in names', () {
    expect(CareFormat.initials('Amina Khan'), 'AK');
    expect(CareFormat.initials('👩🏽‍⚕️ Aman'), '👩🏽‍⚕️A');
    expect(CareFormat.initials(''), 'CL');
  });
}
