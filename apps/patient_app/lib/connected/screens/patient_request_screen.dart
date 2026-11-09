import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/api_client.dart';
import '../models/patient_code.dart';
import '../widgets/care_notice.dart';
import '../widgets/care_save_bar.dart';
import 'patient_qr_scanner.dart';

class PatientRequestScreen extends StatefulWidget {
  const PatientRequestScreen({
    super.key,
    required this.api,
    this.scan = PatientQrScanner.open,
  });

  final ApiClient api;
  final Future<String?> Function(BuildContext) scan;

  @override
  State<PatientRequestScreen> createState() => _PatientRequestScreenState();
}

class _PatientRequestScreenState extends State<PatientRequestScreen> {
  final _form = GlobalKey<FormState>();
  final _patientId = TextEditingController();
  bool _sending = false, _openingScanner = false, _scanned = false;
  String? _error;

  @override
  void dispose() {
    _patientId.dispose();
    super.dispose();
  }

  Future<void> _scan() async {
    if (_sending || _openingScanner) return;
    FocusScope.of(context).unfocus();
    setState(() => _openingScanner = true);
    try {
      final scanned = await widget.scan(context);
      if (!mounted || scanned == null) return;
      final id = PatientCode.fromInput(scanned);
      if (id == null) return;
      setState(() {
        _patientId.text = id;
        _scanned = true;
        _error = null;
      });
      _form.currentState?.validate();
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Could not open the camera. Enter the patient ID instead.',
        );
      }
    } finally {
      if (mounted) setState(() => _openingScanner = false);
    }
  }

  Future<void> _send() async {
    if (_sending || _openingScanner || !_form.currentState!.validate()) return;
    final id = PatientCode.fromInput(_patientId.text)!;
    FocusScope.of(context).unfocus();
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await widget.api.call('POST', '/connections', {'patient_id': id});
      if (mounted) Navigator.pop(context, true);
    } on ApiFailure catch (error) {
      if (!mounted) return;
      setState(() {
        _error = switch (error.status) {
          401 => 'Sign in again to send a request.',
          404 =>
            'Patient not found. Check the ID or ask for their current QR code.',
          409 => 'You already have a request or connection for this patient.',
          0 => 'Could not send the request. Check your internet connection and try again.',
          _ => error.message,
        };
      });
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_sending,
    child: Scaffold(
      appBar: AppBar(title: const Text('Add a patient')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
          children: [
            OutlinedButton.icon(
              onPressed: _sending || _openingScanner ? null : _scan,
              icon: const Icon(Icons.qr_code_scanner_rounded),
              label: const Text('Scan patient QR'),
            ),
            const SizedBox(height: 16),
            TextFormField(
              key: const ValueKey('patient-id-input'),
              controller: _patientId,
              readOnly: _sending,
              autocorrect: false,
              enableSuggestions: false,
              textCapitalization: TextCapitalization.characters,
              inputFormatters: [LengthLimitingTextInputFormatter(100)],
              decoration: const InputDecoration(
                labelText: 'Patient ID',
                hintText: 'Starts with CL-',
              ),
              validator: (text) => PatientCode.fromInput(text ?? '') == null
                  ? 'Scan the patient QR or enter their full CL- ID.'
                  : null,
              onChanged: (_) {
                if (_error != null || _scanned) {
                  setState(() {
                    _error = null;
                    _scanned = false;
                  });
                }
              },
            ),
            if (_scanned) ...[
              const SizedBox(height: 10),
              const Text('QR read. Check the ID before sending.'),
            ],
            const SizedBox(height: 14),
            const CareNotice(
              'The patient must approve your request before you can see their records.',
              icon: Icons.shield_outlined,
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Semantics(
                liveRegion: true,
                child: CareNotice(_error!, error: true),
              ),
            ],
          ],
        ),
      ),
      bottomNavigationBar: CareSaveBar(
        label: 'Send request',
        icon: Icons.send_outlined,
        busy: _sending,
        onSave: _openingScanner ? null : _send,
      ),
    ),
  );
}
