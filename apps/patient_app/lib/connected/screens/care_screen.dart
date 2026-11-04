import 'package:flutter/material.dart';

import '../data/api_client.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_connection_card.dart';
import '../widgets/care_empty_state.dart';
import '../widgets/care_notice.dart';
import 'care_identity_screen.dart';

class CareScreen extends StatefulWidget {
  const CareScreen({super.key, required this.api, this.patientId, this.name});
  final ApiClient api;
  final String? patientId, name;
  @override
  State<CareScreen> createState() => _CareScreenState();
}

class _CareScreenState extends State<CareScreen> {
  List<dynamic> _rows = [];
  String? _error;
  bool _busy = false;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _busy = true);
    try {
      final rows = await widget.api.call('GET', '/connections');
      if (mounted) {
        setState(() {
          _rows = rows;
          _error = null;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _identity() async {
    if (widget.patientId == null) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CareIdentityScreen(
          patientId: widget.patientId!,
          name: widget.name ?? 'CareLink patient',
        ),
      ),
    );
  }

  Future<void> _act(dynamic row, String action) async {
    final title = action == 'accept'
        ? 'Connect with ${row['caregiver_name']}?'
        : action == 'decline'
        ? 'Decline this request?'
        : 'Remove this connection?';
    final explanation = action == 'accept'
        ? 'They can view your name, condition, schedules, dose reports, summaries and health readings. They can add notes for this connection. They cannot change your medicines or reports. You can remove access at any time.'
        : action == 'decline'
        ? 'This request will be declined. No access to your records will be granted.'
        : 'After server confirmation this person will have no access through this connection. Previously viewed information cannot be recalled.';
    final yes = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(child: Text(explanation)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: Text(
              action == 'accept'
                  ? 'Approve connection'
                  : action == 'decline'
                  ? 'Decline request'
                  : 'Remove access',
            ),
          ),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await widget.api.call('POST', '/connections/${row['id']}', {
        'action': action,
      });
      if (mounted) await _load();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error.toString();
          _busy = false;
        });
      }
    }
  }

  Future<void> _notes(dynamic row) async {
    try {
      final notes = await widget.api.call(
        'GET',
        '/connections/${row['id']}/notes',
      ) as List;
      if (!mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        showDragHandle: true,
        builder: (sheet) => SizedBox(
          height: MediaQuery.sizeOf(sheet).height * 0.72,
          child: ListView(
            padding: const EdgeInsets.all(22),
            children: [
              Text(
                'Care notes',
                style: Theme.of(sheet).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text('From ${row['caregiver_name']}'),
              const SizedBox(height: 24),
              if (notes.isEmpty)
                const CareEmptyState(
                  icon: Icons.notes_rounded,
                  title: 'A space for a little support',
                  message: 'Notes from this care connection will appear here.',
                ),
              for (final note in notes) ...[
                CareCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        note['text'],
                        style: Theme.of(sheet).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: 14),
                      Text(
                        CareFormat.stamp(note['received_at']),
                        style: Theme.of(sheet).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
              ],
            ],
          ),
        ),
      );
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Widget _connection(dynamic row) => CareConnectionCard(
    connection: row,
    busy: _busy,
    onApprove: () => _act(row, 'accept'),
    onDecline: () => _act(row, 'decline'),
    onRemove: () => _act(row, 'remove'),
    onNotes: () => _notes(row),
  );

  @override
  Widget build(BuildContext context) {
    final requests = _rows.where((row) => row['state'] == 'pending').toList();
    final connected = _rows.where((row) => row['state'] == 'active').toList();
    final previous = _rows
        .where((row) => !['pending', 'active'].contains(row['state']))
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: const Text('My care team'),
        actions: [
          IconButton(
            tooltip: 'Refresh connections',
            onPressed: _busy ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Care feels better together',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            const Text(
              'Choose who can see your updates. Every connection starts with your approval.',
            ),
            const SizedBox(height: 22),
            if (widget.patientId != null &&
                (requests.isNotEmpty || connected.isNotEmpty || _error != null))
              OutlinedButton.icon(
                onPressed: _identity,
                icon: const Icon(Icons.qr_code_2_rounded),
                label: const Text('Show my care ID'),
              ),
            const SizedBox(height: 16),
            if (_busy) const LinearProgressIndicator(),
            if (_error != null) ...[
              CareNotice(_error!, error: true),
              const SizedBox(height: 16),
            ],
            if (!_busy &&
                _error == null &&
                requests.isEmpty &&
                connected.isEmpty) ...[
              const SizedBox(height: 12),
              CareEmptyState(
                icon: Icons.people_outline_rounded,
                title: 'Your circle starts with you',
                message: 'Share your care ID with someone you trust. Their connection request will appear here.',
                actionLabel: widget.patientId == null
                    ? null
                    : 'Open my care ID',
                onAction: widget.patientId == null ? null : _identity,
              ),
            ],
            if (requests.isNotEmpty) ...[
              CareSectionHeading('Requests (${requests.length})'),
              for (final row in requests) ...[
                _connection(row),
                const SizedBox(height: 14),
              ],
            ],
            if (connected.isNotEmpty) ...[
              const CareSectionHeading('Connected with you'),
              for (final row in connected) ...[
                _connection(row),
                const SizedBox(height: 14),
              ],
            ],
            if (previous.isNotEmpty)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Previous connections'),
                children: [
                  for (final row in previous)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _connection(row),
                    ),
                ],
              ),
            const SizedBox(height: 22),
            const CareNotice(
              'Connection changes need internet. Your records are shared only after approval.',
              icon: Icons.shield_outlined,
            ),
          ],
        ),
      ),
    );
  }
}
