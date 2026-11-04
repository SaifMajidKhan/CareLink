import 'package:carelink_patient/connected/auth/native_auth.dart';
import 'package:carelink_patient/connected/auth/social_sign_in.dart';
import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

class SocialApi extends ApiClient {
  SocialApi() : super('https://api.example.test');
  bool nativeSupported = true;
  bool configured = true;
  final exchanges = <({String path, Map body})>[];
  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    if (path == '/auth/providers') {
      return {
        for (final provider in ['google', 'facebook'])
          provider: {
            'available': configured,
            if (nativeSupported) 'native_available': configured,
          },
      };
    }
    exchanges.add((path: path, body: Map.from(body! as Map)));
    return {
      'token': 'carelink-session',
      'user': {'id': 'patient-ui', 'role': 'patient'},
    };
  }
}

class FakeNativeAuth implements NativeAuth {
  bool googleConfigured = true, facebookConfigured = true, cancelled = false;
  int googleCalls = 0, facebookCalls = 0;
  @override
  Future<NativeAuthConfiguration> configuration() async =>
      NativeAuthConfiguration(
        googleServerClientId: googleConfigured
            ? 'public-web-client.apps.googleusercontent.com'
            : '',
        facebookConfigured: facebookConfigured,
      );
  @override
  Future<String> googleToken(String serverClientId) async {
    googleCalls++;
    expect(serverClientId, 'public-web-client.apps.googleusercontent.com');
    if (cancelled) throw ApiFailure('Google sign-in was cancelled.');
    return 'google-sdk-id-token';
  }

  @override
  Future<String> facebookToken() async {
    facebookCalls++;
    if (cancelled) throw ApiFailure('Facebook sign-in was cancelled.');
    return 'facebook-sdk-access-token';
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  for (final provider in ['google', 'facebook']) {
    test(
      '$provider SDK credential is exchanged for a CareLink session',
      () async {
        final api = SocialApi();
        final native = FakeNativeAuth();
        final service = SocialSignIn(api, native: native);
        final result = await service.signIn(provider);
        expect(result['token'], 'carelink-session');
        final exchange = api.exchanges.single;
        expect(exchange.path, '/auth/social/$provider/native');
        expect(
          exchange.body,
          provider == 'google'
              ? {'id_token': 'google-sdk-id-token'}
              : {'access_token': 'facebook-sdk-access-token'},
        );
        expect(native.googleCalls, provider == 'google' ? 1 : 0);
        expect(native.facebookCalls, provider == 'facebook' ? 1 : 0);
      },
    );

    test('$provider cancellation never reaches the backend exchange', () async {
      final api = SocialApi();
      final native = FakeNativeAuth()..cancelled = true;
      final service = SocialSignIn(api, native: native);
      await expectLater(service.signIn(provider), throwsA(isA<ApiFailure>()));
      expect(api.exchanges, isEmpty);
    });
  }

  test('an older backend does not trigger a browser fallback', () async {
    final api = SocialApi()..nativeSupported = false;
    final native = FakeNativeAuth();
    final service = SocialSignIn(api, native: native);
    expect(await service.providers(), {'google': false, 'facebook': false});
    await expectLater(service.signIn('google'), throwsA(isA<ApiFailure>()));
    expect(api.exchanges, isEmpty);
    expect(native.googleCalls, 0);
  });

  test(
    'missing local Android configuration keeps provider buttons disabled',
    () async {
      final api = SocialApi();
      final native = FakeNativeAuth()
        ..googleConfigured = false
        ..facebookConfigured = false;
      final service = SocialSignIn(api, native: native);
      expect(await service.providers(), {'google': false, 'facebook': false});
      await expectLater(service.signIn('facebook'), throwsA(isA<ApiFailure>()));
      expect(api.exchanges, isEmpty);
      expect(native.facebookCalls, 0);
    },
  );

  test('unconfigured backend cannot be bypassed by a configured SDK', () async {
    final api = SocialApi()..configured = false;
    final service = SocialSignIn(api, native: FakeNativeAuth());
    await expectLater(service.signIn('google'), throwsA(isA<ApiFailure>()));
    expect(api.exchanges, isEmpty);
  });

  test('unsupported providers do not invoke an SDK or API exchange', () async {
    final api = SocialApi();
    final service = SocialSignIn(api, native: FakeNativeAuth());
    await expectLater(service.signIn('unknown'), throwsA(isA<ApiFailure>()));
    expect(api.exchanges, isEmpty);
  });

  test('Android bridge returns public Google configuration and a Facebook readiness flag', () async {
    const channel = MethodChannel('carelink/native_auth_config');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          expect(call.method, 'configuration');
          return {
            'googleServerClientId':
                'public-web-client.apps.googleusercontent.com',
            'facebookConfigured': true,
          };
        });
    final config = await ProviderNativeAuth().configuration();
    expect(config.googleConfigured, isTrue);
    expect(config.facebookConfigured, isTrue);
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });
}
