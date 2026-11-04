import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_empty_state.dart';
import '../widgets/care_notice.dart';
import 'schedule_form.dart';

class ManageSchedulesScreen extends StatefulWidget {
  const ManageSchedulesScreen({
    super.key,
    required this.api,
    required this.patientId,
  });
  final ApiClient api;
  final String patientId;
  @override
  State<ManageSchedulesScreen> createState() => _ManageSchedulesScreenState();
}

class _ManageSchedulesScreenState extends State<ManageSchedulesScreen> {
  List<dynamic> _rows = [];
  bool _busy = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final data = await widget.api.call(
        'GET',
        '/patients/${widget.patientId}/schedules',
      );
      if (mounted) setState(() => _rows = data as List);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _add() async {
    final saved = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => ScheduleForm(api: widget.api)),
    );
    if (saved == true && mounted) await _load();
  }

  Future<void> _end(dynamic row) async {
    final today = DateUtils.dateOnly(DateTime.now());
    final starts = DateTime.parse(row['start']);
    final first = starts.isAfter(today) ? starts : today;
    final last = row['end'] == null
        ? first.add(const Duration(days: 730))
        : DateTime.parse(row['end']);
    if (last.isBefore(first)) return;
    final date = await showDatePicker(
      context: context,
      initialDate: first,
      firstDate: first,
      lastDate: last,
      helpText: 'Last scheduled day',
    );
    if (date == null || !mounted) return;
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Update the end date?'),
        content: Text(
          '${row['name']} will be scheduled through ${CareFormat.date(date, year: true)}. Your existing dose records stay unchanged.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('Save end date'),
          ),
        ],
      ),
    );
    if (accepted != true || !mounted) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.call('POST', '/schedules/${row['id']}/stop', {
        'end': dayKey(date),
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (mounted && _error == null) await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('My medicines'),
      actions: [
        IconButton(
          tooltip: 'Refresh schedules',
          onPressed: _busy ? null : _load,
          icon: const Icon(Icons.refresh_rounded),
        ),
      ],
    ),
    body: RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 110),
        children: [
          Text(
            'Your routine, organized',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 10),
          const Text(
            'Keep the schedule from your care plan here. Saved dose records stay in your history.',
          ),
          const SizedBox(height: 24),
          if (_busy) const LinearProgressIndicator(),
          if (_error != null) ...[
            CareNotice(_error!, error: true),
            const SizedBox(height: 16),
          ],
          if (!_busy && _rows.isEmpty)
            CareEmptyState(
              icon: Icons.medication_outlined,
              title: 'Your medicines belong here',
              message: 'Add a medicine and the instructions you were given.',
              actionLabel: 'Add a medicine',
              onAction: _add,
            ),
          for (final row in _rows) ...[
            CareCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    row['name'],
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(row['instructions']),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final time in row['times'])
                        Chip(label: Text(CareFormat.clock(time))),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    CareFormat.zone(row['timezone']),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  Text(
                    'From ${CareFormat.date(DateTime.parse(row['start']), year: true)}${row['end'] == null ? ' · Ongoing' : ' to ${CareFormat.date(DateTime.parse(row['end']), year: true)}'}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (row['end'] == null ||
                      !DateTime.parse(row['end'])
                          .isBefore(DateUtils.dateOnly(DateTime.now()))) ...[
                    const SizedBox(height: 16),
                    OutlinedButton(
                      onPressed: _busy ? null : () => _end(row),
                      child: const Text('Set an end date'),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 14),
          ],
        ],
      ),
    ),
    floatingActionButton: _rows.isEmpty
        ? null
        : FloatingActionButton.extended(
            onPressed: _add,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Add medicine'),
          ),
  );
}
