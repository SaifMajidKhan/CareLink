import 'package:flutter/material.dart';

import '../auth/account_role.dart';
import '../widgets/auth_prompt.dart';
import '../widgets/carelink_brand.dart';

class GuestHomeScreen extends StatelessWidget {
  const GuestHomeScreen({super.key, required this.onAuthenticate});

  final Future<void> Function(bool register, AccountRole role) onAuthenticate;

  Future<void> _request(
    BuildContext context,
    String feature, {
    AccountRole role = AccountRole.patient,
  }) {
    final caregiver = role == AccountRole.caregiver;
    return showAuthPrompt(
      context,
      feature: feature,
      title: caregiver ? 'Caregiver access' : 'Your care starts here',
      account: caregiver ? 'a caregiver account' : 'an account',
      onAuthenticate: (register) => onAuthenticate(register, role),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
            children: [
              Row(
                children: [
                  const Expanded(child: CareLinkBrand(compact: true)),
                  TextButton(
                    onPressed: () => onAuthenticate(false, AccountRole.patient),
                    child: const Text('Sign in'),
                  ),
                ],
              ),
              const SizedBox(height: 22),
              Text(
                'Your daily care',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 6),
              const Text(
                'Keep track of medicines and share updates with people you trust.',
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: () => _request(context, 'manage your medicines'),
                icon: const Icon(Icons.medication_outlined),
                label: const Text('Get started'),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () => _request(
                  context,
                  'add a patient',
                  role: AccountRole.caregiver,
                ),
                icon: const Icon(Icons.people_outline_rounded),
                label: const Text('I’m a caregiver'),
              ),
            ],
          ),
        ),
      ),
    ),
    bottomNavigationBar: NavigationBar(
      height: MediaQuery.textScalerOf(context).scale(14) > 19 ? 92 : 68,
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
