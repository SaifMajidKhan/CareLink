import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../data/account_store.dart';
import '../data/reminders.dart';
import 'report_form.dart';
import 'schedule_form.dart';
import 'readings_screen.dart';
import 'care_screen.dart';

class Dashboard extends StatefulWidget {
  const Dashboard({
    super.key,
    required this.store,
    required this.user,
    required this.onLogout,
    required this.onRenew,
  });
  final AccountStore store;
  final Map<String, dynamic> user;
  final Future<void> Function() onLogout;
  final Future<void> Function(BuildContext) onRenew;
  @override
  State<Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<Dashboard> with WidgetsBindingObserver {
  final reminders = Reminders();
  List<Map<String, dynamic>> _doses = [];
  int _tab = 0;
  bool _busy = false, _remindersEnabled = false;
  String? _message, _updated;
  DateTime _historyDate = DateTime.now();
  Timer? _retry;
  AccountStore get store => widget.store;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    reminders.onAction = (payload, action) async {
      final dose = Map<String, dynamic>.from(jsonDecode(payload));
      if (dose['account'] != store.scope) return;
      await _refresh();
      if (!mounted) return;
      final matches = _doses.where((d) => d['key'] == dose['key']);
      if (matches.isEmpty) return;
      final current = matches.first;
      if (current['report'] != null || current['pending'] == true) return;
      if (action == 'snooze') {
        await reminders.snooze(current);
      } else {
        await _record(
          current,
          action == 'taken' || action == 'skipped' ? action : null,
        );
      }
    };
    _start();
    _retry = Timer.periodic(const Duration(seconds: 60), (_) => _refresh());
  }

  Future<void> _start() async {
    try {
      final settings = await store.cached('reminders');
      _remindersEnabled = settings?['data'] == true;
      await reminders.initialize();
      await _refresh();
      await reminders.handleLaunch();
    } catch (e) {
      if (mounted) setState(() => _message = 'Could not restore reminders: $e');
    }
  }

  @override
  void dispose() {
    _retry?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _refresh();
  }

