import 'package:flutter/material.dart';

import '../data/api_client.dart';

class CareScreen extends StatefulWidget {
  const CareScreen({super.key, required this.api});
  final ApiClient api;
  @override
  State<CareScreen> createState() => _CareScreenState();
}

class _CareScreenState extends State<CareScreen> {
  List<dynamic> _rows = [];
  String? _error;
  bool _busy = true;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await widget.api.call('GET', '/connections');
      if (mounted) {
        setState(() {
          _rows = rows;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _act(dynamic row, String action) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(
          '${action == 'accept'
              ? 'Connect with'
              : action == 'decline'
              ? 'Decline'
              : 'Remove'} ${row['caregiver_name']}?',
        ),
        content: Text(
          action == 'accept'
              ? 'They can view your name, condition, schedules, dose reports, summaries and health readings. They can add notes for this connection. They cannot change your medicines or reports. You can remove access at any time.'
              : 'After server confirmation this person will have no access through this connection. Previously viewed information cannot be recalled.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Confirm'),
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
      await _load();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
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
      await showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Care notes'),
          content: SizedBox(
            width: 400,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (notes.isEmpty) const Text('No notes yet.'),
                  for (final n in notes)
                    ListTile(
                      title: Text(n['text']),
                      subtitle: Text('${n['author']} • ${n['received_at']}'),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('My care'),
      actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
    ),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Text(
          'Share your Patient ID or QR from Profile. Requests need your approval. Connection changes require internet.',
        ),
        if (_busy) const LinearProgressIndicator(),
        if (_error != null) Text(_error!),
        if (!_busy && _rows.isEmpty)
          const Padding(
            padding: EdgeInsets.all(24),
            child: Text('No caregiver requests yet.'),
          ),
        for (final r in _rows)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r['caregiver_name'],
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  Text('Caregiver • ${r['state']}'),
                  if (r['state'] == 'pending')
                    Wrap(
                      spacing: 8,
                      children: [
                        FilledButton(
                          onPressed: _busy ? null : () => _act(r, 'accept'),
                          child: const Text('Review & accept'),
                        ),
                        TextButton(
                          onPressed: _busy ? null : () => _act(r, 'decline'),
                          child: const Text('Decline'),
                        ),
                      ],
                    ),
                  if (r['state'] == 'active')
                    Wrap(
                      spacing: 8,
                      children: [
                        OutlinedButton(
                          onPressed: () => _notes(r),
                          child: const Text('Care notes'),
                        ),
                        TextButton(
                          onPressed: _busy ? null : () => _act(r, 'remove'),
                          child: const Text('Remove access'),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
      ],
    ),
  );
}
