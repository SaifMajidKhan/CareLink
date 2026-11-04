import '../data/api_client.dart';
import 'native_auth.dart';

/// Coordinates provider SDK credentials and the existing CareLink session API.
/// There is no browser redirect or embedded provider-password form here.
class SocialSignIn {
  SocialSignIn(this.api, {NativeAuth? native})
    : _native = native ?? ProviderNativeAuth();

  final ApiClient api;
  final NativeAuth _native;
  NativeAuthConfiguration? _configuration;
  Map<String, bool> _available = {'google': false, 'facebook': false};

  Future<Map<String, bool>> providers() async {
    final data = await api.call('GET', '/auth/providers');
    final google = data['google']?['native_available'] == true;
    final facebook = data['facebook']?['native_available'] == true;
    if (!google && !facebook) {
      _available = {'google': false, 'facebook': false};
      return Map.from(_available);
    }
    _configuration = await _native.configuration();
    _available = {
      'google': google && _configuration!.googleConfigured,
      'facebook': facebook && _configuration!.facebookConfigured,
    };
    return Map.from(_available);
  }

  Future<Map<String, dynamic>> signIn(String provider) async {
    if (!['google', 'facebook'].contains(provider)) {
      throw ApiFailure('Choose a supported sign-in option.');
    }
    if (_configuration == null) await providers();
    if (_available[provider] != true) {
      throw ApiFailure(
        'This sign-in option is not available yet. Please use email.',
      );
    }
    final token = provider == 'google'
        ? await _native.googleToken(_configuration!.googleServerClientId)
        : await _native.facebookToken();
    if (token.isEmpty) {
      throw ApiFailure('Sign-in was not completed. Please try again.');
    }
    final result = await api.call('POST', '/auth/social/$provider/native', {
      provider == 'google' ? 'id_token' : 'access_token': token,
    });
    if (result is! Map ||
        result['token'] is! String ||
        result['user'] is! Map) {
      throw ApiFailure('Sign-in could not be completed. Please try again.');
    }
    return Map<String, dynamic>.from(result);
  }
}
