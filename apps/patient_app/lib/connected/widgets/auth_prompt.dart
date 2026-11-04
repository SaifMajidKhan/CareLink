import 'package:flutter/material.dart';

Future<void> showAuthPrompt(
  BuildContext context, {
  required String feature,
  required Future<void> Function(bool register) onAuthenticate,
}) async {
  final register = await showDialog<bool>(
    context: context,
    builder: (dialog) => AlertDialog(
      icon: const Icon(Icons.lock_outline_rounded),
      title: const Text('Your care starts here'),
      content: SizedBox(
        width: 340,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Sign in or create an account to $feature.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => Navigator.pop(dialog, true),
                child: const Text('Create account'),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: () => Navigator.pop(dialog, false),
                child: const Text('Sign in'),
              ),
              const SizedBox(height: 6),
              TextButton(
                onPressed: () => Navigator.pop(dialog),
                child: const Text('Maybe later'),
              ),
            ],
          ),
        ),
      ),
    ),
  );
  if (register != null) await onAuthenticate(register);
}
