import 'package:characters/characters.dart';

class CareFormat {
  static const _months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  static const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  static String weekday(DateTime value) => _days[value.weekday - 1];
  static String date(DateTime value, {bool year = false}) =>
      '${value.day} ${_months[value.month - 1]}${year ? ' ${value.year}' : ''}';
  static String longDate(DateTime value) => '${weekday(value)}, ${date(value)}';
  static bool sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
  static String time(DateTime value) =>
      '${value.hour % 12 == 0 ? 12 : value.hour % 12}:${value.minute.toString().padLeft(2, '0')} ${value.hour < 12 ? 'AM' : 'PM'}';
  static String clock(String value) {
    final parts = value.split(':');
    if (parts.length < 2) return value;
    final hour = int.tryParse(parts[0]), minute = int.tryParse(parts[1]);
    if (hour == null || minute == null) return value;
    return time(DateTime(2000, 1, 1, hour, minute));
  }

  static String stamp(String? value, {DateTime? now}) {
    final parsed = value == null ? null : DateTime.tryParse(value)?.toLocal();
    if (parsed == null) return 'Time unavailable';
    final current = now ?? DateTime.now();
    final day = sameDay(parsed, current)
        ? 'Today'
        : sameDay(parsed, current.subtract(const Duration(days: 1)))
        ? 'Yesterday'
        : date(parsed, year: parsed.year != current.year);
    return '$day · ${time(parsed)}';
  }

  static String updated(String? value, {DateTime? now}) {
    final parsed = value == null ? null : DateTime.tryParse(value)?.toLocal();
    if (parsed == null) return 'No downloaded updates yet';
    final current = now ?? DateTime.now();
    final age = current.difference(parsed);
    if (age.inSeconds < 60) return 'Updated just now';
    if (age.inMinutes < 60) return 'Updated ${age.inMinutes} min ago';
    return 'Updated ${stamp(value, now: current).toLowerCase()}';
  }

  static String zone(String value) =>
      value == 'Asia/Karachi' ? 'Pakistan time' : value.replaceAll('_', ' ');
  static String condition(String? value) => switch (value) {
    'hypertension' => 'Hypertension',
    'diabetes' => 'Diabetes',
    'both' => 'Hypertension & diabetes',
    _ => 'Your personal care space',
  };
  static String initials(String name) {
    final words = name
        .trim()
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty)
        .toList();
    if (words.isEmpty) return 'CL';
    return words.take(2).map((w) => w.characters.first).join().toUpperCase();
  }

  static String number(dynamic value) {
    if (value is num && value == value.roundToDouble()) {
      return value.toInt().toString();
    }
    return '$value';
  }
}
