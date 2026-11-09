import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/theme/app_theme.dart';
import '../models/patient_code.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';

class CareIdentityScreen extends StatelessWidget {
  const CareIdentityScreen({
    super.key,
    required this.patientId,
    required this.name,
  });
  final String patientId, name;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Your care ID')),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
      children: [
        const Text(
          'Ask your caregiver to scan this code. You approve every request.',
        ),
        const SizedBox(height: 12),
        CareCard(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                name,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              LayoutBuilder(
                builder: (context, constraints) => Center(
                  child: Semantics(
                    label: 'Patient connection QR code for $patientId',
                    image: true,
                    child: ExcludeSemantics(
                      child: QrImageView(
                        data: PatientCode.encode(patientId),
                        size: constraints.maxWidth.clamp(0.0, 224.0),
                        backgroundColor: Colors.white,
                        padding: const EdgeInsets.all(16),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Patient ID',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 6),
              SelectableText(
                patientId,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.ink,
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: patientId));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Patient ID copied')),
                    );
                  }
                },
                icon: const Icon(Icons.copy_outlined, size: 19),
                label: const Text('Copy patient ID'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        const CareNotice(
          'Sharing an ID does not give access to your records. You stay in control and can remove a connection at any time.',
          icon: Icons.shield_outlined,
        ),
      ],
    ),
  );
}
