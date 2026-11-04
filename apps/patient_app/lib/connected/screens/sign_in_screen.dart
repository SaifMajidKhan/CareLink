import 'package:flutter/material.dart';

import '../data/api_client.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key, required this.onSignedIn, this.initialServer});
  final String? initialServer;
  final Future<void> Function(String, Map<String, dynamic>) onSignedIn;
  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _server = TextEditingController(
    text: const String.fromEnvironment(
      'CARELINK_API',
      defaultValue: 'http://10.0.2.2:8000',
    ),
  );
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController();
  bool _register = false, _busy = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    if (widget.initialServer != null) _server.text = widget.initialServer!;
  }

  @override
  void dispose() {
    for (final c in [_server, _email, _password, _name]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final base = _server.text.trim().replaceAll(RegExp(r'/+$'), '');
      final uri = Uri.tryParse(base);
      if (uri == null ||
          !['http', 'https'].contains(uri.scheme) ||
          uri.host.isEmpty) {
        throw ApiFailure('Enter a valid server address.');
      }
      final result = await ApiClient(base)
          .call('POST', _register ? '/auth/register' : '/auth/login', {
            'email': _email.text.trim(),
            'password': _password.text,
            if (_register) 'name': _name.text.trim(),
            if (_register) 'role': 'patient',
          });
      if (result['user']['role'] != 'patient') {
        throw ApiFailure('Use the caregiver portal for this account.');
      }
      await widget.onSignedIn(base, Map<String, dynamic>.from(result));
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(24),
            children: [
              const Icon(
                Icons.favorite_outline,
                size: 64,
                color: Color(0xFF0F766E),
              ),
              const SizedBox(height: 16),
              Text(
                'CareLink',
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const Text('A little support. A clearer daily routine.'),
              const SizedBox(height: 24),
              const Text('FYP demonstration • Use fictional details only.'),
              if (_register)
                TextField(
                  controller: _name,
                  decoration: const InputDecoration(labelText: 'Your name'),
                ),
              TextField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Password (at least 10 characters)',
                ),
              ),
              const SizedBox(height: 16),
              if (_error != null)
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: Text(
                  _busy
                      ? 'Please wait…'
                      : _register
                      ? 'Create patient account'
                      : 'Sign in',
                ),
              ),
              TextButton(
                onPressed: _busy
                    ? null
                    : () => setState(() => _register = !_register),
                child: Text(
                  _register
                      ? 'Already registered? Sign in'
                      : 'Create an account',
                ),
              ),
              ExpansionTile(
                title: const Text('Server connection'),
                children: [
                  TextField(
                    controller: _server,
                    decoration: const InputDecoration(labelText: 'API address'),
                  ),
                  const Text(
                    'Android emulator: http://10.0.2.2:8000. Public deployments require HTTPS.',
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
