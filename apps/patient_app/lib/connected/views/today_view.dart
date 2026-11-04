import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../models/day_summary.dart';
import '../utils/care_format.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';
import '../widgets/care_empty_state.dart';
import '../widgets/care_notice.dart';

class TodayView extends StatelessWidget {
  const TodayView({
    super.key,
    required this.name,
    required this.doses,
    required this.doseBuilder,
    required this.onAdd,
    required this.onReadings,
    required this.onCare,
    this.updated,
    this.pending = 0,
    this.busy = false,
    this.unavailable = false,
    this.onRetry,
  });
  final String name;
  final List<Map<String, dynamic>> doses;
  final Widget Function(Map<String, dynamic>) doseBuilder;
  final VoidCallback onAdd, onReadings, onCare;
  final String? updated;
  final int pending;
  final bool busy;
  final bool unavailable;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final summary = DaySummary(doses);
    final loading = busy && updated == null;
    return ListView(
      key: const PageStorageKey('patient-today'),
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      children: [
        Text(
          CareFormat.longDate(DateTime.now()),
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 7),
        Text(
          'Hello, ${name.trim().isEmpty ? 'there' : name.trim().split(' ').first}',
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 8),
        const Text('A little support for your daily routine.'),
        const SizedBox(height: 16),
        CareSyncLine(updated: updated, pending: pending, busy: busy),
        if (doses.isEmpty) ...[
          const SizedBox(height: 28),
          CareEmptyState(
            icon: loading
                ? Icons.sync_rounded
                : unavailable
                ? Icons.cloud_off_rounded
                : Icons.medication_outlined,
            title: loading
                ? 'Bringing your routine together'
                : unavailable
                ? 'Your schedule is not available yet'
                : 'Make room for a simpler routine',
            message: loading
                ? 'Your saved medicines will appear here.'
                : unavailable
                ? 'Refresh when you are connected to see the latest saved schedule.'
                : 'Add your first medicine to keep your schedule and daily updates together.',
            actionLabel: loading
                ? null
                : unavailable
                ? 'Refresh updates'
                : 'Add your first medicine',
            onAction: loading
                ? null
                : unavailable
                ? onRetry
                : onAdd,
          ),
        ] else ...[
          const SizedBox(height: 20),
          CareCard(
            color: AppTheme.tealSoft,
            borderColor: const Color(0xFFCCFBF1),
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const Icon(Icons.fact_check_outlined, color: AppTheme.teal),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    '${summary.reported} of ${summary.total} dose updates saved',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.tealDark,
                    ),
                  ),
                ),
              ],
            ),
          ),
          CareSectionHeading(
            'Today’s medicines',
            action: IconButton(
              tooltip: 'Add medicine',
              onPressed: onAdd,
              icon: const Icon(Icons.add_rounded),
            ),
          ),
          for (final dose in doses) ...[
            doseBuilder(dose),
            const SizedBox(height: 14),
          ],
          const CareNotice(
            'No update stays Not confirmed. It does not mean you skipped your medicine.',
          ),
        ],
        const CareSectionHeading('Keep your care connected'),
        CareCard(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              CareActionRow(
                icon: Icons.people_outline_rounded,
                title: 'My care team',
                subtitle: 'People you choose to share with',
                onTap: onCare,
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 18),
                child: Divider(),
              ),
              CareActionRow(
                icon: Icons.monitor_heart_outlined,
                title: 'Health readings',
                subtitle: 'Save and view your measurements',
                onTap: onReadings,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
