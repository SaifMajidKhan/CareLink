import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../utils/care_format.dart';

class CareNotice extends StatelessWidget {
  const CareNotice(
    this.message, {
    super.key,
    this.error = false,
    this.warning = false,
    this.icon = Icons.info_outline_rounded,
    this.onDismiss,
  });
  final String message;
  final bool error;
  final bool warning;
  final IconData icon;
  final VoidCallback? onDismiss;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
    decoration: BoxDecoration(
      color: error
          ? const Color(0xFFFEF2F2)
          : warning
          ? const Color(0xFFFEF3C7)
          : AppTheme.tealSoft,
      borderRadius: BorderRadius.circular(16),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(
            icon,
            size: 21,
            color: error
                ? AppTheme.danger
                : warning
                ? AppTheme.amber
                : AppTheme.teal,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            message,
            style: TextStyle(
              fontSize: 14,
              height: 1.5,
              color: error
                  ? const Color(0xFF991B1B)
                  : warning
                  ? AppTheme.amber
                  : AppTheme.tealDark,
            ),
          ),
        ),
        if (onDismiss != null)
          IconButton(
            tooltip: 'Dismiss',
            onPressed: onDismiss,
            icon: const Icon(Icons.close_rounded, size: 19),
          ),
      ],
    ),
  );
}

class CareSyncLine extends StatelessWidget {
  const CareSyncLine({
    super.key,
    this.updated,
    this.pending = 0,
    this.busy = false,
  });
  final String? updated;
  final int pending;
  final bool busy;
  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 6,
    runSpacing: 5,
    crossAxisAlignment: WrapCrossAlignment.center,
    children: [
      Icon(
        pending > 0 ? Icons.cloud_upload_outlined : Icons.update_rounded,
        size: 16,
        color: pending > 0 ? AppTheme.amber : AppTheme.muted,
      ),
      Text(
        busy ? 'Updating your records…' : CareFormat.updated(updated),
        style: Theme.of(context).textTheme.bodySmall,
      ),
      if (pending > 0)
        Text(
          ' · $pending waiting to upload',
          style: const TextStyle(
            fontSize: 14,
            color: AppTheme.amber,
            fontWeight: FontWeight.w600,
          ),
        ),
    ],
  );
}
