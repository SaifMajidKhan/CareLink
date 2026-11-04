import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../data/account_store.dart';
import '../utils/care_format.dart';
import '../widgets/care_card.dart';
import '../widgets/care_empty_state.dart';
import '../widgets/care_notice.dart';
import 'reading_form.dart';

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
    String? error;
    try {
      final data = await widget.store.api.call(
        'GET',
        '/patients/${widget.store.userId}/readings',
      );
      await widget.store.cache('readings', data);
    } catch (failure) {
      error = failure.toString();
    }
    try {
      final cache = await widget.store.cached('readings');
      if (mounted) {
        setState(() {
          _rows = cache?['data'] ?? [];
          _updated = cache?['updated'];
          _error = error;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'The saved readings on this phone could not be loaded. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _add() async {
    final saved = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => ReadingForm(api: widget.store.api)),
    );
    if (saved == true && mounted) await _load();
  }

  Widget _reading(dynamic row) {
    final pressure = row['kind'] == 'blood_pressure';
    return CareCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.tealSoft,
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(
                  pressure
                      ? Icons.monitor_heart_outlined
                      : Icons.water_drop_outlined,
                  color: AppTheme.teal,
                  size: 23,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  pressure ? 'Blood pressure' : 'Blood glucose',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 8,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [
              Text(
                '${CareFormat.number(row['value'])}${row['secondary'] == null ? '' : ' / ${CareFormat.number(row['secondary'])}'}',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(row['unit']),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            CareFormat.stamp(row['measured_at']),
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Health readings'),
      actions: [
        IconButton(
          tooltip: 'Refresh readings',
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
            'Your readings, together',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 10),
          const Text(
            'Keep the measurements you enter in one easy-to-find place.',
          ),
          const SizedBox(height: 18),
          CareSyncLine(updated: _updated, busy: _busy),
          const SizedBox(height: 22),
          if (_busy) const LinearProgressIndicator(),
          if (_error != null) ...[
            CareNotice(_error!, error: true),
            const SizedBox(height: 16),
          ],
          if (!_busy && _rows.isEmpty && _error == null)
            CareEmptyState(
              icon: Icons.monitor_heart_outlined,
              title: 'A clearer picture starts here',
              message: 'Save a reading when you have one. The date, time and unit stay with your record.',
              actionLabel: 'Add a reading',
              onAction: _add,
            ),
          for (final row in _rows) ...[
            _reading(row),
            const SizedBox(height: 14),
          ],
          if (_rows.isNotEmpty) ...[
            const SizedBox(height: 6),
            const CareNotice(
              'These are the values you recorded. Follow your healthcare professional’s advice about what they mean.',
            ),
          ],
        ],
      ),
    ),
    floatingActionButton: _rows.isEmpty
        ? null
        : FloatingActionButton.extended(
            onPressed: _add,
            icon: const Icon(Icons.add_rounded),
            label: const Text('Add reading'),
          ),
  );
}
