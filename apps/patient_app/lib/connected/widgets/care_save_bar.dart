import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class CareSaveBar extends StatelessWidget {
  const CareSaveBar({
    super.key,
    required this.label,
    required this.onSave,
    this.busy = false,
    this.icon = Icons.check_rounded,
  });
  final String label;
  final VoidCallback? onSave;
  final bool busy;
  final IconData icon;
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(top: BorderSide(color: AppTheme.border)),
    ),
    child: SafeArea(
      top: false,
      minimum: const EdgeInsets.fromLTRB(20, 14, 20, 16),
      child: FilledButton.icon(
        onPressed: busy ? null : onSave,
        icon: busy
            ? const SizedBox(
                width: 19,
                height: 19,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Icon(icon, size: 21),
        label: Text(busy ? 'Saving…' : label),
      ),
    ),
  );
}
