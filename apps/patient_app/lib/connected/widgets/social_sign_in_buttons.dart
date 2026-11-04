import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class SocialSignInButtons extends StatelessWidget {
  const SocialSignInButtons({
    super.key,
    required this.available,
    required this.busy,
    required this.loading,
    required this.onSelected,
  });
  final Map<String, bool> available;
  final bool busy, loading;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      OutlinedButton.icon(
        onPressed: !busy && available['google'] == true
            ? () => onSelected('google')
            : null,
        icon: SvgPicture.asset('assets/auth/google.svg', width: 20, height: 20),
        label: const Text('Continue with Google'),
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          backgroundColor: Colors.white,
        ),
      ),
      const SizedBox(height: 10),
      OutlinedButton.icon(
        onPressed: !busy && available['facebook'] == true
            ? () => onSelected('facebook')
            : null,
        icon: const Icon(Icons.facebook, color: Color(0xFF1877F2), size: 24),
        label: const Text('Continue with Facebook'),
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          backgroundColor: Colors.white,
        ),
      ),
      if (!loading && available.values.every((enabled) => !enabled)) ...[
        const SizedBox(height: 10),
        Text(
          'Google and Facebook sign-in are not available yet. You can continue with email.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall
              ?.copyWith(color: const Color(0xFF64748B)),
        ),
      ],
    ],
  );
}
