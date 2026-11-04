import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../auth/auth_validation.dart';
import '../auth/social_sign_in.dart';
import '../config/app_config.dart';
import '../data/api_client.dart';
import '../widgets/carelink_brand.dart';
import '../widgets/social_sign_in_buttons.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({
    super.key,
    required this.onSignedIn,
    this.initialServer,
    this.initialRegister = false,
    this.allowRegistration = true,
    this.api,
    this.social,
  });
  final Future<void> Function(String, Map<String, dynamic>) onSignedIn;
  final String? initialServer;
  final bool initialRegister, allowRegistration;
  final ApiClient? api;
  final SocialSignIn? social;
  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController();
  final _confirmation = TextEditingController();
  late final ApiClient _api;
  late final SocialSignIn _social;
  late bool _register;
  bool _busy = false, _showPassword = false, _loadingProviders = true;
  Map<String, bool> _providers = {'google': false, 'facebook': false};
  Map<String, String> _fieldErrors = {};
  String? _error;

  @override
  void initState() {
    super.initState();
    _register = widget.allowRegistration && widget.initialRegister;
    _api =
        widget.api ??
        ApiClient(
          (widget.initialServer ?? AppConfig.apiBase).trim().replaceAll(
            RegExp(r'/+$'),
            '',
          ),
        );
    _social = widget.social ?? SocialSignIn(_api);
    _loadProviders();
  }

  Future<void> _loadProviders() async {
    try {
      final available = await _social.providers();
      if (mounted) setState(() => _providers = available);
    } catch (_) {
      // Email sign-in remains available if provider setup is not ready.
    } finally {
      if (mounted) setState(() => _loadingProviders = false);
    }
  }

  @override
  void dispose() {
    for (final controller in [_email, _password, _name, _confirmation]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _accept(dynamic result) async {
    if (result is! Map ||
        result['token'] is! String ||
        result['user'] is! Map) {
      throw ApiFailure('Sign-in could not be completed. Please try again.');
    }
    if (result['user']['role'] != 'patient') {
      throw ApiFailure('Use the caregiver portal for this account.');
    }
    await widget.onSignedIn(_api.baseUrl, Map<String, dynamic>.from(result));
    TextInput.finishAutofillContext();
  }

  Future<void> _submit() async {
    if (_busy || !_form.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
      _fieldErrors = {};
    });
    try {
      final result = await _api.call(
        'POST',
        _register ? '/auth/register' : '/auth/login',
        {
          'email': _email.text.trim().toLowerCase(),
          'password': _password.text,
          if (_register) 'name': _name.text.trim(),
          if (_register) 'role': 'patient',
        },
      );
      await _accept(result);
    } on ApiFailure catch (error) {
      if (mounted) {
        setState(() {
          _fieldErrors = error.fieldErrors;
          _error = error.fieldErrors.isEmpty
              ? error.message
              : 'Please correct the highlighted details.';
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'Sign-in could not be completed. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _socialSubmit(String provider) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _accept(await _social.signIn(provider));
    } on ApiFailure catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'Sign-in could not be completed. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  InputDecoration _decoration(String label, IconData icon, String field) =>
      InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, size: 21),
        filled: true,
        fillColor: Colors.white,
        errorText: _fieldErrors[field],
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
        ),
      );

  void _edited(String field) {
    if (_fieldErrors.containsKey(field)) {
      setState(() => _fieldErrors.remove(field));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      backgroundColor: Colors.transparent,
      foregroundColor: const Color(0xFF0F172A),
      systemOverlayStyle: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
      ),
      elevation: 0,
      title: const Text(''),
    ),
    body: SafeArea(
      top: false,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: AutofillGroup(
            child: Form(
              key: _form,
              autovalidateMode: AutovalidateMode.onUserInteraction,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
                children: [
                  const CareLinkBrand(),
                  const SizedBox(height: 30),
                  Text(
                    _register ? 'Start your care journey' : 'Welcome back',
                    style: const TextStyle(
                      fontSize: 27,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF0F172A),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _register
                        ? 'Create an account to keep your daily care together.'
                        : 'Sign in to continue your daily routine.',
                    style: const TextStyle(
                      fontSize: 16,
                      height: 1.5,
                      color: Color(0xFF475569),
                    ),
                  ),
                  const SizedBox(height: 26),
                  if (_register) ...[
                    TextFormField(
                      key: const ValueKey('auth-name'),
                      controller: _name,
                      readOnly: _busy,
                      autofillHints: const [AutofillHints.name],
                      textCapitalization: TextCapitalization.words,
                      textInputAction: TextInputAction.next,
                      decoration: _decoration(
                        'Full name',
                        Icons.person_outline,
                        'name',
                      ),
                      validator: AuthValidation.name,
                      onChanged: (_) => _edited('name'),
                    ),
                    const SizedBox(height: 16),
                  ],
                  TextFormField(
                    key: const ValueKey('auth-email'),
                    controller: _email,
                    readOnly: _busy,
                    autofillHints: const [AutofillHints.email],
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    autocorrect: false,
                    decoration: _decoration(
                      'Email address',
                      Icons.mail_outline_rounded,
                      'email',
                    ),
                    validator: AuthValidation.email,
                    onChanged: (_) => _edited('email'),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    key: const ValueKey('auth-password'),
                    controller: _password,
                    readOnly: _busy,
                    autofillHints: [
                      _register
                          ? AutofillHints.newPassword
                          : AutofillHints.password,
                    ],
                    obscureText: !_showPassword,
                    autocorrect: false,
                    enableSuggestions: false,
                    textInputAction: _register
                        ? TextInputAction.next
                        : TextInputAction.done,
                    decoration:
                        _decoration(
                          'Password',
                          Icons.lock_outline_rounded,
                          'password',
                        ).copyWith(
                          helperText: _register
                              ? 'Use at least 10 characters.'
                              : null,
                          suffixIcon: IconButton(
                            tooltip: _showPassword
                                ? 'Hide password'
                                : 'Show password',
                            onPressed: () =>
                                setState(() => _showPassword = !_showPassword),
                            icon: Icon(
                              _showPassword
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                            ),
                          ),
                        ),
                    validator: AuthValidation.password,
                    onChanged: (_) => _edited('password'),
                    onFieldSubmitted: (_) {
                      if (!_register) _submit();
                    },
                  ),
                  if (_register) ...[
                    const SizedBox(height: 16),
                    TextFormField(
                      key: const ValueKey('auth-confirmation'),
                      controller: _confirmation,
                      readOnly: _busy,
                      obscureText: !_showPassword,
                      autocorrect: false,
                      enableSuggestions: false,
                      textInputAction: TextInputAction.done,
                      decoration: _decoration(
                        'Confirm password',
                        Icons.lock_outline_rounded,
                        'confirmation',
                      ),
                      validator: (value) => value == _password.text
                          ? null
                          : 'Passwords do not match.',
                      onFieldSubmitted: (_) => _submit(),
                    ),
                  ],
                  const SizedBox(height: 20),
                  if (_error != null) ...[
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFEF2F2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Color(0xFF991B1B)),
                      ),
                    ),
                    const SizedBox(height: 14),
                  ],
                  FilledButton(
                    onPressed: _busy ? null : _submit,
                    child: _busy
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(_register ? 'Create account' : 'Sign in'),
                  ),
                  const SizedBox(height: 22),
                  const Row(
                    children: [
                      Expanded(child: Divider()),
                      Padding(
                        padding: EdgeInsets.symmetric(horizontal: 14),
                        child: Text(
                          'or continue with',
                          style: TextStyle(color: Color(0xFF64748B)),
                        ),
                      ),
                      Expanded(child: Divider()),
                    ],
                  ),
                  const SizedBox(height: 20),
                  SocialSignInButtons(
                    available: _providers,
                    busy: _busy,
                    loading: _loadingProviders,
                    onSelected: _socialSubmit,
                  ),
                  if (widget.allowRegistration) ...[
                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => setState(() {
                              _register = !_register;
                              _error = null;
                              _fieldErrors = {};
                              _confirmation.clear();
                              _form.currentState?.reset();
                            }),
                      child: Text(
                        _register
                            ? 'Already have an account? Sign in'
                            : 'New to CareLink? Create account',
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
