import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../models/patient_code.dart';
import '../widgets/care_notice.dart';

class PatientQrScanner extends StatefulWidget {
  const PatientQrScanner({super.key});

  static Future<String?> open(BuildContext context) => Navigator.push<String>(
    context,
    MaterialPageRoute(builder: (_) => const PatientQrScanner()),
  );

  @override
  State<PatientQrScanner> createState() => _PatientQrScannerState();
}

class _PatientQrScannerState extends State<PatientQrScanner> {
  String? _hint;
  bool _finished = false;

  void _detect(BarcodeCapture capture) {
    if (_finished || !mounted || ModalRoute.of(context)?.isCurrent != true) {
      return;
    }
    final codes = capture.barcodes
        .where((barcode) => barcode.format == BarcodeFormat.qrCode)
        .map((barcode) => barcode.rawValue)
        .toSet();
    if (codes.isEmpty) return;
    final id = codes.length == 1 ? PatientCode.fromScan(codes.single) : null;
    if (id != null) {
      _finished = true;
      Navigator.pop(context, id);
      return;
    }
    final hint = codes.length > 1
        ? 'Show one patient QR code at a time.'
        : 'Use the CareLink QR code from the patient’s profile.';
    if (_hint != hint) setState(() => _hint = hint);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Scan patient QR')),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
      children: [
        const Text(
          'Ask the patient to open Profile → Your care ID. Point the camera at their QR code.',
        ),
        const SizedBox(height: 12),
        ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: SizedBox(
            height: (MediaQuery.sizeOf(context).height * 0.36)
                .clamp(160.0, 320.0)
                .toDouble(),
            child: MobileScanner(
              // The scanner owns the camera and pauses it when the app is inactive.
              onDetect: _detect,
              errorBuilder: (context, error) => ColoredBox(
                color: Colors.white,
                child: Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      error.errorCode == MobileScannerErrorCode.permissionDenied
                          ? 'Camera access is off. Enter the patient ID below, or allow camera access in Android settings.'
                          : 'The camera is unavailable. You can enter the patient ID instead.',
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
        if (_hint != null) ...[
          const SizedBox(height: 12),
          Semantics(liveRegion: true, child: CareNotice(_hint!)),
        ],
      ],
    ),
    bottomNavigationBar: SafeArea(
      top: false,
      minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: OutlinedButton.icon(
        onPressed: () => Navigator.pop(context),
        icon: const Icon(Icons.keyboard_outlined),
        label: const Text('Enter patient ID instead'),
      ),
    ),
  );
}
