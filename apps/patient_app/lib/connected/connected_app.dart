import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/theme/app_theme.dart';
import 'data/api_client.dart';
import 'data/account_store.dart';
import 'screens/sign_in_screen.dart';
import 'screens/dashboard.dart';
import 'screens/guest_home_screen.dart';

class ConnectedCareLinkApp extends StatefulWidget {
  const ConnectedCareLinkApp({super.key});
  @override
  State<ConnectedCareLinkApp> createState() => _ConnectedCareLinkAppState();
}

class _ConnectedCareLinkAppState extends State<ConnectedCareLinkApp> {
  static const _secure = FlutterSecureStorage();
  Map<String, dynamic>? _session;
  AccountStore? _store;
  bool _loading = true;
  String? _error;
  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    try {
      final raw = await _secure.read(key: 'carelink_session');
      if (raw != null) _setSession(Map<String, dynamic>.from(jsonDecode(raw)));
    } catch (_) {
      _error = 'Secure sign-in storage could not be read. Restart the app and try again.';
    }
    if (mounted) setState(() => _loading = false);
  }

  void _setSession(Map<String, dynamic> data) {
    _session = data;
    _store = AccountStore(
      ApiClient(data['server'], token: data['token']),
      data['user']['id'],
    );
  }

  Future<void> _signedIn(String server, Map<String, dynamic> data) async {
    data['server'] = server;
    await _secure.write(key: 'carelink_session', value: jsonEncode(data));
    if (mounted) setState(() => _setSession(data));
  }

  Future<void> _profileChanged(Map<String, dynamic> user) async {
    if (_session == null || user['id'] != _store?.userId) return;
    final updated = {..._session!, 'user': user};
    await _secure.write(key: 'carelink_session', value: jsonEncode(updated));
    if (mounted) setState(() => _session = updated);
  }

  Future<void> _authenticate(BuildContext pageContext, bool register) async {
    await Navigator.of(pageContext).push(
      MaterialPageRoute<void>(
        builder: (loginContext) => SignInScreen(
          initialRegister: register,
          onSignedIn: (server, data) async {
            await _signedIn(server, data);
            if (loginContext.mounted) Navigator.of(loginContext).pop();
          },
        ),
      ),
    );
  }

  Future<void> _logout() async {
    await _secure.delete(key: 'carelink_session');
    await _store?.close();
    if (mounted) {
      setState(() {
        _session = null;
        _store = null;
      });
    }
  }

  Future<void> _renew(BuildContext pageContext) async {
    await Navigator.of(pageContext).push(
      MaterialPageRoute<void>(
        builder: (loginContext) => SignInScreen(
          initialServer: _session!['server'],
          allowRegistration: false,
          onSignedIn: (server, data) async {
            if (server != _session!['server'] ||
                data['user']['id'] != _store!.userId) {
              throw ApiFailure(
                'Sign in to the same patient account and server to keep pending reports safe.',
              );
            }
            data['server'] = server;
            await _secure.write(
              key: 'carelink_session',
              value: jsonEncode(data),
            );
            _store!.api.token = data['token'];
            if (mounted) setState(() => _session = data);
            if (loginContext.mounted) Navigator.of(loginContext).pop();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'CareLink',
    debugShowCheckedModeBanner: false,
    theme: AppTheme.light,
    home: _loading
        ? const Scaffold(body: Center(child: CircularProgressIndicator()))
        : _error != null
        ? Scaffold(body: Center(child: Text(_error!)))
        : _session == null
        ? Builder(
            builder: (pageContext) => GuestHomeScreen(
              onAuthenticate: (register) =>
                  _authenticate(pageContext, register),
            ),
          )
        : Dashboard(
            key: ValueKey(_store!.scope),
            store: _store!,
            user: Map<String, dynamic>.from(_session!['user']),
            onLogout: _logout,
            onRenew: _renew,
            onProfileChanged: _profileChanged,
          ),
  );
}
