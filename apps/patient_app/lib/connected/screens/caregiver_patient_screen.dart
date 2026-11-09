import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';
import '../utils/care_format.dart';
import '../widgets/care_notice.dart';
import '../widgets/connected_dose_card.dart';

/// Approved caregiver view. Shared records are fetched online and not cached.
class CaregiverPatientScreen extends StatefulWidget {
  const CaregiverPatientScreen({
    super.key,
    required this.api,
    required this.patientId,
    required this.name,
  });

  final ApiClient api;
  final String patientId, name;

  @override
  State<CaregiverPatientScreen> createState() => _CaregiverPatientScreenState();
}

class _CaregiverPatientScreenState extends State<CaregiverPatientScreen>
    with WidgetsBindingObserver {
  List<Map<String, dynamic>> _doses = [];
  String? _error;
  bool _loading = false;
  int _loadNumber = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _load();
  }

  Future<void> _load() async {
    final load = ++_loadNumber;
    setState(() {
      _loading = true;
      _error = null;
      _doses = [];
    });
    final day = dayKey(DateTime.now());
    final id = Uri.encodeComponent(widget.patientId);
    try {
      final result = await widget.api.call(
        'GET',
        '/patients/$id/doses?start=$day&end=$day',
      );
      if (result is! List) throw ApiFailure('Could not load shared updates.');
      if (mounted && load == _loadNumber) {
        setState(
          () => _doses = result.whereType<Map<String, dynamic>>().toList(),
        );
      }
    } on ApiFailure catch (error) {
      if (mounted && load == _loadNumber) {
        setState(() {
          _error = error.status == 403
              ? 'This patient has not approved access, or the connection has ended.'
              : error.message;
        });
      }
    } finally {
      if (mounted && load == _loadNumber) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Shared updates'),
      actions: [
        IconButton(
          tooltip: 'Refresh patient updates',
          onPressed: _loading ? null : _load,
          icon: const Icon(Icons.refresh_rounded),
        ),
      ],
    ),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
      children: [
        Text(widget.name, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 4),
        Text('Medicines · ${CareFormat.longDate(DateTime.now())}'),
        const SizedBox(height: 14),
        if (_loading)
          const LinearProgressIndicator()
        else if (_error != null)
          Semantics(liveRegion: true, child: CareNotice(_error!, error: true))
        else if (_doses.isEmpty)
          const Text('No medicines are scheduled for today.')
        else
          for (final dose in _doses)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: ConnectedDoseCard(dose: dose),
            ),
      ],
    ),
  );
}
