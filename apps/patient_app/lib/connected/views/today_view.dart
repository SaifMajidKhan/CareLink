import 'package:flutter/material.dart';

import '../models/day_summary.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';
import '../widgets/dose_summary_row.dart';

class TodayView extends StatelessWidget {
  const TodayView({
    super.key,
    required this.name,
    required this.doses,
    required this.doseBuilder,
    required this.onDoseDetails,
    required this.onAdd,
    this.updated,
    this.pending = 0,
    this.busy = false,
    this.unavailable = false,
    this.onRetry,
  });

  final String name;
  final List<Map<String, dynamic>> doses;
  final Widget Function(Map<String, dynamic>) doseBuilder;
  final ValueChanged<Map<String, dynamic>> onDoseDetails;
  final VoidCallback onAdd;
  final String? updated;
  final int pending;
  final bool busy, unavailable;
  final VoidCallback? onRetry;

  Map<String, dynamic>? _focusDose(DateTime now) {
    Map<String, dynamic>? pendingDose;
    Map<String, dynamic>? upcoming;
    for (final dose in doses) {
      if (dose['pending'] == true) {
        pendingDose ??= dose;
        continue;
      }
      if (dose['report'] != null) continue;
      final scheduled = DateTime.tryParse('${dose['scheduled_at']}');
      if (scheduled == null) continue;
      if (!scheduled.isAfter(now)) return dose;
      upcoming ??= dose;
    }
    return pendingDose ?? upcoming;
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final summary = DaySummary(doses);
    final loading = busy && updated == null;
    final focus = _focusDose(now);
    final firstName = name.trim().isEmpty
        ? 'there'
        : name.trim().split(' ').first;
    return ListView(
      key: const PageStorageKey('patient-today'),
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
      children: [
        Semantics(
          header: true,
          child: Text(
            'Hello, $firstName',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ),
        Text(
          CareFormat.longDate(now),
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SizedBox(height: 10),
        if (doses.isEmpty) ...[
          CareCard(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  loading
                      ? 'Loading your medicines…'
                      : unavailable
                      ? 'Schedule unavailable'
                      : 'No medicines scheduled today',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                if (!loading) ...[
                  const SizedBox(height: 10),
                  FilledButton(
                    onPressed: unavailable ? onRetry : onAdd,
                    child: Text(
                      unavailable
                          ? 'Refresh updates'
                          : 'Add your first medicine',
                    ),
                  ),
                ],
              ],
            ),
          ),
        ] else ...[
          if (focus != null) ...[
            doseBuilder(focus),
            const SizedBox(height: 10),
          ],
          if (doses.length > 1 || focus == null)
            CareCard(
              padding: EdgeInsets.zero,
              child: ExpansionTile(
                key: const PageStorageKey('today-dose-list'),
                title: Text('All doses (${doses.length})'),
                subtitle: Text('${summary.reported} updates recorded'),
                children: [
                  for (final dose in doses) ...[
                    const Divider(),
                    DoseSummaryRow(
                      dose: dose,
                      onTap: () => onDoseDetails(dose),
                    ),
                  ],
                ],
              ),
            ),
        ],
        const SizedBox(height: 10),
        CareSyncLine(updated: updated, pending: pending, busy: busy),
      ],
    );
  }
}
