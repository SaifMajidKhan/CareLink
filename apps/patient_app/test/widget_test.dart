import 'package:flutter/material.dart';
import 'package:carelink_patient/features/medication/models/dose_history_entry.dart';

import 'fake_profile_repository.dart';

import 'package:flutter_test/flutter_test.dart';
import 'package:carelink_patient/app.dart';
import 'package:carelink_patient/features/medication/data/dose_repository.dart';
import 'package:carelink_patient/features/medication/models/dose_record.dart';

class FakeRepository implements DoseRepository {
  final records = <(String, String), DoseRecord>{};

  bool failRead = false;
  bool failSave = false;

  @override
  Future<DoseRecord?> read(
    String day, {
    String doseId = defaultDemoDoseId,
  }) async {
    if (failRead) throw StateError('read failed');

    return records[(day, doseId)];
  }

  @override
  Future<void> save(
    String day,
    DoseRecord record, {
    String doseId = defaultDemoDoseId,
  }) async {
    if (failSave) throw StateError('write failed');

    final key = (day, doseId);

    if (records.containsKey(key)) {
      throw StateError('A report already exists for this dose.');
    }

    records[key] = record;
  }

  @override
  Future<List<DoseHistoryEntry>> readHistory() async {
    if (failRead) throw StateError('read failed');

    final entries = records.entries.map((entry) {
      return DoseHistoryEntry(
        scheduledDay: entry.key.$1,
        doseId: entry.key.$2,
        record: entry.value,
      );
    }).toList();

    entries.sort((a, b) {
      final dateOrder = b.scheduledDay.compareTo(a.scheduledDay);

      return dateOrder != 0 ? dateOrder : a.doseId.compareTo(b.doseId);
    });

    return entries;
  }
}

Future<void> launch(WidgetTester tester, FakeRepository repository) async {
  await tester.pumpWidget(
    CareLinkApp(repository: repository, profiles: FakeProfileRepository()),
  );
  await tester.pumpAndSettle();
}

Future<void> press(WidgetTester tester, String label) async {
  final target = label == 'Record dose'
      ? find.text(label).first
      : find.text(label);

  if (target.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      target,
      250,
      scrollable: find.byType(Scrollable).first,
    );
  }
  await Scrollable.ensureVisible(tester.element(target), alignment: 0.5);

  await tester.pumpAndSettle();
  await tester.tap(target);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Cancel leaves storage unchanged', (tester) async {
    final repository = FakeRepository();
    await launch(tester, repository);
    await press(tester, 'Record dose');

    final saveButton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Save demo record'),
    );
    expect(saveButton.onPressed, isNull);

    await press(tester, 'Taken');
    await press(tester, 'Cancel');

    expect(find.text('Not confirmed'), findsNWidgets(3));
    expect(repository.records, isEmpty);

    await tester.pumpWidget(const SizedBox());
  });

  for (final choice in ['Taken', 'Skipped']) {
    testWidgets('$choice survives screen recreation', (tester) async {
      final repository = FakeRepository();
      await launch(tester, repository);
      await press(tester, 'Record dose');
      await press(tester, choice);
      await press(tester, 'Save demo record');

      final label = choice == 'Taken' ? 'Reported taken' : 'Reported skipped';

      expect(find.text(label), findsOneWidget);

      await tester.pumpWidget(const SizedBox());
      await launch(tester, repository);

      expect(find.text(label), findsOneWidget);
      expect(find.text('Record dose'), findsNWidgets(2));
      expect(repository.records.length, 1);

      await tester.pumpWidget(const SizedBox());
    });
  }

  testWidgets('Save failure retains form and allows retry', (tester) async {
    final repository = FakeRepository()..failSave = true;
    await launch(tester, repository);
    await press(tester, 'Record dose');
    await press(tester, 'Skipped');
    await press(tester, 'Save demo record');

    expect(
      find.text('Not saved. Please try again. Your choices are still here.'),
      findsOneWidget,
    );
    expect(repository.records, isEmpty);

    repository.failSave = false;
    await press(tester, 'Save demo record');

    expect(find.text('Reported skipped'), findsOneWidget);

    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Read failure blocks reporting until retry succeeds', (
    tester,
  ) async {
    final repository = FakeRepository()..failRead = true;
    await launch(tester, repository);

    expect(find.text('Record dose'), findsNothing);

    repository.failRead = false;
    await press(tester, 'Retry loading');

    expect(find.text('Record dose'), findsNWidgets(3));

    await tester.pumpWidget(const SizedBox());
  });
}
