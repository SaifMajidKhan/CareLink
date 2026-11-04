import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../utils/care_format.dart';
import 'care_card.dart';
import 'care_notice.dart';
import 'dose_status_tag.dart';

class ConnectedDoseCard extends StatelessWidget {
  const ConnectedDoseCard({
    super.key,
    required this.dose,
    required this.onRecord,
    required this.onConflict,
    this.onSnooze,
  });
  final Map<String, dynamic> dose;
  final VoidCallback onRecord, onConflict;
  final VoidCallback? onSnooze;

  @override
  Widget build(BuildContext context) {
    final pending = dose['pending'] == true;
    final report = dose['report'] as Map?;
    final scheduled = DateTime.tryParse('${dose['scheduled_at']}');
    final canReport =
        !pending && scheduled != null && !scheduled.isAfter(DateTime.now());
    return CareCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.tealSoft,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(
                  Icons.medication_outlined,
                  color: AppTheme.teal,
                  size: 26,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${dose['name']}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${dose['instructions']}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 8,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const Icon(
                Icons.schedule_rounded,
                size: 18,
                color: AppTheme.muted,
              ),
              Text(
                CareFormat.clock('${dose['time']}'),
                style: const TextStyle(
                  fontSize: 16,
                  color: AppTheme.ink,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '· ${CareFormat.zone('${dose['timezone']}')}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerLeft,
            child: DoseStatusTag('${report?['outcome'] ?? dose['status']}'),
          ),
          if (report != null) ...[
            const SizedBox(height: 14),
            if (report['taken_at'] != null)
              Text(
                'Taken: ${CareFormat.stamp(report['taken_at'])}${report['approximate'] == true ? ' (approximate)' : ''}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            Text(
              'Recorded: ${CareFormat.stamp(report['recorded_at'])}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          if (pending) ...[
            const SizedBox(height: 14),
            const CareNotice(
              'Saved on this phone—waiting to upload',
              warning: true,
              icon: Icons.cloud_upload_outlined,
            ),
          ],
          if (dose['upload_error'] != null)
            TextButton.icon(
              onPressed: onConflict,
              icon: const Icon(Icons.info_outline_rounded),
              label: const Text('Review upload problem'),
            ),
          if (canReport) ...[
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onRecord,
              icon: Icon(
                report == null ? Icons.edit_note_rounded : Icons.edit_outlined,
              ),
              label: Text(report == null ? 'Record dose' : 'Correct report'),
            ),
          ],
          if (report == null && onSnooze != null) ...[
            const SizedBox(height: 6),
            TextButton.icon(
              onPressed: onSnooze,
              icon: const Icon(Icons.snooze_rounded, size: 20),
              label: const Text('Remind me in 10 minutes'),
            ),
          ],
        ],
      ),
    );
  }
}
