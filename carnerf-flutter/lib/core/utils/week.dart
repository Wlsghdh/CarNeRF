const int _kstOffsetMs = 9 * 60 * 60 * 1000;

DateTime nowKst() =>
    DateTime.fromMillisecondsSinceEpoch(DateTime.now().millisecondsSinceEpoch + _kstOffsetMs, isUtc: true);

DateTime weekStartKst([DateTime? d]) {
  final base = d ?? nowKst();
  final dow = base.weekday;
  final diff = (dow + 6) % 7;
  final ws = DateTime.utc(base.year, base.month, base.day).subtract(Duration(days: diff));
  return ws;
}

String weekKey([DateTime? d]) {
  final ws = weekStartKst(d);
  final year = ws.year;
  final first = DateTime.utc(year, 1, 1);
  final days = ws.difference(first).inDays;
  final week = ((days + first.weekday) / 7).ceil();
  return '$year-W${week.toString().padLeft(2, '0')}';
}

class CountdownParts {
  const CountdownParts({
    required this.days,
    required this.hours,
    required this.minutes,
    required this.seconds,
    required this.totalMs,
  });

  final int days;
  final int hours;
  final int minutes;
  final int seconds;
  final int totalMs;
}

CountdownParts timeToNextMondayKst([DateTime? d]) {
  final base = d ?? nowKst();
  final ws = weekStartKst(base);
  final next = ws.add(const Duration(days: 7));
  final totalMs = next.difference(base).inMilliseconds;
  return CountdownParts(
    days: totalMs ~/ 86400000,
    hours: (totalMs % 86400000) ~/ 3600000,
    minutes: (totalMs % 3600000) ~/ 60000,
    seconds: (totalMs % 60000) ~/ 1000,
    totalMs: totalMs,
  );
}

double Function() mulberry32(int seed) {
  var a = seed & 0xFFFFFFFF;
  return () {
    a = (a + 0x6D2B79F5) & 0xFFFFFFFF;
    var t = a;
    t = (t ^ (t >>> 15)) & 0xFFFFFFFF;
    t = _imul(t, 1 | a);
    t = (t + _imul(t ^ (t >>> 7), 61 | t)) & 0xFFFFFFFF;
    t = t ^ t;
    t = a;
    t = (t ^ (t >>> 15)) & 0xFFFFFFFF;
    t = _imul(t, 1 | a);
    var u = (t ^ (t >>> 7)) & 0xFFFFFFFF;
    u = _imul(u, 61 | t);
    t = (t + u) & 0xFFFFFFFF;
    t = (t ^ (t >>> 14)) & 0xFFFFFFFF;
    return t / 4294967296;
  };
}

int _imul(int a, int b) {
  final aHi = (a >>> 16) & 0xFFFF;
  final aLo = a & 0xFFFF;
  final bHi = (b >>> 16) & 0xFFFF;
  final bLo = b & 0xFFFF;
  return ((aLo * bLo) + (((aHi * bLo + aLo * bHi) & 0xFFFF) << 16)) & 0xFFFFFFFF;
}

int hashSeed(String s) {
  var h = 2166136261 & 0xFFFFFFFF;
  for (final code in s.codeUnits) {
    h = (h ^ code) & 0xFFFFFFFF;
    h = _imul(h, 16777619);
  }
  return h & 0xFFFFFFFF;
}
