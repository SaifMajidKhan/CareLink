import 'package:carelink_patient/connected/auth/social_sign_in.dart';
import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:flutter_test/flutter_test.dart';

class SocialApi extends ApiClient {
  SocialApi() : super('https://api.example.test');
  final state = 's' * 43;
  String? startedChallenge;
  int exchanges = 0;
  String? authorizationOverride;
  @override
  Future<dynamic> call(String method, String path, [Object? body]) async {
    final data = body! as Map;
    if (path.endsWith('/start')) {
      startedChallenge = data['code_challenge'];
      return {
        'state': state,
        'authorization_url':
            authorizationOverride ??
            'https://accounts.google.com/o/oauth2/v2/auth?state=$state',
      };
    }
    exchanges++;
    expect(data['state'], state);
    expect(SocialSignIn.challenge(data['code_verifier']), startedChallenge);
    return {
      'token': 'test-session',
      'user': {'role': 'patient'},
    };
  }
}

void main() {
  test('PKCE SHA256 challenge matches the RFC 7636 example', () {
    expect(
      SocialSignIn.challenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'),
      'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM',
    );
  });
  test(
    'browser handoff is exchanged with the original device verifier',
    () async {
      final api = SocialApi();
      final service = SocialSignIn(
        api,
        browser: (url, scheme) async {
          expect(scheme, 'carelink');
          return 'carelink://auth/callback?state=${api.state}&code=${'c' * 43}';
        },
      );
      expect((await service.signIn('google'))['token'], 'test-session');
      expect(api.exchanges, 1);
    },
  );
  for (final callback in [
    'carelink://auth/callback?state=wrong&code=example',
    'carelink://wrong/callback?state=${'s' * 43}&code=example',
    'carelink://auth/callback?state=${'s' * 43}&error=cancelled',
  ]) {
    test(
      'unexpected or cancelled callback never creates a session: $callback',
      () async {
        final api = SocialApi();
        final service = SocialSignIn(api, browser: (_, _) async => callback);
        await expectLater(service.signIn('google'), throwsA(isA<ApiFailure>()));
        expect(api.exchanges, 0);
      },
    );
  }
  test('untrusted provider address never opens the browser', () async {
    final api = SocialApi()
      ..authorizationOverride = 'https://attacker.example/login';
    var opened = false;
    final service = SocialSignIn(
      api,
      browser: (_, _) async {
        opened = true;
        return '';
      },
    );
    await expectLater(service.signIn('google'), throwsA(isA<ApiFailure>()));
    expect(opened, isFalse);
    expect(api.exchanges, 0);
  });
}
