import 'package:carelink_patient/connected/screens/reading_form.dart';
import 'package:carelink_patient/connected/screens/care_screen.dart';
import 'package:carelink_patient/connected/screens/report_form.dart';
import 'package:carelink_patient/connected/screens/schedule_form.dart';
import 'package:carelink_patient/core/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_connected_store.dart';

Future<void> open(WidgetTester tester, Widget page) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light,
      home: Builder(
        builder: (context) => Scaffold(
          body: Center(
            child: FilledButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => page),
              ),
              child: const Text('Open test page'),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('Open test page'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('caregiver access changes only after patient confirmation', (
    tester,
  ) async {
    final api = UiApi()
      ..connections = [
        {'id': 'care-ui', 'caregiver_name': 'Mariam Khan', 'state': 'pending'},
      ];
    await open(tester, CareScreen(api: api));
    await uiPress(tester, find.text('Review request'));
    expect(
      find.textContaining('They cannot change your medicines or reports.'),
      findsOneWidget,
    );
    expect(api.writes, isEmpty);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(api.writes, isEmpty);
    await uiPress(tester, find.text('Review request'));
    await tester.tap(find.text('Approve connection'));
    await tester.pumpAndSettle();
    expect(api.writes.single.path, '/connections/care-ui');
    expect(api.writes.single.body['action'], 'accept');
  });

  testWidgets(
    'dose form still queues a skipped report with the correct fields',
    (tester) async {
      final store = UiStore(UiApi());
      var notificationCancelled = false;
      await open(
        tester,
        ReportForm(
          dose: uiDose(),
          store: store,
          afterSave: () async {
            notificationCancelled = true;
          },
        ),
      );
      await uiPress(tester, find.text('Skipped'));
      await tester.tap(find.text('Save record'));
      await tester.pumpAndSettle();
      final body = store.queued.single['body'] as Map;
      expect(body['outcome'], 'skipped');
      expect(body['taken_at'], isNull);
      expect(body['approximate'], isFalse);
      expect(body['expected_version'], 0);
      expect(notificationCancelled, isTrue);
      expect(find.text('Open test page'), findsOneWidget);
    },
  );

  testWidgets(
    'correcting a report still requires a reason and server version',
    (tester) async {
      final store = UiStore(UiApi());
      await open(
        tester,
        ReportForm(
          dose: uiDose(status: 'taken'),
          store: store,
          afterSave: () async {},
        ),
      );
      await uiPress(tester, find.text('Skipped'));
      await tester.tap(find.text('Save record'));
      await tester.pumpAndSettle();
      expect(store.queued, isEmpty);
      await uiPress(tester, find.byType(TextField));
      await tester.enterText(
        find.byType(TextField),
        'Correcting my earlier tap',
      );
      await tester.tap(find.text('Save record'));
      await tester.pumpAndSettle();
      expect(store.queued.single['body']['expected_version'], 1);
      expect(
        store.queued.single['body']['reason'],
        'Correcting my earlier tap',
      );
    },
  );

  testWidgets('medicine form checks required details before API writes', (
    tester,
  ) async {
    final api = UiApi();
    await open(tester, ScheduleForm(api: api));
    await tester.tap(find.text('Review and save'));
    await tester.pumpAndSettle();
    expect(api.writes, isEmpty);
    expect(find.text('Enter the medicine name.'), findsOneWidget);
    expect(find.text('Enter your prescribed instructions.'), findsOneWidget);
  });

  testWidgets(
    'reading form preserves blood-pressure fields and measurement time',
    (tester) async {
      final api = UiApi();
      await open(tester, ReadingForm(api: api));
      await tester.enterText(
        find.byKey(const ValueKey('reading-value')),
        '120',
      );
      await tester.enterText(
        find.byKey(const ValueKey('reading-secondary')),
        '80',
      );
      await tester.tap(find.text('Save reading'));
      await tester.pumpAndSettle();
      final body = api.writes.single.body;
      expect(body['kind'], 'blood_pressure');
      expect(body['value'], 120);
      expect(body['secondary'], 80);
      expect(body['unit'], 'mmHg');
      expect(DateTime.parse(body['measured_at']).isUtc, isTrue);
    },
  );

  testWidgets('changing glucose units clears the old numeric value', (
    tester,
  ) async {
    await open(tester, ReadingForm(api: UiApi()));
    await tester.tap(find.byKey(const ValueKey('reading-kind')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Blood glucose').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('reading-value')), '100');
    await uiPress(tester, find.byKey(const ValueKey('reading-unit-mg/dL')));
    await tester.tap(find.text('mmol/L').last);
    await tester.pumpAndSettle();
    final field = tester.widget<TextFormField>(
      find.byKey(const ValueKey('reading-value')),
    );
    expect(field.controller!.text, isEmpty);
    expect(find.byKey(const ValueKey('reading-unit-mmol/L')), findsOneWidget);
  });
}
