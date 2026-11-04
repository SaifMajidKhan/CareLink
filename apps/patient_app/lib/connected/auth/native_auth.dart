import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_facebook_auth/flutter_facebook_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../data/api_client.dart';

class NativeAuthConfiguration {
  const NativeAuthConfiguration({
    this.googleServerClientId = '',
    this.facebookConfigured = false,
  });
  final String googleServerClientId;
  final bool facebookConfigured;
  bool get googleConfigured =>
      googleServerClientId.endsWith('.apps.googleusercontent.com');
}

/// Injectable boundary keeps SDK identity tokens out of screens and storage.
abstract interface class NativeAuth {
  Future<NativeAuthConfiguration> configuration();
  Future<String> googleToken(String serverClientId);
  Future<String> facebookToken();
}

class ProviderNativeAuth implements NativeAuth {
  static const _config = MethodChannel('carelink/native_auth_config');
  static Future<void>? _googleInitialization;
  static String? _googleClientId;

  @override
  Future<NativeAuthConfiguration> configuration() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return const NativeAuthConfiguration();
    }
    try {
      final data = await _config.invokeMapMethod<String, dynamic>(
        'configuration',
      );
      return NativeAuthConfiguration(
        googleServerClientId: data?['googleServerClientId'] as String? ?? '',
        facebookConfigured: data?['facebookConfigured'] == true,
      );
    } on PlatformException {
      return const NativeAuthConfiguration();
    } on MissingPluginException {
      return const NativeAuthConfiguration();
    }
  }

  @override
  Future<String> googleToken(String serverClientId) async {
    if (_googleClientId != null && _googleClientId != serverClientId) {
      throw ApiFailure('Restart CareLink to refresh Google sign-in.');
    }
    _googleClientId = serverClientId;
    try {
      // The official SDK requires initialization exactly once per app engine.
      _googleInitialization ??= GoogleSignIn.instance.initialize(
        serverClientId: serverClientId,
      );
      await _googleInitialization;
      final account = await GoogleSignIn.instance.authenticate();
      final token = account.authentication.idToken;
      if (token == null || token.isEmpty) {
        throw ApiFailure('Google did not complete sign-in. Please try again.');
      }
      return token;
    } on GoogleSignInException catch (error) {
      throw ApiFailure(switch (error.code) {
        GoogleSignInExceptionCode.canceled =>
          'Google sign-in was cancelled. You can try again.',
        GoogleSignInExceptionCode.clientConfigurationError ||
        GoogleSignInExceptionCode.providerConfigurationError => 'Google sign-in setup needs to be completed for this app. You can use email for now.',
        GoogleSignInExceptionCode.interrupted ||
        GoogleSignInExceptionCode.uiUnavailable =>
          'Google sign-in could not open. Please try again.',
        _ => 'Google sign-in could not be completed. Please try again.',
      });
    } on PlatformException {
      throw ApiFailure('Google sign-in could not open. Please try again.');
    }
  }

  @override
  Future<String> facebookToken() async {
    try {
      final result = await FacebookAuth.instance.login(
        permissions: const ['email', 'public_profile'],
        loginBehavior: LoginBehavior.nativeWithFallback,
      );
      if (result.status == LoginStatus.cancelled) {
        throw ApiFailure('Facebook sign-in was cancelled. You can try again.');
      }
      final token = result.accessToken;
      if (result.status != LoginStatus.success ||
          token == null ||
          token.type != AccessTokenType.classic ||
          token.tokenString.isEmpty) {
        throw ApiFailure(
          'Facebook sign-in could not be completed. Please try again.',
        );
      }
      return token.tokenString;
    } on PlatformException {
      throw ApiFailure('Facebook sign-in could not open. Please try again.');
    } on MissingPluginException {
      throw ApiFailure(
        'Facebook sign-in setup needs to be completed for this app. You can use email for now.',
      );
    }
  }
}
