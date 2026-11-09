import 'package:flutter/material.dart';

import '../models/day_summary.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';
import '../widgets/dose_summary_row.dart';

class HistoryView extends StatelessWidget {
  const HistoryView({
    super.key,
    required this.date,
    required this.doses,
    required this.onDate,
    required this.onCalendar,
    required this.onDoseDetails,
    this.updated,
    this.busy = false,
  });

  final DateTime date;
  final List<Map<String, dynamic>> doses;
  final ValueChanged<DateTime> onDate;
  final VoidCallback onCalendar;
  final ValueChanged<Map<String, dynamic>> onDoseDetails;
  final String? updated;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final today = DateUtils.dateOnly(DateTime.now());
    final earliest = DateTime(today.year, today.month, today.day - 30);
    final summary = DaySummary(doses);
    return ListView(
      key: const PageStorageKey('patient-history'),
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
      children: [
        Semantics(
          header: true,
          child: Text(
            'Your history',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            IconButton(
              tooltip: 'Previous day',
              onPressed: date.isAfter(earliest)
                  ? () => onDate(DateTime(date.year, date.month, date.day - 1))
                  : null,
              icon: const Icon(Icons.chevron_left_rounded),
            ),
            Expanded(
              child: OutlinedButton(
                onPressed: onCalendar,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 10,
                  ),
                ),
                child: Text(
                  CareFormat.date(date, year: true),
                  textAlign: TextAlign.center,
                  semanticsLabel:
                      'Choose a date. ${CareFormat.date(date, year: true)}',
                ),
              ),
            ),
            IconButton(
              tooltip: 'Next day',
              onPressed: date.isBefore(today)
                  ? () => onDate(DateTime(date.year, date.month, date.day + 1))
                  : null,
              icon: const Icon(Icons.chevron_right_rounded),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (doses.isEmpty)
          CareCard(
            padding: const EdgeInsets.all(14),
            child: Text(
              busy && updated == null
                  ? 'Loading your history…'
                  : updated == null
                  ? 'No history downloaded yet.'
                  : 'No doses scheduled for this day.',
            ),
          )
        else ...[
          Text(
            '${summary.taken} taken · ${summary.skipped} skipped · ${summary.unconfirmed} not confirmed',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          CareCard(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                for (var i = 0; i < doses.length; i++) ...[
                  if (i > 0) const Divider(),
                  DoseSummaryRow(
                    dose: doses[i],
                    onTap: () => onDoseDetails(doses[i]),
                  ),
                ],
              ],
            ),
          ),
        ],
        const SizedBox(height: 10),
        CareSyncLine(updated: updated, busy: busy),
      ],
    );
  }
}
