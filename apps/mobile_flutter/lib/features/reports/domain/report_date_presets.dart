// Date presets for report filters (mirrors desktop `reportDatePresets.ts`).

typedef ReportDatePreset = String;

abstract final class ReportDatePresets {
  static const none = '';
  static const today = 'today';
  static const yesterday = 'yesterday';
  static const week = 'week';
  static const month = 'month';
  static const quarter = 'quarter';
  static const year = 'year';
  static const custom = 'custom';

  static const labels = <String, String>{
    none: 'All dates',
    today: 'Today',
    yesterday: 'Yesterday',
    week: 'This week',
    month: 'This month',
    quarter: 'This quarter',
    year: 'This year',
    custom: 'Custom range',
  };
}

class ReportDateRange {
  const ReportDateRange({required this.from, required this.to});

  final String from;
  final String to;
}

DateTime _startOfDay(DateTime date) => DateTime(date.year, date.month, date.day);

DateTime _endOfDay(DateTime date) =>
    DateTime(date.year, date.month, date.day, 23, 59, 59, 999);

String _isoDateTime(DateTime date) => date.toUtc().toIso8601String();

ReportDateRange resolveReportDatePreset(String preset) {
  final today = _startOfDay(DateTime.now());
  switch (preset) {
    case ReportDatePresets.today:
      return ReportDateRange(from: _isoDateTime(today), to: _isoDateTime(_endOfDay(today)));
    case ReportDatePresets.yesterday:
      final yesterday = today.subtract(const Duration(days: 1));
      return ReportDateRange(
        from: _isoDateTime(yesterday),
        to: _isoDateTime(_endOfDay(yesterday)),
      );
    case ReportDatePresets.week:
      final start = today.subtract(Duration(days: today.weekday % 7));
      return ReportDateRange(from: _isoDateTime(start), to: _isoDateTime(_endOfDay(today)));
    case ReportDatePresets.month:
      final start = DateTime(today.year, today.month);
      return ReportDateRange(from: _isoDateTime(start), to: _isoDateTime(_endOfDay(today)));
    case ReportDatePresets.quarter:
      final quarter = (today.month - 1) ~/ 3;
      final start = DateTime(today.year, quarter * 3 + 1);
      return ReportDateRange(from: _isoDateTime(start), to: _isoDateTime(_endOfDay(today)));
    case ReportDatePresets.year:
      final start = DateTime(today.year);
      return ReportDateRange(from: _isoDateTime(start), to: _isoDateTime(_endOfDay(today)));
    default:
      return const ReportDateRange(from: '', to: '');
  }
}

ReportDateRange reportDateInputRange(String from, String to) {
  return ReportDateRange(
    from: from.isNotEmpty ? '${from}T00:00:00.000Z' : '',
    to: to.isNotEmpty ? '${to}T23:59:59.999Z' : '',
  );
}

ReportDateRange resolveReportDateRange(String preset, String from, String to) {
  if (preset.isNotEmpty && preset != ReportDatePresets.custom) {
    return resolveReportDatePreset(preset);
  }
  return reportDateInputRange(from, to);
}
