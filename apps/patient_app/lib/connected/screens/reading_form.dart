import 'package:flutter/material.dart';

import '../data/api_client.dart';
import '../utils/care_format.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';
import '../widgets/care_save_bar.dart';

class ReadingForm extends StatefulWidget {
  const ReadingForm({super.key, required this.api});
  final ApiClient api;
  @override
  State<ReadingForm> createState() => _ReadingFormState();
}

class _ReadingFormState extends State<ReadingForm> {
  final _form = GlobalKey<FormState>();
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

  String? _positive(String? value) => (double.tryParse(value ?? '') ?? 0) > 0
      ? null
      : 'Enter a positive measured value.';

  Future<void> _pick() async {
    final day = await showDatePicker(
      context: context,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now(),
      initialDate: _at,
      helpText: 'Measurement date',
    );
    if (day == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_at),
      helpText: 'Measurement time',
    );
    if (time != null && mounted) {
      setState(
        () => _at = DateTime(
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
    if (!_form.currentState!.validate()) return;
    if (_at.isAfter(DateTime.now())) {
      setState(
        () => _error = 'Choose a measurement time that has already happened.',
      );
      return;
    }
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
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _input(
    TextEditingController controller,
    String label,
    String key, {
    String? helper,
  }) => TextFormField(
    key: ValueKey(key),
    controller: controller,
    readOnly: _busy,
    keyboardType: const TextInputType.numberWithOptions(decimal: true),
    style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w600),
    decoration: InputDecoration(labelText: label, helperText: helper),
    validator: _positive,
  );

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_busy,
    child: Scaffold(
      appBar: AppBar(title: const Text('Add a reading')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Keep a clear record',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            const Text(
              'Enter the values from a measurement you have already taken.',
            ),
            const CareSectionHeading('Reading type'),
            DropdownButtonFormField<String>(
              key: const ValueKey('reading-kind'),
              initialValue: _kind,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: 'What did you measure?',
                prefixIcon: Icon(Icons.monitor_heart_outlined),
              ),
              items: const [
                DropdownMenuItem(
                  value: 'blood_pressure',
                  child: Text('Blood pressure'),
                ),
                DropdownMenuItem(
                  value: 'glucose',
                  child: Text('Blood glucose'),
                ),
              ],
              onChanged: _busy
                  ? null
                  : (value) => setState(() {
                      _kind = value!;
                      _unit = value == 'glucose' ? 'mg/dL' : 'mmHg';
                      _value.clear();
                      _second.clear();
                      _error = null;
                    }),
            ),
            const CareSectionHeading('Measured values'),
            CareCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_kind == 'blood_pressure') ...[
                    LayoutBuilder(
                      builder: (context, box) {
                        final fields = [
                          _input(
                            _value,
                            'Systolic',
                            'reading-value',
                            helper: 'Top number · mmHg',
                          ),
                          _input(
                            _second,
                            'Diastolic',
                            'reading-secondary',
                            helper: 'Bottom number · mmHg',
                          ),
                        ];
                        if (box.maxWidth > 350 &&
                            MediaQuery.textScalerOf(context).scale(16) < 21) {
                          return Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(child: fields[0]),
                              const SizedBox(width: 16),
                              Expanded(child: fields[1]),
                            ],
                          );
                        }
                        return Column(
                          children: [
                            fields[0],
                            const SizedBox(height: 20),
                            fields[1],
                          ],
                        );
                      },
                    ),
                  ] else ...[
                    DropdownButtonFormField<String>(
                      key: ValueKey('reading-unit-$_unit'),
                      initialValue: _unit,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Your measurement unit',
                      ),
                      items: const [
                        DropdownMenuItem(value: 'mg/dL', child: Text('mg/dL')),
                        DropdownMenuItem(
                          value: 'mmol/L',
                          child: Text('mmol/L'),
                        ),
                      ],
                      onChanged: _busy
                          ? null
                          : (value) => setState(() {
                              _unit = value!;
                              _value.clear();
                              _error = null;
                            }),
                    ),
                    const SizedBox(height: 20),
                    _input(
                      _value,
                      'Blood glucose',
                      'reading-value',
                      helper: _unit,
                    ),
                  ],
                ],
              ),
            ),
            const CareSectionHeading('When was it measured?'),
            CareCard(
              padding: EdgeInsets.zero,
              child: CareActionRow(
                icon: Icons.event_outlined,
                title: 'Date and time',
                subtitle: CareFormat.stamp(_at.toIso8601String()),
                onTap: _busy ? null : _pick,
                trailing: const Icon(Icons.edit_outlined, size: 20),
              ),
            ),
            const SizedBox(height: 20),
            const CareNotice(
              'An internet connection is needed to save a reading.',
              icon: Icons.cloud_outlined,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              CareNotice(_error!, error: true),
            ],
            const SizedBox(height: 12),
          ],
        ),
      ),
      bottomNavigationBar: CareSaveBar(
        label: 'Save reading',
        busy: _busy,
        onSave: _save,
      ),
    ),
  );
}
