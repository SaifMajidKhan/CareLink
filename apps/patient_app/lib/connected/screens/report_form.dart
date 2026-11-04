import 'package:flutter/material.dart';

import '../data/account_store.dart';

class ReportForm extends StatefulWidget {
  const ReportForm({
    super.key,
    required this.dose,
    required this.store,
    required this.afterSave,
    this.initialOutcome,
  });
  final Map<String, dynamic> dose;
  final AccountStore store;
  final Future<void> Function() afterSave;
  final String? initialOutcome;
  @override
  State<ReportForm> createState() => _ReportFormState();
}

class _ReportFormState extends State<ReportForm> {
  String? _outcome;
  DateTime _taken = DateTime.now();
  bool _approx = false, _busy = false;
  String? _error;
  final _reason = TextEditingController();
  @override
  void initState() {
    super.initState();
    _outcome = widget.initialOutcome;
  }

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _pick() async {
    final day = await showDatePicker(
      context: context,
      firstDate: DateTime.parse(widget.dose['day'])
          .subtract(const Duration(days: 1)),
      lastDate: DateTime.now(),
      initialDate: _taken,
    );
    if (day == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_taken),
    );
    if (time != null && mounted) {
      setState(
        () => _taken = DateTime(
          day.year,
          day.month,
          day.day,
          time.hour,
          time.minute,
        ),
      );
    }
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (_outcome == 'taken' && _taken.isAfter(DateTime.now())) {
        throw Exception('Choose a past time.');
      }
      final version = widget.dose['report']?['version'] ?? 0;
      if (version > 0 && _reason.text.trim().isEmpty) {
        throw Exception('Please explain the correction.');
      }
      await widget.store.queue(widget.dose['key'], {
        'request_id': requestId(),
        'schedule_id': widget.dose['schedule_id'],
        'day': widget.dose['day'],
        'time': widget.dose['time'],
        'outcome': _outcome,
        'taken_at': _outcome == 'taken'
            ? _taken.toUtc().toIso8601String()
            : null,
        'recorded_at': DateTime.now().toUtc().toIso8601String(),
        'approximate': _outcome == 'taken' && _approx,
        'expected_version': version,
        'reason': _reason.text.trim(),
      });
      await widget.afterSave();
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_busy,
    child: Scaffold(
      appBar: AppBar(title: const Text('Record what happened')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            widget.dose['name'],
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          Text(
            '${widget.dose['instructions']} • ${widget.dose['day']} ${widget.dose['time']}',
          ),
          const SizedBox(height: 24),
          Wrap(
            spacing: 12,
            children: [
              for (final value in ['taken', 'skipped'])
                ChoiceChip(
                  label: Text(value == 'taken' ? 'Taken' : 'Skipped'),
                  selected: _outcome == value,
                  onSelected: _busy
                      ? null
                      : (_) => setState(() => _outcome = value),
                ),
            ],
          ),
          if (_outcome == 'taken') ...[
            TextButton.icon(
              onPressed: _busy ? null : _pick,
              icon: const Icon(Icons.access_time),
              label: Text('Taken: ${_taken.toString().substring(0, 16)}'),
            ),
            CheckboxListTile(
              value: _approx,
              onChanged: _busy ? null : (v) => setState(() => _approx = v!),
              title: const Text('This time is approximate'),
            ),
          ],
          if (widget.dose['report'] != null)
            TextField(
              controller: _reason,
              decoration: const InputDecoration(
                labelText: 'Reason for correction (required)',
              ),
            ),
          const SizedBox(height: 24),
          const Text(
            'Reports describe what happened. They do not change your prescribed schedule.',
          ),
          const SizedBox(height: 16),
          if (_error != null) Text(_error!),
          FilledButton(
            onPressed: _busy || _outcome == null ? null : _save,
            child: Text(_busy ? 'Saving…' : 'Save record'),
          ),
          const Text(
            'Saved on this phone first. Your caregiver receives it after upload.',
          ),
        ],
      ),
    ),
  );
}
