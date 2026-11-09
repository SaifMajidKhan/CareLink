import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class CareActionRow extends StatelessWidget {
  const CareActionRow({
    super.key,
    required this.icon,
    required this.title,
    required this.onTap,
    this.subtitle,
    this.danger = false,
    this.compact = false,
    this.trailing,
  });
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  final bool danger, compact;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => InkWell(
    borderRadius: BorderRadius.circular(18),
    onTap: onTap,
    child: Container(
      constraints: const BoxConstraints(minHeight: 52),
      padding: EdgeInsets.symmetric(horizontal: 14, vertical: compact ? 9 : 16),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.all(compact ? 6 : 11),
            decoration: BoxDecoration(
              color: danger ? const Color(0xFFFEF2F2) : AppTheme.tealSoft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              icon,
              size: 22,
              color: danger ? AppTheme.danger : AppTheme.teal,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: danger ? AppTheme.danger : AppTheme.ink,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 4),
                  Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
                ],
              ],
            ),
          ),
          if (trailing != null || onTap != null) ...[
            const SizedBox(width: 8),
            trailing ??
                const Icon(Icons.chevron_right_rounded, color: AppTheme.muted),
          ],
        ],
      ),
    ),
  );
}
