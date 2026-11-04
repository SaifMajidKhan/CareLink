import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../widgets/auth_prompt.dart';
import '../widgets/carelink_brand.dart';

/// Guests can explore the welcome screen without creating a patient session.
class GuestHomeScreen extends StatelessWidget {
  const GuestHomeScreen({super.key, required this.onAuthenticate});
  final Future<void> Function(bool register) onAuthenticate;

  Future<void> _request(BuildContext context, String feature) =>
      showAuthPrompt(context, feature: feature, onAuthenticate: onAuthenticate);

  Widget _feature(
    BuildContext context,
    IconData icon,
    String title,
    String description,
    String action,
  ) => Card(
    elevation: 0,
    margin: const EdgeInsets.only(bottom: 12),
    color: Colors.white,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(18),
      side: const BorderSide(color: Color(0xFFE2E8F0)),
    ),
    child: ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      leading: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFFCCFBF1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: AppTheme.teal),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(description),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: () => _request(context, action),
    ),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
            children: [
              Row(
                children: [
                  const Expanded(child: CareLinkBrand(compact: true)),
                  TextButton(
                    onPressed: () => onAuthenticate(false),
                    child: const Text('Sign in'),
                  ),
                ],
              ),
              const SizedBox(height: 32),
              const Text(
                'A little support.\nA clearer daily routine.',
                style: TextStyle(
                  fontSize: 31,
                  height: 1.18,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Keep track of your medicines and stay connected with the people who care for you.',
                style: TextStyle(
                  fontSize: 16,
                  height: 1.5,
                  color: Color(0xFF475569),
                ),
              ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: AppTheme.teal,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.wb_sunny_outlined,
                      color: Color(0xFF99F6E4),
                      size: 28,
                    ),
                    const SizedBox(height: 14),
                    const Text(
                      'Your day, at a glance',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Your schedule and daily updates will be here when you sign in.',
                      style: TextStyle(color: Color(0xFFCCFBF1), height: 1.5),
                    ),
                    const SizedBox(height: 18),
                    FilledButton(
                      onPressed: () =>
                          _request(context, 'view your daily schedule'),
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: AppTheme.teal,
                      ),
                      child: const Text('Get started'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'Your care, in one place',
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF0F172A),
                ),
              ),
              const SizedBox(height: 14),
              _feature(
                context,
                Icons.medication_outlined,
                'My medicines',
                'Your schedule and dose reminders',
                'manage your medicines',
              ),
              _feature(
                context,
                Icons.history_rounded,
                'Dose history',
                'See the updates you have recorded',
                'view your dose history',
              ),
              _feature(
                context,
                Icons.monitor_heart_outlined,
                'Health readings',
                'Keep your readings together',
                'save and view health readings',
              ),
              _feature(
                context,
                Icons.people_outline_rounded,
                'My care team',
                'Connect with people you trust',
                'connect with your care team',
              ),
              const SizedBox(height: 8),
              const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.visibility_outlined,
                    size: 17,
                    color: Color(0xFF64748B),
                  ),
                  SizedBox(width: 7),
                  Text(
                    'Browsing as a guest',
                    style: TextStyle(color: Color(0xFF64748B)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: 0,
      onDestinationSelected: (index) => _request(context, switch (index) {
        1 => 'view your dose history',
        2 => 'view your profile',
        _ => 'view your daily schedule',
      }),
      destinations: const [
        NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Today'),
        NavigationDestination(icon: Icon(Icons.history), label: 'History'),
        NavigationDestination(
          icon: Icon(Icons.person_outline),
          label: 'Profile',
        ),
      ],
    ),
  );
}
