import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';

class ScheduleForm extends StatefulWidget {
  const ScheduleForm({super.key, required this.api});
  final ApiClient api;
  @override
  State<ScheduleForm> createState() => _ScheduleFormState();
}

class _ScheduleFormState extends State<ScheduleForm> {
  final _name = TextEditingController(),
      _dose = TextEditingController(),
      _zone = TextEditingController(text: 'Asia/Karachi');
  final List<String> _times = [];
  DateTime _start = DateTime.now();
  DateTime? _end;
  bool _busy = false;
  String? _error;
  @override
  void dispose() {
    _name.dispose();
    _dose.dispose();
    _zone.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty ||
        _dose.text.trim().isEmpty ||
        _times.isEmpty) {
      setState(
        () => _error =
            'Enter a name, prescribed instructions and at least one time.',
      );
      return;
    }
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Review schedule'),
        content: Text(
          '${_name.text}\n${_dose.text}\n${_times.join(', ')} (${_zone.text})\nFrom ${dayKey(_start)}${_end == null ? '' : ' until ${dayKey(_end!)}'}\n\nCopy your existing prescription. CareLink does not choose doses.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Back'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Save schedule'),
          ),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.call('POST', '/schedules', {
        'name': _name.text.trim(),
        'instructions': _dose.text.trim(),
        'times': _times,
        'start': dayKey(_start),
        'end': _end == null ? null : dayKey(_end!),
        'timezone': _zone.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Add prescribed schedule')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Text(
          'Daily clock times only. Use the instructions already prescribed to you.',
        ),
        TextField(
          controller: _name,
          decoration: const InputDecoration(labelText: 'Medicine name'),
        ),
        TextField(
          controller: _dose,
          decoration: const InputDecoration(
            labelText: 'Prescribed dose / instructions',
          ),
        ),
        TextField(
          controller: _zone,
          decoration: const InputDecoration(
            labelText: 'Schedule timezone',
            helperText:
                'Fixed timezone; travelling does not change it automatically.',
          ),
        ),
        Wrap(
          spacing: 8,
          children: [
            for (final t in _times)
              InputChip(
                label: Text(t),
                onDeleted: () => setState(() => _times.remove(t)),
              ),
          ],
        ),
        OutlinedButton(
          onPressed: () async {
            final t = await showTimePicker(
              context: context,
              initialTime: const TimeOfDay(hour: 8, minute: 0),
            );
            if (t != null && mounted) {
              final v =
                  '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
              setState(() {
                if (!_times.contains(v)) _times.add(v);
                _times.sort();
              });
            }
          },
          child: const Text('Add daily time'),
        ),
        TextButton(
          onPressed: () async {
            final d = await showDatePicker(
              context: context,
              initialDate: _start,
              firstDate: DateTime.now(),
              lastDate: DateTime.now().add(const Duration(days: 365)),
            );
            if (d != null && mounted) setState(() => _start = d);
          },
          child: Text('Starts ${dayKey(_start)}'),
        ),
        TextButton(
          onPressed: () async {
            final d = await showDatePicker(
              context: context,
              initialDate: _end ?? _start,
              firstDate: _start,
              lastDate: _start.add(const Duration(days: 730)),
            );
            if (d != null && mounted) setState(() => _end = d);
          },
          child: Text(
            _end == null ? 'Add end date (optional)' : 'Ends ${dayKey(_end!)}',
          ),
        ),
        if (_error != null) Text(_error!),
        FilledButton(
          onPressed: _busy ? null : _save,
          child: Text(_busy ? 'Saving…' : 'Review and save'),
        ),
      ],
    ),
  );
}
