import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../utils/care_format.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';

class ProfileView extends StatelessWidget {
  const ProfileView({
    super.key,
    required this.user,
    required this.patientId,
    required this.onEdit,
    required this.onIdentity,
    required this.onCare,
    required this.onReadings,
    required this.onAdd,
    required this.onManage,
    required this.onReminders,
    required this.onLogout,
    required this.onRenew,
    this.updated,
    this.pending = 0,
    this.remindersEnabled = false,
  });
  final Map<String, dynamic> user;
  final String patientId;
  final VoidCallback onEdit,
      onIdentity,
      onCare,
      onReadings,
      onAdd,
      onManage,
      onReminders,
      onLogout,
      onRenew;
  final String? updated;
  final int pending;
  final bool remindersEnabled;

  Widget _group(List<Widget> rows) => CareCard(
    padding: EdgeInsets.zero,
    child: Column(
      children: [
        for (var i = 0; i < rows.length; i++) ...[
          if (i > 0)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 18),
              child: Divider(),
            ),
          rows[i],
        ],
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    final name = '${user['name'] ?? 'CareLink member'}';
    return ListView(
      key: const PageStorageKey('patient-profile'),
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      children: [
        Text('Your profile', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        const Text('Your care, your people, your preferences.'),
        const SizedBox(height: 24),
        CareCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 32,
                    backgroundColor: const Color(0xFFCCFBF1),
                    child: Text(
                      CareFormat.initials(name),
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.tealDark,
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          name,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 5),
                        Text(
                          CareFormat.condition(user['condition']),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              OutlinedButton.icon(
                onPressed: onEdit,
                icon: const Icon(Icons.edit_outlined, size: 19),
                label: const Text('Edit profile'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        CareCard(
          color: AppTheme.tealSoft,
          borderColor: const Color(0xFFCCFBF1),
          onTap: onIdentity,
          child: Row(
            children: [
              const Icon(
                Icons.qr_code_2_rounded,
                color: AppTheme.teal,
                size: 34,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Your care ID',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.tealDark,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      patientId,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppTheme.tealDark,
                      ),
                      softWrap: true,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Open your QR code and sharing details',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.chevron_right_rounded, color: AppTheme.teal),
            ],
          ),
        ),
        const CareSectionHeading('Care and records'),
        _group([
          CareActionRow(
            icon: Icons.people_outline_rounded,
            title: 'My care team',
            subtitle: 'Connections and requests',
            onTap: onCare,
          ),
          CareActionRow(
            icon: Icons.monitor_heart_outlined,
            title: 'Health readings',
            subtitle: 'Blood pressure and glucose',
            onTap: onReadings,
          ),
        ]),
        const CareSectionHeading('Your routine'),
        _group([
          CareActionRow(
            icon: Icons.medication_outlined,
            title: 'My medicines',
            subtitle: 'View and manage your schedules',
            onTap: onManage,
          ),
          CareActionRow(
            icon: Icons.add_circle_outline_rounded,
            title: 'Add a medicine',
            subtitle: 'Add the instructions you were given',
            onTap: onAdd,
          ),
          CareActionRow(
            icon: Icons.notifications_outlined,
            title: 'Reminders',
            subtitle: remindersEnabled
                ? 'Refresh your saved reminder schedule'
                : 'Set up notifications for your routine',
            onTap: onReminders,
          ),
        ]),
        const CareSectionHeading('Account'),
        _group([
          CareActionRow(
            icon: Icons.lock_reset_rounded,
            title: 'Reconnect account',
            subtitle: 'Sign in again while keeping pending updates',
            onTap: onRenew,
          ),
          CareActionRow(
            icon: Icons.logout_rounded,
            title: 'Sign out',
            subtitle: 'Leave this account on this phone',
            danger: true,
            onTap: onLogout,
          ),
        ]),
        const SizedBox(height: 24),
        CareSyncLine(updated: updated, pending: pending),
        const SizedBox(height: 14),
        Text(
          'Follow the care plan provided by your healthcare professional.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
