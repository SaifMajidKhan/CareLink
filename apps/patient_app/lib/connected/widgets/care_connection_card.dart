import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../utils/care_format.dart';
import 'care_card.dart';

class CareConnectionCard extends StatelessWidget {
  const CareConnectionCard({
    super.key,
    required this.connection,
    required this.busy,
    required this.onApprove,
    required this.onDecline,
    required this.onRemove,
    required this.onNotes,
  });
  final Map connection;
  final bool busy;
  final VoidCallback onApprove, onDecline, onRemove, onNotes;
  @override
  Widget build(BuildContext context) {
    final state = connection['state'];
    final name = '${connection['caregiver_name']}';
    final pending = state == 'pending', active = state == 'active';
    final status = pending
        ? 'Waiting for your approval'
        : active
        ? 'Connected'
        : state == 'declined'
        ? 'Request declined'
        : 'Connection ended';
    return CareCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 25,
                backgroundColor: AppTheme.tealSoft,
                child: Text(
                  CareFormat.initials(name),
                  style: const TextStyle(
                    color: AppTheme.tealDark,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      status,
                      style: TextStyle(
                        fontSize: 14,
                        color: pending ? AppTheme.amber : AppTheme.muted,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (pending) ...[
            const SizedBox(height: 18),
            const Text('Review what this person can see before you connect.'),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: busy ? null : onApprove,
              icon: const Icon(Icons.shield_outlined, size: 20),
              label: const Text('Review request'),
            ),
            TextButton(
              onPressed: busy ? null : onDecline,
              child: const Text('Decline'),
            ),
          ],
          if (active) ...[
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: busy ? null : onNotes,
              icon: const Icon(Icons.notes_rounded, size: 20),
              label: const Text('Care notes'),
            ),
            TextButton.icon(
              onPressed: busy ? null : onRemove,
              style: TextButton.styleFrom(foregroundColor: AppTheme.danger),
              icon: const Icon(Icons.link_off_rounded, size: 20),
              label: const Text('Remove access'),
            ),
          ],
        ],
      ),
    );
  }
}
