import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';

import '../data/account_store.dart';
import '../data/api_client.dart';
import '../data/reminders.dart';
import 'report_form.dart';
import 'schedule_form.dart';
import 'readings_screen.dart';
import 'care_screen.dart';
import 'care_identity_screen.dart';
import 'edit_profile_screen.dart';
import 'manage_schedules_screen.dart';
import '../views/today_view.dart';
import '../views/history_view.dart';
import '../views/profile_view.dart';
import '../widgets/carelink_brand.dart';
import '../widgets/care_notice.dart';
import '../widgets/connected_dose_card.dart';
import '../../core/theme/app_theme.dart';
import '../utils/care_format.dart';

class Dashboard extends StatefulWidget {
  const Dashboard({
    super.key,
    required this.store,
    required this.user,
    required this.onLogout,
    required this.onRenew,
    this.onProfileChanged,
  });
  final AccountStore store;
  final Map<String, dynamic> user;
  final Future<void> Function() onLogout;
  final Future<void> Function(BuildContext) onRenew;
  final Future<void> Function(Map<String, dynamic>)? onProfileChanged;
  @override
  State<Dashboard> createState() => _DashboardState();
}

class _DashboardState extends State<Dashboard> with WidgetsBindingObserver {
  final reminders = Reminders();
  List<Map<String, dynamic>> _doses = [];
  int _tab = 0, _pendingCount = 0;
  late Map<String, dynamic> _profileData;
  bool _busy = false, _remindersEnabled = false;
  String? _message, _updated;
  DateTime _historyDate = DateTime.now();
  Timer? _retry;
  AccountStore get store => widget.store;
  @override
  void initState() {
    super.initState();
    _profileData = Map<String, dynamic>.from(widget.user);
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
  void didUpdateWidget(covariant Dashboard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.user != widget.user) {
      _profileData = Map<String, dynamic>.from(widget.user);
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
          _pendingCount = pending.length;
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
    final result = await Navigator.push<Map<String, dynamic>>(
      context,
      MaterialPageRoute(
        builder: (_) =>
            EditProfileScreen(api: store.api, profile: _profileData),
      ),
    );
    if (result == null || !mounted) return;
    setState(() => _profileData = result);
    try {
      await widget.onProfileChanged?.call(result);
    } catch (_) {
      if (mounted) {
        setState(
          () => _message = 'Your profile was saved online. This phone could not remember the updated details yet.',
        );
      }
    }
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
    } on ApiFailure {
      // Remote revocation is best-effort; confirmed local sign-out must work offline.
      // The pending-report guard above still protects unsent records.
    }
    try {
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
      : '${report['outcome']}\nRecorded: ${CareFormat.stamp(report['recorded_at'])}${report['taken_at'] == null ? '' : '\nTaken: ${CareFormat.stamp(report['taken_at'])}'}';

  Future<void> _identity() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CareIdentityScreen(
          patientId: store.userId,
          name: '${_profileData['name']}',
        ),
      ),
    );
  }

  Future<void> _care() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CareScreen(
          api: store.api,
          patientId: store.userId,
          name: '${_profileData['name']}',
        ),
      ),
    );
  }

  Future<void> _readings() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ReadingsScreen(store: store)),
    );
  }

  Future<void> _manageSchedules() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) =>
            ManageSchedulesScreen(api: store.api, patientId: store.userId),
      ),
    );
    if (mounted) await _refresh();
  }

  Future<void> _snooze(Map<String, dynamic> dose) async {
    try {
      await reminders.snooze(dose);
      if (mounted) {
        setState(
          () => _message =
              'Reminder snoozed for 10 minutes. Your schedule is unchanged.',
        );
      }
    } catch (error) {
      if (mounted) setState(() => _message = error.toString());
    }
  }

  Future<void> _pickHistoryDate() async {
    final today = DateUtils.dateOnly(DateTime.now());
    final picked = await showDatePicker(
      context: context,
      initialDate: _historyDate,
      firstDate: today.subtract(const Duration(days: 30)),
      lastDate: today,
      helpText: 'Choose a day',
    );
    if (picked != null && mounted) setState(() => _historyDate = picked);
  }

  Widget _card(Map<String, dynamic> dose) => ConnectedDoseCard(
    dose: dose,
    onRecord: () => _record(dose),
    onConflict: () => _conflict(dose),
    onSnooze: _remindersEnabled ? () => _snooze(dose) : null,
  );

  @override
  Widget build(BuildContext context) {
    final day = dayKey(_tab == 1 ? _historyDate : DateTime.now());
    final visible = _doses
        .where(
          (dose) => _tab == 0
              ? dayKey(DateTime.parse(dose['scheduled_at']).toLocal()) == day
              : dose['day'] == day,
        )
        .toList();
    final view = switch (_tab) {
      1 => HistoryView(
        date: _historyDate,
        doses: visible,
        doseBuilder: _card,
        updated: _updated,
        busy: _busy,
        onCalendar: _pickHistoryDate,
        onDate: (date) => setState(() => _historyDate = date),
        onToday: () => setState(() => _tab = 0),
      ),
      2 => ProfileView(
        user: _profileData,
        patientId: store.userId,
        updated: _updated,
        pending: _pendingCount,
        remindersEnabled: _remindersEnabled,
        onEdit: _editProfile,
        onIdentity: _identity,
        onCare: _care,
        onReadings: _readings,
        onAdd: _addSchedule,
        onManage: _manageSchedules,
        onReminders: _enable,
        onLogout: _logout,
        onRenew: () => widget.onRenew(context),
      ),
      _ => TodayView(
        unavailable: _updated == null && _message != null,
        onRetry: _refresh,
        name: '${_profileData['name']}',
        doses: visible,
        doseBuilder: _card,
        updated: _updated,
        pending: _pendingCount,
        busy: _busy,
        onAdd: _addSchedule,
        onReadings: _readings,
        onCare: _care,
      ),
    };
    return Scaffold(
      appBar: AppBar(
        title: const CareLinkBrand(compact: true),
        toolbarHeight: 72,
        actions: [
          Container(
            margin: const EdgeInsets.fromLTRB(0, 12, 16, 12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: AppTheme.border),
            ),
            child: IconButton(
              tooltip: 'Refresh updates',
              onPressed: _busy ? null : _refresh,
              icon: const Icon(Icons.sync_rounded, color: AppTheme.teal),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_busy) const LinearProgressIndicator(minHeight: 2),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
              child: CareNotice(
                _message!,
                warning: true,
                onDismiss: () => setState(() => _message = null),
              ),
            ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refresh,
              child: AnimatedSwitcher(
                duration: Duration(
                  milliseconds: MediaQuery.disableAnimationsOf(context)
                      ? 0
                      : 180,
                ),
                child: KeyedSubtree(key: ValueKey(_tab), child: view),
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        minimum: const EdgeInsets.fromLTRB(16, 6, 16, 12),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: AppTheme.border),
            boxShadow: const [
              BoxShadow(
                color: Color(0x080F172A),
                blurRadius: 20,
                offset: Offset(0, 6),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: NavigationBar(
              height: MediaQuery.textScalerOf(context).scale(14) > 19 ? 96 : 76,
              selectedIndex: _tab,
              onDestinationSelected: (index) => setState(() => _tab = index),
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home_rounded),
                  label: 'Today',
                ),
                NavigationDestination(
                  icon: Icon(Icons.history_outlined),
                  selectedIcon: Icon(Icons.history_rounded),
                  label: 'History',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline_rounded),
                  selectedIcon: Icon(Icons.person_rounded),
                  label: 'Profile',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
