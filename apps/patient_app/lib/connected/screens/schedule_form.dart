import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';
import '../utils/care_format.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';
import '../widgets/care_save_bar.dart';

class ScheduleForm extends StatefulWidget {
  const ScheduleForm({super.key, required this.api});
  final ApiClient api;
  @override
  State<ScheduleForm> createState() => _ScheduleFormState();
}

class _ScheduleFormState extends State<ScheduleForm> {
  final _form = GlobalKey<FormState>();
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

  Future<void> _addTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: const TimeOfDay(hour: 8, minute: 0),
      helpText: 'Choose a daily time',
    );
    if (picked == null || !mounted) return;
    final time =
        '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
    setState(() {
      if (!_times.contains(time)) _times.add(time);
      _times.sort();
      _error = null;
    });
  }

  Future<void> _pickStart() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _start,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      helpText: 'First scheduled day',
    );
    if (picked != null && mounted) {
      setState(() {
        _start = picked;
        if (_end != null && _end!.isBefore(_start)) _end = null;
      });
    }
  }

  Future<void> _pickEnd() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _end ?? _start,
      firstDate: _start,
      lastDate: _start.add(const Duration(days: 730)),
      helpText: 'Last scheduled day',
    );
    if (picked != null && mounted) setState(() => _end = picked);
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate() || _times.isEmpty) {
      setState(
        () =>
            _error = _times.isEmpty ? 'Choose at least one daily time.' : null,
      );
      return;
    }
    final accepted = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('Review your schedule'),
        content: SizedBox(
          width: 340,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _name.text.trim(),
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 10),
                Text(_dose.text.trim()),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final time in _times)
                      Chip(label: Text(CareFormat.clock(time))),
                  ],
                ),
                const SizedBox(height: 12),
                Text(CareFormat.zone(_zone.text.trim())),
                const SizedBox(height: 8),
                Text(
                  'From ${CareFormat.date(_start, year: true)}${_end == null ? ' · Ongoing' : ' to ${CareFormat.date(_end!, year: true)}'}',
                ),
                const SizedBox(height: 18),
                const CareNotice(
                  'Use the instructions you were prescribed. CareLink does not choose or change doses.',
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('Back'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('Save schedule'),
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
      await widget.api.call('POST', '/schedules', {
        'name': _name.text.trim(),
        'instructions': _dose.text.trim(),
        'times': _times,
        'start': dayKey(_start),
        'end': _end == null ? null : dayKey(_end!),
        'timezone': _zone.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_busy,
    child: Scaffold(
      appBar: AppBar(title: const Text('Add a medicine')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'A place for your routine',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            const Text(
              'Add the medicine and daily instructions from your care plan.',
            ),
            const CareSectionHeading('Medicine details'),
            CareCard(
              child: Column(
                children: [
                  TextFormField(
                    key: const ValueKey('schedule-name'),
                    controller: _name,
                    readOnly: _busy,
                    textCapitalization: TextCapitalization.sentences,
                    decoration: const InputDecoration(
                      labelText: 'Medicine name',
                      prefixIcon: Icon(Icons.medication_outlined),
                    ),
                    validator: (value) => (value ?? '').trim().isEmpty
                        ? 'Enter the medicine name.'
                        : value!.trim().length > 100
                        ? 'Use 100 characters or fewer.'
                        : null,
                  ),
                  const SizedBox(height: 20),
                  TextFormField(
                    key: const ValueKey('schedule-instructions'),
                    controller: _dose,
                    readOnly: _busy,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Dose and instructions',
                      helperText: 'Copy the instructions you were given.',
                    ),
                    validator: (value) => (value ?? '').trim().isEmpty
                        ? 'Enter your prescribed instructions.'
                        : value!.trim().length > 300
                        ? 'Use 300 characters or fewer.'
                        : null,
                  ),
                ],
              ),
            ),
            const CareSectionHeading('Daily times'),
            CareCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Choose each time from your existing schedule.'),
                  const SizedBox(height: 16),
                  if (_times.isNotEmpty) ...[
                    Wrap(
                      spacing: 8,
                      runSpacing: 10,
                      children: [
                        for (final time in _times)
                          InputChip(
                            label: Text(CareFormat.clock(time)),
                            deleteButtonTooltipMessage:
                                'Remove ${CareFormat.clock(time)}',
                            onDeleted: _busy
                                ? null
                                : () => setState(() => _times.remove(time)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 14),
                  ],
                  OutlinedButton.icon(
                    onPressed: _busy || _times.length >= 8 ? null : _addTime,
                    icon: const Icon(Icons.add_rounded),
                    label: const Text('Add daily time'),
                  ),
                  const SizedBox(height: 10),
                  ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    childrenPadding: const EdgeInsets.only(top: 12),
                    title: const Text('Time zone'),
                    subtitle: Text(CareFormat.zone(_zone.text)),
                    children: [
                      TextFormField(
                        controller: _zone,
                        readOnly: _busy,
                        decoration: const InputDecoration(
                          labelText: 'Schedule time zone',
                          helperText:
                              'Times stay in this zone when you travel.',
                        ),
                        validator: (value) => (value ?? '').trim().isEmpty
                            ? 'Enter a time zone.'
                            : null,
                        onChanged: (_) => setState(() {}),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const CareSectionHeading('Schedule dates'),
            CareCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  CareActionRow(
                    icon: Icons.calendar_today_outlined,
                    title: 'First day',
                    subtitle: CareFormat.date(_start, year: true),
                    onTap: _busy ? null : _pickStart,
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 18),
                    child: Divider(),
                  ),
                  CareActionRow(
                    icon: Icons.event_available_outlined,
                    title: 'End date',
                    subtitle: _end == null
                        ? 'Ongoing · optional'
                        : CareFormat.date(_end!, year: true),
                    onTap: _busy ? null : _pickEnd,
                  ),
                  if (_end != null)
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => setState(() => _end = null),
                      child: const Text('Keep this schedule ongoing'),
                    ),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 20),
              CareNotice(_error!, error: true),
            ],
            const SizedBox(height: 20),
          ],
        ),
      ),
      bottomNavigationBar: CareSaveBar(
        label: 'Review and save',
        busy: _busy,
        icon: Icons.arrow_forward_rounded,
        onSave: _save,
      ),
    ),
  );
}