  Future<void> _refresh() async {
    if (_busy) return;
    setState(() => _busy = true);
    String? message;
    final start = dayKey(DateTime.now().subtract(const Duration(days: 30)));
    final end = dayKey(DateTime.now().add(const Duration(days: 7)));
    try {
      await store.sync();
      final data = await store.api.call(
        'GET',
        '/patients/${store.userId}/doses?start=$start&end=$end',
      );
      await store.cache('doses', data);
    } catch (e) {
      message = e.toString();
    }
    try {
      final cached = await store.cached('doses');
      final pending = await store.pending();
      final rows = (cached?['data'] as List? ?? [])
          .map((d) => Map<String, dynamic>.from(d))
          .toList();
      for (final dose in rows) {
        dose['account'] = store.scope;
        final queued = pending.where((p) => p['key'] == dose['key']);
        if (queued.isNotEmpty) {
          dose['server_report'] = dose['report'];
          dose['report'] = queued.first['body'];
          dose['pending'] = true;
          dose['upload_error'] = queued.first['error'];
          dose['status'] = queued.first['body']['outcome'];
        } else {
          final ack = await store.cached('report:${dose['key']}');
          if (ack != null &&
              (dose['report'] == null ||
                  (ack['data']['version'] as int) >
                      (dose['report']['version'] as int))) {
            dose['report'] = ack['data'];
            dose['status'] = ack['data']['outcome'];
          }
        }
      }
      if (_remindersEnabled) {
        await reminders.schedule(rows);
      }
      if (mounted) {
        setState(() {
          _doses = rows;
          _updated = cached?['updated'];
          _message = message;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _message = 'Phone storage could not be loaded: $e');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _record(Map<String, dynamic> dose, [String? initial]) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ReportForm(
          dose: dose,
          store: store,
          initialOutcome: initial,
          afterSave: () async {
            try {
              await reminders.cancel(dose['key']);
            } catch (_) {
              /* Report remains safely queued if notification cancellation fails. */
            }
          },
        ),
      ),
    );
    if (mounted) await _refresh();
  }

  Future<void> _addSchedule() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ScheduleForm(api: store.api)),
    );
    if (mounted) await _refresh();
  }

  Future<void> _enable() async {
    try {
      final allowed = await reminders.permission();
      if (!allowed) throw Exception('Allow notifications in Android settings.');
      setState(() => _remindersEnabled = true);
      await store.cache('reminders', true);
      await _refresh();
      if (mounted) {
        setState(
          () => _message = 'Reminders scheduled for the next 7 days. Open CareLink regularly to renew them. Android may delay delivery.',
        );
      }
    } catch (e) {
      if (mounted) setState(() => _message = e.toString());
    }
  }

  Future<void> _editProfile() async {
    final name = TextEditingController(text: widget.user['name']);
    String condition = widget.user['condition'] ?? '';
    final save = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, change) => AlertDialog(
          title: const Text('Edit profile'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: name,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              DropdownButton<String>(
                value: condition,
                items: const [
                  DropdownMenuItem(value: '', child: Text('Not specified')),
                  DropdownMenuItem(
                    value: 'hypertension',
                    child: Text('Hypertension'),
                  ),
                  DropdownMenuItem(value: 'diabetes', child: Text('Diabetes')),
                  DropdownMenuItem(value: 'both', child: Text('Both')),
                ],
                onChanged: (v) => change(() => condition = v!),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Save online'),
            ),
          ],
        ),
      ),
    );
    if (save == true) {
      try {
        final result = await store.api.call('PUT', '/me', {
          'name': name.text.trim(),
          'condition': condition,
        });
        if (mounted) {
          setState(() => widget.user.addAll(Map<String, dynamic>.from(result)));
        }
      } catch (e) {
        if (mounted) setState(() => _message = e.toString());
      }
    }
    name.dispose();
  }

  Future<void> _logout() async {
    if ((await store.pending()).isNotEmpty) {
      if (mounted) {
        setState(
          () => _message =
              'Upload or resolve pending reports before signing out.',
        );
      }
      return;
    }
    if (!mounted) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text(
          'This clears downloaded account records and reminders from this phone. Uploaded records stay on the server.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await store.api.call('POST', '/auth/logout');
      await reminders.cancelAll();
      await store.clear();
      await widget.onLogout();
    } catch (e) {
      if (mounted) setState(() => _message = e.toString());
    }
  }

  Future<void> _conflict(Map<String, dynamic> dose) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Review upload problem'),
        content: SelectableText(
          'On this phone: ${_describe(dose['report'])}\n\nLast downloaded server report: ${_describe(dose['server_report'])}\n\n${dose['upload_error']}\n\nDiscarding removes only this unsent local version. Refresh first to check the latest server record.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('Keep local report'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('Discard local version'),
          ),
        ],
      ),
    );
    if (yes == true) {
      await store.discardConflict(dose['key']);
      await _refresh();
    }
  }

  String _describe(dynamic report) => report == null
      ? 'No report available'
      : '${report['outcome']}\nEntered: ${report['recorded_at']}${report['taken_at'] == null ? '' : '\nTaken: ${report['taken_at']}'}';

  Widget _card(Map<String, dynamic> d) {
    final pending = d['pending'] == true, report = d['report'];
    final status = pending
        ? '${d['status']} • upload pending'
        : d['status'] == 'taken'
        ? 'Reported taken'
        : d['status'] == 'skipped'
        ? 'Reported skipped'
        : d['status'] == 'upcoming'
        ? 'Upcoming'
        : 'Not confirmed';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${d['time']} • ${d['timezone']}',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            Text(d['name'], style: Theme.of(context).textTheme.titleLarge),
            Text(d['instructions']),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: Chip(label: Text(status)),
            ),
            if (report != null)
              Text(
                'Entered: ${report['recorded_at']}${report['taken_at'] == null ? '' : '\nTaken: ${report['taken_at']}'}${report['approximate'] == true ? ' (approximate)' : ''}',
              ),
            if (pending) const Text('Saved on this phone—waiting to upload'),
            if (d['upload_error'] != null)
              TextButton(
                onPressed: () => _conflict(d),
                child: const Text('Review upload problem'),
              ),
            if (!pending &&
                DateTime.parse(d['scheduled_at']).isBefore(DateTime.now()))
              FilledButton(
                onPressed: () => _record(d),
                child: Text(report == null ? 'Record dose' : 'Correct report'),
              ),
            if (report == null && _remindersEnabled)
              TextButton(
                onPressed: () async {
                  try {
                    await reminders.snooze(d);
                    if (mounted) {
                      setState(
                        () => _message = 'Reminder snoozed for 10 minutes. Your schedule is unchanged.',
                      );
                    }
                  } catch (e) {
                    if (mounted) setState(() => _message = e.toString());
                  }
                },
                child: const Text('Remind me in 10 minutes'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _profile() => ListView(
    padding: const EdgeInsets.all(24),
    children: [
      const CircleAvatar(radius: 32, child: Icon(Icons.person, size: 36)),
      const SizedBox(height: 16),
      Text(
        widget.user['name'],
        style: Theme.of(context).textTheme.headlineMedium,
      ),
      Text('Patient • ${widget.user['condition']}'),
      OutlinedButton(
        onPressed: _editProfile,
        child: const Text('Edit profile'),
      ),
      const SizedBox(height: 16),
      const Text('Your Patient ID'),
      SelectableText(store.userId),
      Center(
        child: QrImageView(
          data: 'carelink:patient:${store.userId}',
          size: 210,
          backgroundColor: Colors.white,
        ),
      ),
      const Text(
        'This QR starts a connection request. You decide who can see your records.',
      ),
      FilledButton.icon(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => CareScreen(api: store.api)),
        ),
        icon: const Icon(Icons.people_outline),
        label: const Text('My caregivers & requests'),
      ),
      OutlinedButton.icon(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ReadingsScreen(store: store)),
        ),
        icon: const Icon(Icons.monitor_heart_outlined),
        label: const Text('Health readings'),
      ),
      OutlinedButton.icon(
        onPressed: _addSchedule,
        icon: const Icon(Icons.medication_outlined),
        label: const Text('Add medication schedule'),
      ),
      OutlinedButton(
        onPressed: _manageSchedules,
        child: const Text('Manage schedules'),
      ),
      OutlinedButton(
        onPressed: _enable,
        child: const Text('Enable / refresh reminders'),
      ),
      const Text(
        'FYP demonstration. Fictional data only. Reports are self-reported. No diagnostic or treatment advice.',
      ),
      TextButton(onPressed: _logout, child: const Text('Sign out')),
      TextButton(
        onPressed: () => widget.onRenew(context),
        child: const Text('Renew sign-in without losing pending reports'),
      ),
    ],
  );
  Future<void> _manageSchedules() async {
    try {
      final rows = await store.api.call(
        'GET',
        '/patients/${store.userId}/schedules',
      ) as List;
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Medication schedules'),
          content: SizedBox(
            width: 400,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'To change a schedule, end its future occurrences and create a replacement. Historical expectations stay unchanged.',
                  ),
                  for (final r in rows)
                    ListTile(
                      title: Text(r['name']),
                      subtitle: Text(
                        '${r['times']}\n${r['start']} → ${r['end'] ?? 'ongoing'}',
                      ),
                      trailing: TextButton(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: DateTime.now(),
                            firstDate: DateTime.now(),
                            lastDate: DateTime.now().add(
                              const Duration(days: 730),
                            ),
                          );
                          if (picked == null) return;
                          try {
                            await store.api.call(
                              'POST',
                              '/schedules/${r['id']}/stop',
                              {'end': dayKey(picked)},
                            );
                            if (c.mounted) Navigator.pop(c);
                            await _refresh();
                          } catch (e) {
                            if (mounted) {
                              setState(() => _message = e.toString());
                            }
                          }
                        },
                        child: const Text('End after…'),
                      ),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (mounted) setState(() => _message = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final day = dayKey(_tab == 1 ? _historyDate : DateTime.now());
    final visible = _doses
        .where(
          (d) => _tab == 0
              ? dayKey(DateTime.parse(d['scheduled_at']).toLocal()) == day
              : d['day'] == day,
        )
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: Text(['CareLink', 'Dose history', 'Your profile'][_tab]),
        actions: [
          IconButton(
            onPressed: _busy ? null : _refresh,
            icon: const Icon(Icons.sync),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_busy) const LinearProgressIndicator(),
          if (_message != null)
            MaterialBanner(
              content: Text(_message!),
              actions: [
                TextButton(
                  onPressed: () => setState(() => _message = null),
                  child: const Text('Dismiss'),
                ),
              ],
            ),
          Expanded(
            child: _tab == 2
                ? _profile()
                : RefreshIndicator(
                    onRefresh: _refresh,
                    child: ListView(
                      padding: const EdgeInsets.all(24),
                      children: [
                        if (_tab == 0) ...[
                          Text(
                            'Hello, ${widget.user['name']}',
                            style: Theme.of(context).textTheme.headlineMedium,
                          ),
                          const Text('Your day, one dose at a time.'),
                          const SizedBox(height: 16),
                        ],
                        if (_tab == 1)
                          TextButton.icon(
                            onPressed: () async {
                              final d = await showDatePicker(
                                context: context,
                                initialDate: _historyDate,
                                firstDate: DateTime.now().subtract(
                                  const Duration(days: 30),
                                ),
                                lastDate: DateTime.now(),
                              );
                              if (d != null && mounted) {
                                setState(() => _historyDate = d);
                              }
                            },
                            icon: const Icon(Icons.calendar_month),
                            label: Text(day),
                          ),
                        if (_updated != null)
                          Text(
                            'Last downloaded: $_updated',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        if (visible.isEmpty) ...[
                          const SizedBox(height: 32),
                          const Text('No saved doses for this day.'),
                          if (_tab == 0)
                            FilledButton(
                              onPressed: _addSchedule,
                              child: const Text('Add your first schedule'),
                            ),
                        ],
                        for (final d in visible) _card(d),
                        const SizedBox(height: 16),
                        const Text(
                          'No response stays Not confirmed. It does not mean a dose was skipped.',
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            label: 'Today',
          ),
          NavigationDestination(icon: Icon(Icons.history), label: 'History'),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
