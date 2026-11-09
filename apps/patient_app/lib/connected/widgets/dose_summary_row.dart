import 'package:flutter/material.dart';

import '../utils/care_format.dart';
import 'care_action_row.dart';
import 'dose_status_tag.dart';

class DoseSummaryRow extends StatelessWidget {
  const DoseSummaryRow({super.key, required this.dose, required this.onTap});

  final Map<String, dynamic> dose;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final report = dose['report'] as Map?;
    final status = DoseStatusTag.labelFor(
      '${report?['outcome'] ?? dose['status']}',
    );
    final time = CareFormat.clock('${dose['time']}');
    return CareActionRow(
      compact: true,
      icon: Icons.medication_outlined,
      title: '${dose['name']}',
      subtitle: dose['pending'] == true
          ? '$time · $status · Waiting to upload'
          : '$time · $status',
      onTap: onTap,
    );
  }
}
