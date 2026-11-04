import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_action_row.dart';
import '../widgets/care_notice.dart';
import '../widgets/care_save_bar.dart';
import '../widgets/dose_outcome_option.dart';

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
        throw ApiFailure('Choose a time that has already happened.');
      }
      final version = widget.dose['report']?['version'] ?? 0;
      if (version > 0 && _reason.text.trim().isEmpty) {
        throw ApiFailure('Please explain why you are correcting this report.');
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
      appBar: AppBar(
        title: Text(
          widget.dose['report'] == null ? 'Record dose' : 'Correct report',
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Your update matters',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 10),
          const Text('Record what happened, when it works for you.'),
          const SizedBox(height: 24),
          CareCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.dose['name'],
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 7),
                Text(widget.dose['instructions']),
                const SizedBox(height: 14),
                Text(
                  'Scheduled for ${CareFormat.clock(widget.dose['time'])} · ${CareFormat.date(DateTime.parse(widget.dose['day']))}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const CareSectionHeading('How did this dose go?'),
          DoseOutcomeOption(
            taken: true,
            selected: _outcome == 'taken',
            onTap: _busy ? null : () => setState(() => _outcome = 'taken'),
          ),
          const SizedBox(height: 12),
          DoseOutcomeOption(
            taken: false,
            selected: _outcome == 'skipped',
            onTap: _busy ? null : () => setState(() => _outcome = 'skipped'),
          ),
          if (_outcome == 'taken') ...[
            const CareSectionHeading('When did you take it?'),
            CareCard(
              padding: EdgeInsets.zero,
              child: Column(
                children: [
                  CareActionRow(
                    icon: Icons.access_time_rounded,
                    title: 'Time taken',
                    subtitle: CareFormat.stamp(_taken.toIso8601String()),
                    onTap: _busy ? null : _pick,
                    trailing: const Icon(Icons.edit_outlined, size: 20),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 18),
                    child: Divider(),
                  ),
                  SwitchListTile.adaptive(
                    value: _approx,
                    onChanged: _busy
                        ? null
                        : (value) => setState(() => _approx = value),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 18,
                      vertical: 8,
                    ),
                    title: const Text('Approximate time'),
                    subtitle: const Text(
                      'Use this if you are not sure of the exact time.',
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (widget.dose['report'] != null) ...[
            const CareSectionHeading('Reason for the correction'),
            TextField(
              controller: _reason,
              readOnly: _busy,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'What changed?',
                helperText: 'Your previous report stays in the record.',
              ),
            ),
          ],
          const SizedBox(height: 24),
          const CareNotice(
            'Saved on this phone first. Your caregiver receives it after upload.',
            icon: Icons.cloud_upload_outlined,
          ),
          const SizedBox(height: 16),
          Text(
            'A report records what happened. It does not change your medicine schedule.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            CareNotice(_error!, error: true),
          ],
          const SizedBox(height: 12),
        ],
      ),
      bottomNavigationBar: CareSaveBar(
        label: 'Save record',
        busy: _busy,
        onSave: _outcome == null ? null : _save,
      ),
    ),
  );
}
