import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class DoseOutcomeOption extends StatelessWidget {
  const DoseOutcomeOption({
    super.key,
    required this.taken,
    required this.selected,
    required this.onTap,
  });
  final bool taken, selected;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) {
    final color = taken ? AppTheme.teal : const Color(0xFF9A3412);
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected
            ? (taken ? AppTheme.tealSoft : const Color(0xFFFFF7ED))
            : Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(
            color: selected ? color : AppTheme.border,
            width: selected ? 1.5 : 1,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              children: [
                Icon(
                  taken
                      ? Icons.check_circle_outline_rounded
                      : Icons.remove_circle_outline_rounded,
                  color: color,
                  size: 29,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        taken ? 'Taken' : 'Skipped',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 3),
                      Text(
                        taken ? 'I took this dose' : 'I skipped this dose',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  selected
                      ? Icons.radio_button_checked
                      : Icons.radio_button_off,
                  color: selected ? color : AppTheme.muted,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
