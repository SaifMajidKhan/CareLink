import 'package:carelink_patient/connected/data/account_store.dart';
import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:carelink_patient/connected/screens/dashboard.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_test/flutter_test.dart';

class LogoutApi extends ApiClient {
  LogoutApi(this.failure) : super('http://10.0.2.2:8000');
  final ApiFailure failure;
  int logoutCalls = 0;
  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    if (path == '/auth/logout') {
      logoutCalls++;
      throw failure;
    }
    return <Map<String, dynamic>>[];
  }
}

class LogoutStore extends AccountStore {
  LogoutStore(LogoutApi api) : super(api, 'patient-demo');
  bool cleared = false;
  final queued = <Map<String, dynamic>>[];
  @override
  Future<void> sync() async {}
  @override
  Future<void> cache(String key, dynamic body) async {}
  @override
  Future<Map<String, dynamic>?> cached(String key) async => key == 'doses'
      ? {'data': <Map<String, dynamic>>[], 'updated': '2026-11-04T00:00:00Z'}
      : null;
  @override
  Future<List<Map<String, dynamic>>> pending() async => queued;
  @override
  Future<void> clear() async {
    cleared = true;
  }
}

Future<void> openProfile(
  WidgetTester tester,
  LogoutStore store,
  Future<void> Function() onLogout,
) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Dashboard(
        store: store,
        user: const {'name': 'Demo Patient', 'condition': ''},
        onLogout: onLogout,
        onRenew: (_) async {},
      ),
    ),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.text('Profile'));
  await tester.pumpAndSettle();
  await tester.scrollUntilVisible(
    find.text('Sign out'),
    350,
    scrollable: find.byType(Scrollable).first,
  );
  await Scrollable.ensureVisible(
    tester.element(find.text('Sign out')),
    alignment: 0.5,
  );
  await tester.pumpAndSettle();
  await tester.tap(find.text('Sign out'));
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('dexterous.com/flutter/local_notifications');
  var remindersCancelled = false;
  setUp(() {
    AndroidFlutterLocalNotificationsPlugin.registerWith();
    remindersCancelled = false;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          if (call.method == 'initialize') return true;
          if (call.method == 'getNotificationAppLaunchDetails') {
            return {'notificationLaunchedApp': false};
          }
          if (call.method == 'cancelAll') remindersCancelled = true;
          return null;
        });
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });
  for (final status in [0, 401]) {
    testWidgets('local sign-out succeeds after remote logout fails ($status)', (
      tester,
    ) async {
      final api = LogoutApi(ApiFailure('Old server unavailable', status));
      final store = LogoutStore(api);
      var signedOut = false;
      await openProfile(tester, store, () async {
        signedOut = true;
      });
      expect(signedOut, isFalse);
      expect(store.cleared, isFalse);
      await tester.tap(find.widgetWithText(FilledButton, 'Sign out'));
      await tester.pumpAndSettle();
      expect(api.logoutCalls, 1);
      expect(remindersCancelled, isTrue);
      expect(store.cleared, isTrue);
      expect(signedOut, isTrue);
      await tester.pumpWidget(const SizedBox());
    });
  }
  testWidgets('unsent reports still block sign-out and are kept', (
    tester,
  ) async {
    final api = LogoutApi(ApiFailure('Old server unavailable'));
    final store = LogoutStore(api);
    store.queued.add({'key': 'unsent-demo-report'});
    var signedOut = false;
    await openProfile(tester, store, () async {
      signedOut = true;
    });
    expect(
      find.text('Upload or resolve pending reports before signing out.'),
      findsOneWidget,
    );
    expect(api.logoutCalls, 0);
    expect(store.queued, hasLength(1));
    expect(store.cleared, isFalse);
    expect(remindersCancelled, isFalse);
    expect(signedOut, isFalse);
    await tester.pumpWidget(const SizedBox());
  });
}
