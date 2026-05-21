enum InsurerKey { kb, samsung, db, hyundai, meritz, carrot }

class InsurerEntry {
  const InsurerEntry({
    required this.key,
    required this.name,
    required this.short,
    required this.base,
  });

  final InsurerKey key;
  final String name;
  final String short;
  final String base;
}

const List<InsurerEntry> insurers = [
  InsurerEntry(
    key: InsurerKey.kb,
    name: 'KB손해보험 다이렉트',
    short: 'KB',
    base: 'https://direct.kbinsure.co.kr/m/auto/quick.ec',
  ),
  InsurerEntry(
    key: InsurerKey.samsung,
    name: '삼성화재 다이렉트',
    short: '삼성',
    base: 'https://direct.samsungfire.com/m/auto',
  ),
  InsurerEntry(
    key: InsurerKey.db,
    name: 'DB손해보험 다이렉트',
    short: 'DB',
    base: 'https://www.directdb.co.kr/mobile/',
  ),
  InsurerEntry(
    key: InsurerKey.hyundai,
    name: '현대해상 다이렉트',
    short: '현대',
    base: 'https://direct.hi.co.kr/m/auto',
  ),
  InsurerEntry(
    key: InsurerKey.meritz,
    name: '메리츠 다이렉트',
    short: '메리츠',
    base: 'https://direct.meritzfire.com/m/',
  ),
  InsurerEntry(
    key: InsurerKey.carrot,
    name: '캐롯 퍼마일',
    short: '캐롯',
    base: 'https://www.carrot.insure/',
  ),
];

String buildInsurerUrl(
  InsurerEntry entry, {
  String? brand,
  String? model,
  int? year,
  int? age,
  String? region,
}) {
  final pairs = <String>[
    'utm_source=${Uri.encodeComponent('carnerf')}',
    if (brand != null) 'brand=${Uri.encodeComponent(brand)}',
    if (model != null) 'model=${Uri.encodeComponent(model)}',
    if (year != null) 'year=$year',
    if (age != null) 'age=$age',
    if (region != null) 'region=${Uri.encodeComponent(region)}',
  ];
  final sep = entry.base.contains('?') ? '&' : '?';
  return '${entry.base}$sep${pairs.join('&')}';
}
