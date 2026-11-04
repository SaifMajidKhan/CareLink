import 'package:carelink_patient/connected/screens/dashboard.dart';
import 'package:carelink_patient/connected/screens/care_identity_screen.dart';
import 'package:carelink_patient/connected/widgets/connected_dose_card.dart';
import 'package:carelink_patient/core/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'fake_connected_store.dart';

Future<void> launch(
  WidgetTester tester,
  UiStore store, {
  double scale = 1,
  Future<void> Function(Map<String, dynamic>)? onProfileChanged,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context)
            .copyWith(textScaler: TextScaler.linear(scale)),
        child: child!,
      ),
      home: Dashboard(
        store: store,
        user: const {'name': 'Amina Khan', 'condition': 'both'},
        onLogout: () async {},
        onRenew: (_) async {},
        onProfileChanged: onProfileChanged,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(installNotificationFake);

  testWidgets('empty Today has a working medicine entry action', (
    tester,
  ) async {
    await launch(tester, UiStore(UiApi()));
    await uiPress(tester, find.text('Add your first medicine'));
    expect(find.byKey(const ValueKey('schedule-name')), findsOneWidget);
    expect(find.text('Dose and instructions'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Profile keeps QR behind the care-ID page', (tester) async {
    await launch(tester, UiStore(UiApi()));
    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();
    expect(find.byType(QrImageView), findsNothing);
    await uiPress(tester, find.text('Your care ID'));
    expect(find.byType(CareIdentityScreen), findsOneWidget);
    expect(find.byType(QrImageView), findsOneWidget);
    expect(find.text('Copy patient ID'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
    'profile edits return to the patient view and notify secure-session owner',
    (tester) async {
      final api = UiApi();
      Map<String, dynamic>? saved;
      await launch(
        tester,
        UiStore(api),
        onProfileChanged: (value) async {
          saved = value;
        },
      );
      await tester.tap(find.text('Profile'));
      await tester.pumpAndSettle();
      await uiPress(tester, find.text('Edit profile'));
      await tester.enterText(find.byType(TextFormField).first, 'Amina Updated');
      await tester.tap(find.text('Save changes'));
      await tester.pumpAndSettle();
      expect(api.writes.single.path, '/me');
      expect(saved?['name'], 'Amina Updated');
      expect(find.text('Amina Updated'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );

  for (final tab in ['Today', 'History', 'Profile']) {
    testWidgets('$tab fits a small phone with larger text', (tester) async {
      tester.view.physicalSize = const Size(320, 740);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final errors = <FlutterErrorDetails>[];
      final handler = FlutterError.onError;
      FlutterError.onError = (error) {
        errors.add(error);
        handler?.call(error);
      };
      addTearDown(() => FlutterError.onError = handler);
      await launch(tester, UiStore(UiApi()), scale: 1.8);
      if (tab != 'Today') {
        await tester.tap(find.text(tab));
        await tester.pumpAndSettle();
      }
      await tester.drag(find.byType(Scrollable).first, const Offset(0, -450));
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: errors.map((e) => e.toString()).join('\n'),
      );
      await tester.pumpWidget(const SizedBox());
    });
  }

  testWidgets(
    'pending dose cards keep the upload notice and block duplicate editing',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.light,
          home: Scaffold(
            body: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                ConnectedDoseCard(
                  dose: uiDose(status: 'taken', pending: true),
                  onRecord: () {},
                  onConflict: () {},
                ),
              ],
            ),
          ),
        ),
      );
      expect(find.text('Reported taken'), findsOneWidget);
      expect(
        find.text('Saved on this phone—waiting to upload'),
        findsOneWidget,
      );
      expect(find.text('Record dose'), findsNothing);
      expect(find.text('Correct report'), findsNothing);
    },
  );

  testWidgets('future dose cards do not invite an early report', (
    tester,
  ) async {
    final dose = uiDose(status: 'upcoming')
      ..['scheduled_at'] = DateTime.now()
          .add(const Duration(hours: 1))
          .toIso8601String();
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        home: Scaffold(
          body: ListView(
            children: [
              ConnectedDoseCard(dose: dose, onRecord: () {}, onConflict: () {}),
            ],
          ),
        ),
      ),
    );
    expect(find.text('Upcoming'), findsOneWidget);
    expect(find.text('Record dose'), findsNothing);
  });
}
