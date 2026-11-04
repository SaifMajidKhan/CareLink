import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter/services.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

import '../config/app_config.dart';
import '../data/api_client.dart';

typedef AuthBrowser = Future<String> Function(String url, String scheme);

class SocialSignIn {
  SocialSignIn(this.api, {AuthBrowser? browser})
    : _browser = browser ?? _openBrowser;
  final ApiClient api;
  final AuthBrowser _browser;

  static Future<String> _openBrowser(String url, String scheme) =>
      FlutterWebAuth2.authenticate(url: url, callbackUrlScheme: scheme);

  static String challenge(String verifier) => base64Url
      .encode(sha256.convert(ascii.encode(verifier)).bytes)
      .replaceAll('=', '');

  Future<Map<String, bool>> providers() async {
    final data = await api.call('GET', '/auth/providers');
    return {
      'google': data['google']?['available'] == true,
      'facebook': data['facebook']?['available'] == true,
    };
  }

  Future<Map<String, dynamic>> signIn(String provider) async {
    if (!['google', 'facebook'].contains(provider)) {
      throw ApiFailure('Choose a supported sign-in option.');
    }
    final random = Random.secure();
    final verifier = base64Url
        .encode(List.generate(48, (_) => random.nextInt(256)))
        .replaceAll('=', '');
    final started = await api.call('POST', '/auth/social/$provider/start', {
      'code_challenge': challenge(verifier),
    });
    final authorization = Uri.parse(started['authorization_url'] as String);
    final expectedHost = provider == 'google'
        ? 'accounts.google.com'
        : 'www.facebook.com';
    if (authorization.scheme != 'https' || authorization.host != expectedHost) {
      throw ApiFailure('The sign-in service returned an invalid address.');
    }
    String returned;
    try {
      returned = await _browser(
        authorization.toString(),
        AppConfig.callbackScheme,
      );
    } on PlatformException catch (error) {
      if (['CANCELED', 'CANCELLED'].contains(error.code.toUpperCase())) {
        throw ApiFailure('Sign-in was cancelled. You can try again.');
      }
      throw ApiFailure('Could not open secure sign-in. Please try again.');
    }
    final callback = Uri.parse(returned);
    if (callback.scheme != AppConfig.callbackScheme ||
        callback.host != AppConfig.callbackHost ||
        callback.path != AppConfig.callbackPath ||
        callback.queryParameters['state'] != started['state']) {
      throw ApiFailure('Sign-in could not be verified. Please start again.');
    }
    final error = callback.queryParameters['error'];
    if (error != null) {
      throw ApiFailure(switch (error) {
        'cancelled' => 'Sign-in was cancelled. You can try again.',
        'email_in_use' => 'An account already uses this email. Sign in with your existing method.',
        'account_unavailable' =>
          'This account is unavailable. Please contact support.',
        _ =>
          'Sign-in could not be completed. Please try again or use your email.',
      });
    }
    final code = callback.queryParameters['code'];
    if (code == null || code.isEmpty) {
      throw ApiFailure('Sign-in was not completed. Please try again.');
    }
    final result = await api.call('POST', '/auth/social/exchange', {
      'state': started['state'],
      'code': code,
      'code_verifier': verifier,
    });
    return Map<String, dynamic>.from(result);
  }
}
