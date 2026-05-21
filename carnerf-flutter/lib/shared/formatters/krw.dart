import 'package:intl/intl.dart';

final NumberFormat _commaFmt = NumberFormat('#,###', 'ko_KR');

String formatKrw(num value) => _commaFmt.format(value);

String formatManwon(num value) => '${_commaFmt.format(value)}만원';

String formatMileageKm(num km) => '${_commaFmt.format(km)}km';

String compactKrwMan(num manwon) {
  if (manwon >= 10000) {
    final eok = manwon / 10000;
    final intPart = eok.truncate();
    final remain = (manwon - intPart * 10000).round();
    if (remain == 0) return '$intPart억';
    return '$intPart억 ${_commaFmt.format(remain)}만원';
  }
  return '${_commaFmt.format(manwon)}만원';
}
