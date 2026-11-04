import 'dart:convert';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Finite dated reminders. Reporting cancels all three IDs for that occurrence.
class Reminders {
  Reminders({
    FlutterLocalNotificationsPlugin? plugin,
    DateTime Function()? clock,
  }) : _plugin = plugin ?? FlutterLocalNotificationsPlugin(),
       _now = clock ?? DateTime.now;
  final FlutterLocalNotificationsPlugin _plugin;
  final DateTime Function() _now;
  bool _ready = false;
  Future<void> Function(String, String)? onAction;
  Future<void> initialize() async {
    if (_ready) return;
    tzdata.initializeTimeZones();
    await _plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
      onDidReceiveNotificationResponse: (response) {
        if (response.payload != null) {
          onAction?.call(response.payload!, response.actionId ?? '');
        }
      },
    );
    _ready = true;
  }

  int id(String key, int part) {
    var hash = 2166136261;
    for (final unit in '$key:$part'.codeUnits) {
      hash = ((hash ^ unit) * 16777619) & 0x7fffffff;
    }
    return hash;
  }

  Future<void> handleLaunch() async {
    final launch = await _plugin.getNotificationAppLaunchDetails();
    final response = launch?.notificationResponse;
    if (launch?.didNotificationLaunchApp == true && response?.payload != null) {
      await onAction?.call(response!.payload!, response.actionId ?? '');
    }
  }

  Future<void> cancel(String key) async {
    await initialize();
    for (var part = 0; part < 3; part++) {
      await _plugin.cancel(id: id(key, part));
    }
  }

  Future<void> cancelAll() async {
    await initialize();
    await _plugin.cancelAll();
  }

  Future<bool> permission() async {
    await initialize();
    final android = _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    return await android?.requestNotificationsPermission() ?? false;
  }

  Future<void> schedule(List<Map<String, dynamic>> doses) async {
    await initialize();
    final retained = <int>{};
    for (final d in doses) {
      if (d['report'] != null || d['pending'] == true) continue;
      for (var part = 0; part < 3; part++) {
        retained.add(id(d['key'], part));
      }
    }
    for (final notification in await _plugin.pendingNotificationRequests()) {
      if (!retained.contains(notification.id)) {
        await _plugin.cancel(id: notification.id);
      }
    }
    for (final d in doses) {
      if (d['report'] != null || d['pending'] == true) continue;
      final at = DateTime.parse(d['scheduled_at']);
      if (at.isAfter(_now())) {
        await _one(d, at, 0, false);
      }
      final follow = at.add(const Duration(minutes: 30));
      if (follow.isAfter(_now())) {
        await _one(d, follow, 1, true);
      }
    }
  }

  Future<void> snooze(Map<String, dynamic> dose) async {
    await initialize();
    final at = _now().add(const Duration(minutes: 10));
    final follow = DateTime.parse(dose['scheduled_at'])
        .add(const Duration(minutes: 30));
    // One notification when a snooze and the recording follow-up coincide.
    if (at.difference(follow).inSeconds.abs() < 60) return;
    await _one(dose, at, 2, false);
  }

  Future<void> _one(
    Map<String, dynamic> dose,
    DateTime at,
    int part,
    bool follow,
  ) async {
    await _plugin.zonedSchedule(
      id: id(dose['key'], part),
      scheduledDate: tz.TZDateTime.from(at, tz.UTC),
      title: follow ? 'Record your dose' : 'CareLink reminder',
      body: follow
          ? 'Already taken your medicine? Record it here.'
          : 'Open CareLink to review your saved schedule.',
      notificationDetails: const NotificationDetails(
        android: AndroidNotificationDetails(
          'carelink_doses',
          'Dose reminders',
          channelDescription: 'Reminders for your saved schedule',
          importance: Importance.high,
          priority: Priority.high,
          actions: [
            AndroidNotificationAction(
              'taken',
              'Taken',
              showsUserInterface: true,
            ),
            AndroidNotificationAction(
              'skipped',
              'Skipped',
              showsUserInterface: true,
            ),
            AndroidNotificationAction(
              'snooze',
              '10 minutes',
              showsUserInterface: true,
            ),
          ],
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      payload: jsonEncode(dose),
    );
  }
}
