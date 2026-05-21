import 'package:intl/intl.dart';

final DateFormat _yyyyMMdd = DateFormat('yyyy.MM.dd', 'ko_KR');
final DateFormat _yyyyMM = DateFormat('yyyy.MM', 'ko_KR');

String formatYmd(DateTime d) => _yyyyMMdd.format(d);

String formatYm(DateTime d) => _yyyyMM.format(d);

String formatRelative(DateTime when, {DateTime? now}) {
  final base = now ?? DateTime.now();
  final diff = base.difference(when);
  if (diff.inMinutes < 1) return '방금';
  if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
  if (diff.inHours < 24) return '${diff.inHours}시간 전';
  if (diff.inDays < 7) return '${diff.inDays}일 전';
  return formatYmd(when);
}
