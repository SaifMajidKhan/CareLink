/// Counts explicit reports. An unanswered dose is never counted as skipped.
class DaySummary {
  DaySummary(Iterable<Map<String, dynamic>> doses) {
    for (final dose in doses) {
      total++;
      if (dose['pending'] == true) pending++;
      final report = dose['report'];
      final status = report is Map
          ? report['outcome'] ?? dose['status']
          : dose['status'];
      switch (status) {
        case 'taken':
          taken++;
        case 'skipped':
          skipped++;
        case 'upcoming':
          upcoming++;
        default:
          unconfirmed++;
      }
    }
  }
  int total = 0,
      taken = 0,
      skipped = 0,
      upcoming = 0,
      unconfirmed = 0,
      pending = 0;
  int get reported => taken + skipped;
}
