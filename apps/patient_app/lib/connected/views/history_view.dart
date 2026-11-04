import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../models/day_summary.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_empty_state.dart';
import '../widgets/care_notice.dart';

class HistoryView extends StatelessWidget {
  const HistoryView({
    super.key,
    required this.date,
    required this.doses,
    required this.onDate,
    required this.onCalendar,
    required this.onToday,
    required this.doseBuilder,
    this.updated,
    this.busy = false,
  });
  final DateTime date;
  final List<Map<String, dynamic>> doses;
  final ValueChanged<DateTime> onDate;
  final VoidCallback onCalendar, onToday;
  final Widget Function(Map<String, dynamic>) doseBuilder;
  final String? updated;
  final bool busy;

  Widget _metric(BuildContext context, String label, int count, Color color) =>
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$count',
              style: Theme.of(context).textTheme.headlineSmall
                  ?.copyWith(color: color),
            ),
            const SizedBox(height: 4),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final now = DateUtils.dateOnly(DateTime.now());
    final earliest = now.subtract(const Duration(days: 30));
    final monday = DateUtils.dateOnly(date)
        .subtract(Duration(days: date.weekday - 1));
    final summary = DaySummary(doses);
    final largeText = MediaQuery.textScalerOf(context).scale(16) > 21;
    return ListView(
      key: const PageStorageKey('patient-history'),
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      children: [
        Text('Your history', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text('The updates you’ve saved, one day at a time.'),
        const SizedBox(height: 24),
        CareCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.calendar_month_outlined,
                    color: AppTheme.teal,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      CareFormat.date(date, year: true),
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Choose a date',
                    onPressed: onCalendar,
                    icon: const Icon(Icons.expand_more_rounded),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (var i = 0; i < 7; i++) ...[
                      Builder(
                        builder: (_) {
                          final day = monday.add(Duration(days: i));
                          final selected = CareFormat.sameDay(day, date);
                          final enabled =
                              !day.isAfter(now) && !day.isBefore(earliest);
                          return Semantics(
                            selected: selected,
                            label: CareFormat.longDate(day),
                            child: SizedBox(
                              width: largeText ? 80 : 54,
                              child: Material(
                                color: selected
                                    ? AppTheme.teal
                                    : AppTheme.background,
                                borderRadius: BorderRadius.circular(16),
                                child: InkWell(
                                  borderRadius: BorderRadius.circular(16),
                                  onTap: enabled ? () => onDate(day) : null,
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 5,
                                      vertical: 12,
                                    ),
                                    child: Column(
                                      children: [
                                        Text(
                                          CareFormat.weekday(day),
                                          style: TextStyle(
                                            fontSize: 13,
                                            color: selected
                                                ? Colors.white
                                                : enabled
                                                ? AppTheme.muted
                                                : const Color(0xFF94A3B8),
                                          ),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          '${day.day}',
                                          style: TextStyle(
                                            fontSize: 19,
                                            fontWeight: FontWeight.w700,
                                            color: selected
                                                ? Colors.white
                                                : enabled
                                                ? AppTheme.ink
                                                : const Color(0xFF94A3B8),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                      if (i != 6) const SizedBox(width: 8),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        CareSyncLine(updated: updated, busy: busy),
        if (doses.isEmpty) ...[
          const SizedBox(height: 24),
          CareEmptyState(
            icon: Icons.history_rounded,
            title: 'A fresh page for this day',
            message:
                'There are no saved doses for ${CareFormat.date(date)}. Your recorded updates will appear here.',
            actionLabel: 'Go to today',
            onAction: onToday,
          ),
        ] else ...[
          const SizedBox(height: 20),
          CareCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _metric(
                  context,
                  'Taken',
                  summary.taken,
                  const Color(0xFF166534),
                ),
                _metric(
                  context,
                  'Skipped',
                  summary.skipped,
                  const Color(0xFF9A3412),
                ),
                _metric(
                  context,
                  'Not confirmed',
                  summary.unconfirmed,
                  AppTheme.amber,
                ),
              ],
            ),
          ),
          const CareSectionHeading('Daily records'),
          for (final dose in doses) ...[
            doseBuilder(dose),
            const SizedBox(height: 14),
          ],
        ],
      ],
    );
  }
}
