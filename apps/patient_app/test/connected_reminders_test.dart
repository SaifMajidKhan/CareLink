import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/timezone.dart';
import 'package:carelink_patient/connected/data/reminders.dart';

class FakeNotifications implements FlutterLocalNotificationsPlugin {
  final cancelled = <int>[];
  final scheduled = <int, DateTime>{};
  final pending = <PendingNotificationRequest>[];
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
  @override
  Future<bool?> initialize({
    required InitializationSettings settings,
    DidReceiveNotificationResponseCallback? onDidReceiveNotificationResponse,
    DidReceiveBackgroundNotificationResponseCallback?
    onDidReceiveBackgroundNotificationResponse,
  }) async => true;
  @override
  Future<List<PendingNotificationRequest>>
  pendingNotificationRequests() async => pending;
  @override
  Future<void> cancel({required int id, String? tag}) async {
    cancelled.add(id);
  }

  @override
  Future<void> zonedSchedule({
    required int id,
    required TZDateTime scheduledDate,
    required NotificationDetails notificationDetails,
    required AndroidScheduleMode androidScheduleMode,
    String? title,
    String? body,
    String? payload,
    DateTimeComponents? matchDateTimeComponents,
  }) async {
    scheduled[id] = scheduledDate.toUtc();
  }
}

void main() {
  final now = DateTime.utc(2026, 11, 1, 12);
  Map<String, dynamic> dose(DateTime at) => {
    'key': 'dose-1',
    'scheduled_at': at.toIso8601String(),
  };
  test('refresh retains a snooze for an unresolved overdue dose', () async {
    final plugin = FakeNotifications();
    final service = Reminders(plugin: plugin, clock: () => now);
    final snooze = service.id('dose-1', 2);
    plugin.pending.add(
      PendingNotificationRequest(snooze, 'Snoozed', null, null),
    );
    plugin.pending.add(
      const PendingNotificationRequest(123, 'Stale', null, null),
    );
    await service.schedule([dose(now.subtract(const Duration(hours: 2)))]);
    expect(plugin.cancelled, contains(123));
    expect(plugin.cancelled, isNot(contains(snooze)));
    expect(plugin.scheduled, isEmpty);
  });
  test(
    'future dose has a reminder and only one automatic 30-minute follow-up',
    () async {
      final plugin = FakeNotifications();
      final service = Reminders(plugin: plugin, clock: () => now);
      final due = now.add(const Duration(hours: 1));
      await service.schedule([dose(due)]);
      expect(plugin.scheduled.length, 2);
      expect(plugin.scheduled[service.id('dose-1', 0)], due);
      expect(
        plugin.scheduled[service.id('dose-1', 1)],
        due.add(const Duration(minutes: 30)),
      );
    },
  );
  test('report cancellation removes reminder follow-up and snooze', () async {
    final plugin = FakeNotifications();
    final service = Reminders(plugin: plugin, clock: () => now);
    await service.cancel('dose-1');
    expect(plugin.cancelled.toSet(), {
      for (var i = 0; i < 3; i++) service.id('dose-1', i),
    });
  });
  test(
    'snooze does not duplicate a follow-up due in the same minute',
    () async {
      final plugin = FakeNotifications();
      final service = Reminders(plugin: plugin, clock: () => now);
      await service.snooze(dose(now.subtract(const Duration(minutes: 20))));
      expect(plugin.scheduled, isEmpty);
      await service.snooze(dose(now.subtract(const Duration(hours: 1))));
      expect(
        plugin.scheduled[service.id('dose-1', 2)],
        now.add(const Duration(minutes: 10)),
      );
    },
  );
}
