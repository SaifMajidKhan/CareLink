import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:carelink_patient/connected/models/patient_code.dart';
import 'package:carelink_patient/connected/screens/caregiver_home_screen.dart';
import 'package:carelink_patient/connected/screens/patient_request_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_connected_store.dart';

const patientId = 'CL-0123456789ABCDEF';

class CaregiverApi extends ApiClient {
  CaregiverApi() : super('https://caregiver.example.test');
  final requests = <Map<String, dynamic>>[];
  String state = 'pending';
  int doseReads = 0;

  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    if (method == 'POST' && path == '/connections') {
      requests.add(Map<String, dynamic>.from(body! as Map));
      return {'state': 'pending'};
    }
    if (method == 'GET' && path == '/connections') {
      return [
        {
          'patient': patientId,
          'patient_name': 'Amina',
          'caregiver': 'test-caregiver',
          'state': state,
        },
      ];
    }
    if (method == 'GET' && path.startsWith('/patients/$patientId/doses?')) {
      doseReads++;
      if (state != 'active') throw ApiFailure('Connection required.', 403);
      return [uiDose(status: 'taken')];
    }
    throw StateError('Unexpected request: $method $path');
  }
}

Future<void> openRequest(WidgetTester tester, CaregiverApi api) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Builder(
        builder: (context) => Scaffold(
          body: TextButton(
            onPressed: () => Navigator.of(context).push<bool>(
              MaterialPageRoute(
                builder: (_) => PatientRequestScreen(
                  api: api,
                  scan: (_) async => patientId,
                ),
              ),
            ),
            child: const Text('Open request'),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('Open request'));
  await tester.pumpAndSettle();
}

void main() {
  test('scanner accepts CareLink patient codes, with a manual ID fallback', () {
    expect(PatientCode.fromScan(PatientCode.encode(patientId)), patientId);
    expect(PatientCode.fromInput('  cl-0123456789abcdef  '), patientId);
    expect(PatientCode.fromScan(patientId), isNull);
    expect(PatientCode.fromScan('https://example.test/$patientId'), isNull);
    expect(PatientCode.fromScan('carelink:patient:CL-123'), isNull);
    expect(PatientCode.fromInput('CL-0123456789ABCDEZ'), isNull);
  });

  testWidgets('scan fills the ID and waits for the caregiver to send', (
    tester,
  ) async {
    final api = CaregiverApi();
    await openRequest(tester, api);
    await tester.tap(find.text('Scan patient QR'));
    await tester.pumpAndSettle();
    expect(find.text(patientId), findsOneWidget);
    expect(api.requests, isEmpty);
    await tester.tap(find.text('Send request'));
    await tester.pumpAndSettle();
    expect(api.requests.single, {'patient_id': patientId});
    expect(find.text('Open request'), findsOneWidget);
  });

  testWidgets('manual ID rejects mistakes and sends a normalized request', (
    tester,
  ) async {
    final api = CaregiverApi();
    await openRequest(tester, api);
    final field = find.byKey(const ValueKey('patient-id-input'));
    await tester.enterText(field, 'CL-123');
    await tester.tap(find.text('Send request'));
    await tester.pumpAndSettle();
    expect(find.textContaining('enter their full CL- ID'), findsOneWidget);
    expect(api.requests, isEmpty);
    await tester.enterText(field, 'cl-0123456789abcdef');
    await tester.tap(find.text('Send request'));
    await tester.pumpAndSettle();
    expect(api.requests.single, {'patient_id': patientId});
  });

  testWidgets('caregiver can only read active connections and loses access', (
    tester,
  ) async {
    final api = CaregiverApi();
    await tester.pumpWidget(
      MaterialApp(
        home: CaregiverHomeScreen(
          api: api,
          user: const {'id': 'test-caregiver', 'role': 'caregiver'},
          onLogout: () async {},
          onRenew: (_) async {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Waiting for patient approval'), findsOneWidget);
    await tester.tap(find.text('Amina'));
    await tester.pumpAndSettle();
    expect(api.doseReads, 0);

    api.state = 'active';
    await tester.tap(find.byTooltip('Refresh connections'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Amina'));
    await tester.pumpAndSettle();
    expect(find.text('Medicine UI'), findsOneWidget);
    expect(find.text('Reported taken'), findsOneWidget);
    expect(find.text('Record dose'), findsNothing);
    expect(find.text('Correct report'), findsNothing);

    api.state = 'removed';
    await tester.tap(find.byTooltip('Refresh patient updates'));
    await tester.pumpAndSettle();
    expect(api.doseReads, 2);
    expect(find.text('Medicine UI'), findsNothing);
    expect(find.textContaining('connection has ended'), findsOneWidget);
  });
}
