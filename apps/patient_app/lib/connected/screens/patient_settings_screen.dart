import 'package:flutter/material.dart';

import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';

enum PatientSettingsAction { reminders, reconnect, signOut }

class PatientSettingsScreen extends StatelessWidget {
  const PatientSettingsScreen({
    super.key,
    required this.remindersEnabled,
    required this.pending,
    this.updated,
  });

  final bool remindersEnabled;
  final int pending;
  final String? updated;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Settings')),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
      children: [
        CareCard(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              CareActionRow(
                compact: true,
                icon: Icons.notifications_outlined,
                title: remindersEnabled
                    ? 'Refresh reminders'
                    : 'Enable reminders',
                subtitle: 'Reminders are scheduled up to 7 days ahead.',
                onTap: () =>
                    Navigator.pop(context, PatientSettingsAction.reminders),
              ),
              const Divider(),
              CareActionRow(
                compact: true,
                icon: Icons.lock_reset_rounded,
                title: 'Reconnect account',
                subtitle: 'Sign in again to the same account.',
                onTap: () =>
                    Navigator.pop(context, PatientSettingsAction.reconnect),
              ),
              const Divider(),
              CareActionRow(
                compact: true,
                icon: Icons.logout_rounded,
                title: 'Sign out',
                danger: true,
                onTap: () =>
                    Navigator.pop(context, PatientSettingsAction.signOut),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        CareSyncLine(updated: updated, pending: pending),
      ],
    ),
  );
}
