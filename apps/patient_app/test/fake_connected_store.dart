import 'package:carelink_patient/connected/data/account_store.dart';
import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_test/flutter_test.dart';

class UiApi extends ApiClient {
  UiApi() : super('https://ui.example.test');
  List<Map<String, dynamic>> doses = [],
      readings = [],
      schedules = [],
      connections = [];
  final writes = <({String path, Map<String, dynamic> body})>[];
  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    if (method != 'GET') {
      final data = Map<String, dynamic>.from(body! as Map);
      writes.add((path: path, body: data));
      if (path == '/me') {
        return {'id': 'patient-ui', 'role': 'patient', ...data};
      }
      return {'id': 'saved-ui-record', ...data};
    }
    if (path.contains('/doses?')) return doses;
    if (path.endsWith('/readings')) return readings;
    if (path.endsWith('/schedules')) return schedules;
    if (path == '/connections') return connections;
    return <Map<String, dynamic>>[];
  }
}

class UiStore extends AccountStore {
  UiStore(UiApi api) : super(api, 'patient-ui');
  final memory = <String, dynamic>{};
  final queued = <Map<String, dynamic>>[];
  @override
  Future<void> sync() async {}
  @override
  Future<void> cache(String key, dynamic body) async {
    memory[key] = body;
  }

  @override
  Future<Map<String, dynamic>?> cached(String key) async =>
      memory.containsKey(key)
      ? {
          'data': memory[key],
          'updated': DateTime.now().toUtc().toIso8601String(),
        }
      : null;
  @override
  Future<List<Map<String, dynamic>>> pending() async => queued;
  @override
  Future<void> queue(String key, Map<String, dynamic> body) async {
    if (queued.any((row) => row['key'] == key)) {
      throw StateError('Duplicate test report');
    }
    queued.add({'key': key, 'body': body});
  }
}

Map<String, dynamic> uiDose({
  String status = 'not_confirmed',
  bool pending = false,
}) => {
  'key': 'dose-ui',
  'schedule_id': 'medicine-ui',
  'day': dayKey(DateTime.now()),
  'time': '08:00',
  'name': 'Medicine UI',
  'instructions': 'Instructions from care plan',
  'timezone': 'Asia/Karachi',
  'scheduled_at': DateTime.now()
      .subtract(const Duration(hours: 1))
      .toIso8601String(),
  'status': status,
  'pending': pending,
  'report': status == 'taken' || status == 'skipped'
      ? {
          'outcome': status,
          'version': 1,
          'recorded_at': DateTime.now().toUtc().toIso8601String(),
          if (status == 'taken')
            'taken_at': DateTime.now().toUtc().toIso8601String(),
        }
      : null,
};

void installNotificationFake() {
  AndroidFlutterLocalNotificationsPlugin.registerWith();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
        const MethodChannel('dexterous.com/flutter/local_notifications'),
        (call) async {
          if (call.method == 'initialize') return true;
          if (call.method == 'getNotificationAppLaunchDetails') {
            return {'notificationLaunchedApp': false};
          }
          if (call.method == 'pendingNotificationRequests') return <dynamic>[];
          return null;
        },
      );
}

Future<void> uiPress(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      finder,
      250,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await Scrollable.ensureVisible(tester.element(finder), alignment: 0.5);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}
