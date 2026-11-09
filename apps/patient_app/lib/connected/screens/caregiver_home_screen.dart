import 'package:flutter/material.dart';

import '../data/api_client.dart';
import '../models/patient_code.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';
import 'caregiver_patient_screen.dart';
import 'patient_request_screen.dart';

class CaregiverHomeScreen extends StatefulWidget {
  const CaregiverHomeScreen({
    super.key,
    required this.api,
    required this.user,
    required this.onLogout,
    required this.onRenew,
  });

  final ApiClient api;
  final Map<String, dynamic> user;
  final Future<void> Function() onLogout;
  final Future<void> Function(BuildContext) onRenew;

  @override
  State<CaregiverHomeScreen> createState() => _CaregiverHomeScreenState();
}

class _CaregiverHomeScreenState extends State<CaregiverHomeScreen> {
  List<Map<String, dynamic>> _connections = [];
  bool _loading = false, _signingOut = false;
  ApiFailure? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await widget.api.call('GET', '/connections');
      if (result is! List) {
        throw ApiFailure('Could not load patient connections.');
      }
      if (!mounted) return;
      setState(() {
        _connections = result
            .whereType<Map<String, dynamic>>()
            .where((row) => row['caregiver'] == widget.user['id'])
            .toList();
      });
    } on ApiFailure catch (error) {
      if (mounted) {
        setState(() {
          _connections = [];
          _error = error;
        });
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addPatient() async {
    final sent = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => PatientRequestScreen(api: widget.api)),
    );
    if (sent != true || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Request sent. Waiting for patient approval.'),
      ),
    );
    await _load();
  }

  Future<void> _openPatient(String id, String name) async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) =>
            CaregiverPatientScreen(api: widget.api, patientId: id, name: name),
      ),
    );
    if (mounted) await _load();
  }

  Future<void> _signOut() async {
    if (_signingOut) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text(
          'Your patient connections will be here when you sign in again.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _signingOut = true);
    try {
      try {
        await widget.api.call('POST', '/auth/logout');
      } on ApiFailure {
        // A network failure must not prevent local sign-out.
      }
      await widget.onLogout();
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = ApiFailure('Could not sign out. Please try again.'),
        );
      }
    } finally {
      if (mounted) setState(() => _signingOut = false);
    }
  }

  Widget _patient(Map<String, dynamic> row) {
    final name = (row['patient_name'] as String?) ?? 'Patient';
    final status = row['state'];
    final id = PatientCode.fromInput((row['patient'] as String?) ?? '');
    final canOpen = status == 'active' && id != null && !_signingOut;
    return CareActionRow(
      compact: true,
      icon: status == 'pending' ? Icons.hourglass_empty : Icons.person_outline,
      title: name,
      subtitle: switch (status) {
        'active' => canOpen ? 'Connected · View updates' : 'Connected',
        'pending' => 'Waiting for patient approval',
        'declined' => 'Request declined',
        _ => 'Connection ended',
      },
      onTap: canOpen ? () => _openPatient(id, name) : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final open = _connections
        .where((row) => row['state'] == 'active' || row['state'] == 'pending')
        .toList();
    final past = _connections
        .where((row) => row['state'] != 'active' && row['state'] != 'pending')
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Caregiver'),
        actions: [
          IconButton(
            tooltip: 'Refresh connections',
            onPressed: _loading || _signingOut ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: _signingOut ? null : _signOut,
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
          children: [
            FilledButton.icon(
              onPressed: _signingOut || _error?.status == 401
                  ? null
                  : _addPatient,
              icon: const Icon(Icons.person_add_alt_1_outlined),
              label: const Text('Add a patient'),
            ),
            const SizedBox(height: 8),
            const Text(
              'Scan a patient’s QR code or enter their ID to request access.',
            ),
            const SizedBox(height: 16),
            Text(
              'Your patients',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null) ...[
              Semantics(
                liveRegion: true,
                child: CareNotice(_error!.message, error: true),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: _error!.status == 401
                    ? () async {
                        await widget.onRenew(context);
                        if (mounted) await _load();
                      }
                    : _load,
                child: Text(
                  _error!.status == 401 ? 'Sign in again' : 'Try again',
                ),
              ),
            ] else if (!_loading && open.isEmpty)
              const Text('No active connections or pending requests yet.'),
            for (final row in open)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: CareCard(padding: EdgeInsets.zero, child: _patient(row)),
              ),
            if (past.isNotEmpty)
              ExpansionTile(
                title: const Text('Past requests'),
                children: past.map(_patient).toList(),
              ),
          ],
        ),
      ),
    );
  }
}
