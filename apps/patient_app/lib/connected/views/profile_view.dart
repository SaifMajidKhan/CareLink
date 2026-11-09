import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../utils/care_format.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';

class ProfileView extends StatelessWidget {
  const ProfileView({
    super.key,
    required this.user,
    required this.onEdit,
    required this.onIdentity,
    required this.onCare,
    required this.onReadings,
    required this.onManage,
    required this.onSettings,
  });

  final Map<String, dynamic> user;
  final VoidCallback onEdit,
      onIdentity,
      onCare,
      onReadings,
      onManage,
      onSettings;

  @override
  Widget build(BuildContext context) {
    final name = '${user['name'] ?? 'CareLink member'}';
    return ListView(
      key: const PageStorageKey('patient-profile'),
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
      children: [
        Semantics(
          header: true,
          child: Text(
            'Your profile',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ),
        const SizedBox(height: 8),
        CareCard(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 23,
                    backgroundColor: AppTheme.tealSoft,
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Padding(
                        padding: const EdgeInsets.all(5),
                        child: Text(
                          CareFormat.initials(name),
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(color: AppTheme.tealDark),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          name,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if ((user['condition'] as String?)?.isNotEmpty == true)
                          Text(
                            CareFormat.condition(user['condition']),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              TextButton.icon(
                onPressed: onEdit,
                icon: const Icon(Icons.edit_outlined, size: 19),
                label: const Text('Edit profile'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        CareCard(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              CareActionRow(
                compact: true,
                icon: Icons.qr_code_2_rounded,
                title: 'Your care ID',
                onTap: onIdentity,
              ),
              const Divider(),
              CareActionRow(
                compact: true,
                icon: Icons.people_outline_rounded,
                title: 'My care team',
                onTap: onCare,
              ),
              const Divider(),
              CareActionRow(
                compact: true,
                icon: Icons.monitor_heart_outlined,
                title: 'Health readings',
                onTap: onReadings,
              ),
              const Divider(),
              CareActionRow(
                compact: true,
                icon: Icons.medication_outlined,
                title: 'My medicines',
                onTap: onManage,
              ),
              const Divider(),
              CareActionRow(
                compact: true,
                icon: Icons.settings_outlined,
                title: 'Settings',
                onTap: onSettings,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
