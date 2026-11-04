import 'package:carelink_patient/connected/auth/auth_validation.dart';
import 'package:carelink_patient/connected/data/api_client.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('registration limits agree with the backend', () {
    expect(AuthValidation.password('123456789'), isNotNull);
    expect(AuthValidation.password('1234567890'), isNull);
    expect(AuthValidation.password('x' * 129), isNotNull);
    expect(AuthValidation.name('   '), isNotNull);
    expect(AuthValidation.name('Amina Khan'), isNull);
    expect(AuthValidation.email(' member@example.test '), isNull);
    for (final value in [
      'bad@name@host.com',
      'bad address@example.com',
      'invalid',
    ]) {
      expect(AuthValidation.email(value), isNotNull);
    }
  });
  test(
    'structured 422 errors name the field without exposing submitted inputs',
    () {
      final failure = ApiFailure.response(422, {
        'detail': [
          {
            'loc': ['body', 'password'],
            'type': 'string_too_short',
            'msg': 'String should have at least 10 characters',
            'ctx': {'min_length': 10},
            'input': 'private-submitted-value',
          },
        ],
      });
      expect(failure.status, 422);
      expect(failure.fieldErrors['password'], 'Use at least 10 characters.');
      expect(failure.message, contains('Password:'));
      expect(failure.message, isNot(contains('private-submitted-value')));
      expect(failure.message, isNot(contains('(422)')));
    },
  );
  test('HTML gateway errors keep their HTTP status and a useful message', () {
    final failure = ApiFailure.response(503, null);
    expect(failure.status, 503);
    expect(failure.message, contains('temporarily unavailable'));
  });
}
