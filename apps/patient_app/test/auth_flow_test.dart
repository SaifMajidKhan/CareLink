import 'package:carelink_patient/connected/auth/account_role.dart';
import 'package:carelink_patient/connected/connected_app.dart';
import 'package:carelink_patient/connected/config/app_config.dart';
import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:carelink_patient/connected/screens/caregiver_home_screen.dart';
import 'package:carelink_patient/connected/screens/guest_home_screen.dart';
import 'package:carelink_patient/connected/screens/sign_in_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

class AuthApi extends ApiClient {
  AuthApi() : super(AppConfig.apiBase);
  final registrations = <Map<String, dynamic>>[];
  ApiFailure? registrationFailure;
  var role = 'patient';
  var providerChecks = 0;

  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    if (path == '/auth/providers') {
      providerChecks++;
      return {
        'google': {'available': false},
        'facebook': {'available': false},
      };
    }
    if (path == '/auth/register') {
      registrations.add(Map<String, dynamic>.from(body! as Map));
      if (registrationFailure != null) throw registrationFailure!;
      role = registrations.last['role'] as String;
    }
    return {
      'token': 'test-token',
      'user': {'id': 'test-user', 'name': 'Member', 'role': role},
    };
  }
}

Future<void> press(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    250,
    scrollable: find.byType(Scrollable).first,
  );
  await Scrollable.ensureVisible(tester.element(finder), alignment: 0.5);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> fillRegistration(WidgetTester tester) async {
  await tester.enterText(find.byKey(const ValueKey('auth-name')), '  Member  ');
  await tester.enterText(
    find.byKey(const ValueKey('auth-email')),
    'MEMBER@EXAMPLE.TEST',
  );
  await tester.enterText(
    find.byKey(const ValueKey('auth-password')),
    'A-valid-password-123',
  );
  await tester.scrollUntilVisible(
    find.byKey(const ValueKey('auth-confirmation')),
    250,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.enterText(
    find.byKey(const ValueKey('auth-confirmation')),
    'A-valid-password-123',
  );
}

void main() {
  testWidgets('signed-out app opens as guest without a sign-in form', (
    tester,
  ) async {
    FlutterSecureStorage.setMockInitialValues({});
    await tester.pumpWidget(const ConnectedCareLinkApp());
    await tester.pumpAndSettle();
    expect(find.byType(GuestHomeScreen), findsOneWidget);
    expect(find.byType(TextFormField), findsNothing);
    expect(find.textContaining('FYP demonstration'), findsNothing);
    expect(find.text('Server connection'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('a saved caregiver session opens the caregiver home', (
    tester,
  ) async {
    FlutterSecureStorage.setMockInitialValues({
      'carelink_session': '{"token":"test-token","server":"http://invalid.example.test","user":{"id":"test-caregiver","name":"Member","role":"caregiver"}}',
    });
    await tester.pumpWidget(const ConnectedCareLinkApp());
    await tester.pumpAndSettle();
    expect(find.byType(CaregiverHomeScreen), findsOneWidget);
    expect(find.text('Add a patient'), findsOneWidget);
    expect(find.text('Today'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    FlutterSecureStorage.setMockInitialValues({});
  });

  for (final destination in ['Today', 'History', 'Profile']) {
    testWidgets('guest $destination action asks for an account', (
      tester,
    ) async {
      bool? choice;
      await tester.pumpWidget(
        MaterialApp(
          home: GuestHomeScreen(
            onAuthenticate: (register, role) async {
              choice = register;
              expect(role, AccountRole.patient);
            },
          ),
        ),
      );
      await tester.tap(find.text(destination));
      await tester.pumpAndSettle();
      expect(find.text('Your care starts here'), findsOneWidget);
      expect(choice, isNull);
      await tester.tap(find.widgetWithText(FilledButton, 'Create account'));
      await tester.pumpAndSettle();
      expect(choice, isTrue);
    });
  }

  testWidgets('caregiver entry can be dismissed or start caregiver sign-in', (
    tester,
  ) async {
    final choices = <(bool, AccountRole)>[];
    await tester.pumpWidget(
      MaterialApp(
        home: GuestHomeScreen(
          onAuthenticate: (register, role) async {
            choices.add((register, role));
          },
        ),
      ),
    );
    await tester.tap(find.text('I’m a caregiver'));
    await tester.pumpAndSettle();
    expect(find.text('Caregiver access'), findsOneWidget);
    await tester.tap(find.text('Maybe later'));
    await tester.pumpAndSettle();
    expect(choices, isEmpty);
    await tester.tap(find.text('I’m a caregiver'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, 'Sign in'));
    await tester.pumpAndSettle();
    expect(choices, [(false, AccountRole.caregiver)]);
  });

  testWidgets('guest layout and sign-in prompt fit a small phone', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 700);
    final details = <FlutterErrorDetails>[];
    final handler = FlutterError.onError;
    FlutterError.onError = (error) {
      details.add(error);
      handler?.call(error);
    };
    addTearDown(() => FlutterError.onError = handler);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(home: GuestHomeScreen(onAuthenticate: (_, _) async {})),
    );
    expect(find.text('Get started').hitTestable(), findsOneWidget);
    expect(find.text('I’m a caregiver').hitTestable(), findsOneWidget);
    await tester.tap(find.text('History'));
    await tester.pumpAndSettle();
    expect(
      tester.takeException(),
      isNull,
      reason: details.map((e) => e.toString()).join('\n'),
    );
  });

  testWidgets(
    'invalid registration explains fields before contacting the API',
    (tester) async {
      final api = AuthApi();
      await tester.pumpWidget(
        MaterialApp(
          home: SignInScreen(
            initialRegister: true,
            api: api,
            onSignedIn: (_, _) async {},
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('auth-email')),
        'invalid',
      );
      await tester.enterText(
        find.byKey(const ValueKey('auth-password')),
        'short',
      );
      await press(tester, find.widgetWithText(FilledButton, 'Create account'));
      expect(api.registrations, isEmpty);
      expect(find.text('Enter a valid email address.'), findsOneWidget);
      expect(find.text('Use at least 10 characters.'), findsWidgets);
      expect(find.text('Passwords do not match.'), findsOneWidget);
    },
  );

  testWidgets('valid registration uses the hosted API and normalized details', (
    tester,
  ) async {
    final api = AuthApi();
    String? signedInto;
    await tester.pumpWidget(
      MaterialApp(
        home: SignInScreen(
          initialRegister: true,
          api: api,
          onSignedIn: (server, _) async {
            signedInto = server;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();
    await fillRegistration(tester);
    await press(tester, find.widgetWithText(FilledButton, 'Create account'));
    expect(api.registrations.single, {
      'name': 'Member',
      'email': 'member@example.test',
      'password': 'A-valid-password-123',
      'role': 'patient',
    });
    expect(signedInto, 'https://carelink-api-orjq.onrender.com');
    expect(find.text('Server connection'), findsNothing);
    expect(find.textContaining('fictional'), findsNothing);
  });

  testWidgets('backend field errors are shown beside the affected input', (
    tester,
  ) async {
    final api = AuthApi()
      ..registrationFailure = ApiFailure('Email needs checking', 422, {
        'email': 'Please check this email address.',
      });
    await tester.pumpWidget(
      MaterialApp(
        home: SignInScreen(
          initialRegister: true,
          api: api,
          onSignedIn: (_, _) async {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    await fillRegistration(tester);
    await press(tester, find.widgetWithText(FilledButton, 'Create account'));
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('auth-email')),
      -250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Please check this email address.'), findsOneWidget);
    expect(find.textContaining('(422)'), findsNothing);
  });

  testWidgets('caregiver registration uses the caregiver role and email', (
    tester,
  ) async {
    final api = AuthApi();
    String? signedInRole;
    await tester.pumpWidget(
      MaterialApp(
        home: SignInScreen(
          initialRegister: true,
          registrationRole: AccountRole.caregiver,
          api: api,
          onSignedIn: (_, result) async {
            signedInRole = result['user']['role'] as String;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();
    await fillRegistration(tester);
    await press(tester, find.widgetWithText(FilledButton, 'Create account'));
    expect(api.registrations.single['role'], 'caregiver');
    expect(signedInRole, 'caregiver');
    expect(api.providerChecks, 0);
  });

  testWidgets('social buttons do not claim unconfigured providers are ready', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: SignInScreen(api: AuthApi(), onSignedIn: (_, _) async {}),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Continue with Facebook'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    for (final provider in ['Google', 'Facebook']) {
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Continue with $provider'),
            )
            .onPressed,
        isNull,
      );
    }
  });
}
