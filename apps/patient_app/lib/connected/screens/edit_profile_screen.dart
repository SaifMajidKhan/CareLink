import 'package:flutter/material.dart';

import '../auth/auth_validation.dart';
import '../data/api_client.dart';
import '../widgets/care_card.dart';
import '../widgets/care_notice.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({
    super.key,
    required this.api,
    required this.profile,
  });
  final ApiClient api;
  final Map<String, dynamic> profile;
  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _name;
  late String _condition;
  bool _busy = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.profile['name']);
    _condition = widget.profile['condition'] ?? '';
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final data = await widget.api.call('PUT', '/me', {
        'name': _name.text.trim(),
        'condition': _condition,
      });
      if (mounted) Navigator.pop(context, Map<String, dynamic>.from(data));
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
      appBar: AppBar(title: const Text('Edit profile')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Make it yours',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 10),
            const Text(
              'Keep the details you share with your care team up to date.',
            ),
            const SizedBox(height: 26),
            CareCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    controller: _name,
                    readOnly: _busy,
                    textCapitalization: TextCapitalization.words,
                    validator: AuthValidation.name,
                    decoration: const InputDecoration(
                      labelText: 'Full name',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                  ),
                  const SizedBox(height: 20),
                  DropdownButtonFormField<String>(
                    initialValue: _condition,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Condition you manage',
                    ),
                    items: const [
                      DropdownMenuItem(value: '', child: Text('Not specified')),
                      DropdownMenuItem(
                        value: 'hypertension',
                        child: Text('Hypertension'),
                      ),
                      DropdownMenuItem(
                        value: 'diabetes',
                        child: Text('Diabetes'),
                      ),
                      DropdownMenuItem(
                        value: 'both',
                        child: Text('Hypertension & diabetes'),
                      ),
                    ],
                    onChanged: _busy
                        ? null
                        : (value) => setState(() => _condition = value!),
                  ),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 20),
              CareNotice(_error!, error: true),
            ],
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        minimum: const EdgeInsets.all(20),
        child: FilledButton(
          onPressed: _busy ? null : _save,
          child: Text(_busy ? 'Saving…' : 'Save changes'),
        ),
      ),
    ),
  );
}
