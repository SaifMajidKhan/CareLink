import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';

class ReadingsScreen extends StatefulWidget {
  const ReadingsScreen({super.key, required this.store});
  final AccountStore store;
  @override
  State<ReadingsScreen> createState() => _ReadingsScreenState();
}

class _ReadingsScreenState extends State<ReadingsScreen> {
  List<dynamic> _rows = [];
  String? _error, _updated;
  bool _busy = false;
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _busy = true);
    try {
      final data = await widget.store.api.call(
        'GET',
        '/patients/${widget.store.userId}/readings',
      );
      await widget.store.cache('readings', data);
      _error = null;
    } catch (e) {
      _error = e.toString();
    }
    final cache = await widget.store.cached('readings');
    if (mounted) {
      setState(() {
        _rows = cache?['data'] ?? [];
        _updated = cache?['updated'];
        _busy = false;
      });
    }
  }

  Future<void> _add() async {
    final result = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => ReadingForm(api: widget.store.api)),
    );
    if (result == true && mounted) await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Health readings'),
      actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
    ),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: _add,
      label: const Text('Add reading'),
      icon: const Icon(Icons.add),
    ),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 100),
      children: [
        const Text(
          'Record measured values. CareLink does not diagnose or recommend treatment.',
        ),
        if (_updated != null) Text('Last downloaded: $_updated'),
        if (_busy) const LinearProgressIndicator(),
        if (_error != null) Text(_error!),
        for (final r in _rows)
          Card(
            child: ListTile(
              title: Text(
                '${r['value']}${r['secondary'] == null ? '' : ' / ${r['secondary']}'} ${r['unit']}',
              ),
              subtitle: Text('${r['kind']} • ${r['measured_at']}'),
            ),
          ),
        if (!_busy && _rows.isEmpty) const Text('No readings recorded.'),
      ],
    ),
  );
}

class ReadingForm extends StatefulWidget {
  const ReadingForm({super.key, required this.api});
  final ApiClient api;
  @override
  State<ReadingForm> createState() => _ReadingFormState();
}

class _ReadingFormState extends State<ReadingForm> {
  final _value = TextEditingController(), _second = TextEditingController();
  String _kind = 'blood_pressure', _unit = 'mmHg';
  DateTime _at = DateTime.now();
  bool _busy = false;
  String? _error;
  @override
  void dispose() {
    _value.dispose();
    _second.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.call('POST', '/readings', {
        'kind': _kind,
        'value': double.tryParse(_value.text),
        'secondary': _kind == 'blood_pressure'
            ? double.tryParse(_second.text)
            : null,
        'unit': _unit,
        'measured_at': _at.toUtc().toIso8601String(),
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
    appBar: AppBar(title: const Text('Add reading')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        DropdownButtonFormField<String>(
          initialValue: _kind,
          items: const [
            DropdownMenuItem(
              value: 'blood_pressure',
              child: Text('Blood pressure'),
            ),
            DropdownMenuItem(value: 'glucose', child: Text('Glucose')),
          ],
          onChanged: (v) => setState(() {
            _kind = v!;
            _unit = v == 'glucose' ? 'mg/dL' : 'mmHg';
          }),
        ),
        TextField(
          controller: _value,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: _kind == 'blood_pressure'
                ? 'Systolic'
                : 'Measured glucose',
          ),
        ),
        if (_kind == 'blood_pressure')
          TextField(
            controller: _second,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Diastolic'),
          ),
        if (_kind == 'glucose')
          DropdownButton<String>(
            value: _unit,
            items: const [
              DropdownMenuItem(value: 'mg/dL', child: Text('mg/dL')),
              DropdownMenuItem(value: 'mmol/L', child: Text('mmol/L')),
            ],
            onChanged: (v) => setState(() => _unit = v!),
          ),
        TextButton(
          onPressed: () async {
            final d = await showDatePicker(
              context: context,
              firstDate: DateTime.now().subtract(const Duration(days: 365)),
              lastDate: DateTime.now(),
              initialDate: _at,
            );
            if (d == null || !context.mounted) return;
            final t = await showTimePicker(
              context: context,
              initialTime: TimeOfDay.fromDateTime(_at),
            );
            if (t != null && mounted) {
              setState(
                () => _at = DateTime(d.year, d.month, d.day, t.hour, t.minute),
              );
            }
          },
          child: Text('Measured ${_at.toString().substring(0, 16)}'),
        ),
        if (_error != null) Text(_error!),
        FilledButton(
          onPressed: _busy ? null : _save,
          child: Text(_busy ? 'Saving…' : 'Save reading online'),
        ),
      ],
    ),
  );
}
