import 'package:flutter/material.dart';

class DoseStatusTag extends StatelessWidget {
  const DoseStatusTag(this.status, {super.key});
  final String status;
  @override
  Widget build(BuildContext context) {
    final (label, icon, foreground, background) = switch (status) {
      'taken' => (
        'Reported taken',
        Icons.check_circle_outline_rounded,
        const Color(0xFF166534),
        const Color(0xFFDCFCE7),
      ),
      'skipped' => (
        'Reported skipped',
        Icons.remove_circle_outline_rounded,
        const Color(0xFF9A3412),
        const Color(0xFFFFEDD5),
      ),
      'upcoming' => (
        'Upcoming',
        Icons.schedule_rounded,
        const Color(0xFF475569),
        const Color(0xFFF1F5F9),
      ),
      _ => (
        'Not confirmed',
        Icons.help_outline_rounded,
        const Color(0xFF92400E),
        const Color(0xFFFEF3C7),
      ),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 17, color: foreground),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: foreground,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
