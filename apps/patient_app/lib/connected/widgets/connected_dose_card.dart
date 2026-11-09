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
    this.onRecord,
    this.onConflict,
    this.onSnooze,
  });
  final Map<String, dynamic> dose;
  final VoidCallback? onRecord, onConflict, onSnooze;

  @override
  Widget build(BuildContext context) {
    final pending = dose['pending'] == true;
    final report = dose['report'] as Map?;
    final scheduled = DateTime.tryParse('${dose['scheduled_at']}');
    final canReport =
        !pending && scheduled != null && !scheduled.isAfter(DateTime.now());
    return CareCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: AppTheme.tealSoft,
                  borderRadius: BorderRadius.circular(15),
                ),
                child: const Icon(
                  Icons.medication_outlined,
                  color: AppTheme.teal,
                  size: 22,
                ),
              ),
              const SizedBox(width: 10),
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
          const SizedBox(height: 10),
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
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: DoseStatusTag('${report?['outcome'] ?? dose['status']}'),
          ),
          if (report != null) ...[
            const SizedBox(height: 8),
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
            const SizedBox(height: 8),
            const CareNotice(
              'Saved on this phone—waiting to upload',
              warning: true,
              icon: Icons.cloud_upload_outlined,
            ),
          ],
          if (dose['upload_error'] != null && onConflict != null)
            TextButton.icon(
              onPressed: onConflict,
              icon: const Icon(Icons.info_outline_rounded),
              label: const Text('Review upload problem'),
            ),
          if (canReport && onRecord != null) ...[
            const SizedBox(height: 10),
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
