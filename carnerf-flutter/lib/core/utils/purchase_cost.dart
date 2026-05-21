const List<String> regions = [
  '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산',
  '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
];

const Map<String, double> _bondRate = {
  '서울': 0.12, '경기': 0.12, '인천': 0.12,
  '부산': 0.05, '대구': 0.05, '광주': 0.05, '대전': 0.05, '울산': 0.05,
  '세종': 0.05, '강원': 0.05, '충북': 0.05, '충남': 0.05,
  '전북': 0.05, '전남': 0.05, '경북': 0.05, '경남': 0.05, '제주': 0.05,
};

const double _bondDiscountRatio = 0.115;
const int bondDiscountPercent = 12;
const num _registrationFixed = 8;

String normalizeRegion(String? input) {
  if (input == null) return '서울';
  final s = input.trim();
  for (final r in regions) {
    if (s == r || s.startsWith(r)) return r;
  }
  return '서울';
}

String? normalizeFuel(String? input) {
  if (input == null) return null;
  final s = input.trim();
  final lower = s.toLowerCase();
  if (s.contains('전기')) return '전기';
  if (s.contains('하이브리드') || lower.contains('hybrid')) return '하이브리드';
  if (s.contains('LPG') || lower.contains('lpg')) return 'LPG';
  if (s.contains('디젤')) return '디젤';
  if (s.contains('가솔린') || s.contains('휘발유')) return '가솔린';
  return null;
}

class PurchaseCostInput {
  const PurchaseCostInput({
    required this.priceManwon,
    this.engineCc,
    this.fuelType,
    required this.year,
    required this.region,
    required this.discountBond,
  });

  final num priceManwon;
  final int? engineCc;
  final String? fuelType;
  final int year;
  final String region;
  final bool discountBond;
}

class PurchaseCostBreakdown {
  const PurchaseCostBreakdown({
    required this.base,
    required this.acquisitionTax,
    required this.bondFace,
    required this.bondDiscount,
    required this.registrationFee,
    required this.subtotalTaxes,
    required this.totalPurchase,
  });

  final num base;
  final num acquisitionTax;
  final num bondFace;
  final num bondDiscount;
  final num registrationFee;
  final num subtotalTaxes;
  final num totalPurchase;
}

double _acquisitionTaxRate({int? engineCc, String? fuelType}) {
  if (engineCc != null && engineCc > 0 && engineCc <= 1000) return 0.04;
  if (fuelType == '전기') return 0.04;
  return 0.07;
}

num _round1(num n) => (n * 10).round() / 10;

PurchaseCostBreakdown computePurchaseCost(PurchaseCostInput input) {
  final base = input.priceManwon < 0 ? 0 : input.priceManwon;
  final acqRate = _acquisitionTaxRate(engineCc: input.engineCc, fuelType: input.fuelType);
  final acquisitionTax = _round1(base * acqRate);
  final bondRate = _bondRate[input.region] ?? 0.05;
  final bondFace = _round1(base * bondRate);
  final bondDiscount = _round1(bondFace * _bondDiscountRatio);
  final registrationFee = _registrationFixed;
  final bondCost = input.discountBond ? bondDiscount : bondFace;
  final subtotalTaxes = _round1(acquisitionTax + bondCost + registrationFee);
  final totalPurchase = _round1(base + subtotalTaxes);
  return PurchaseCostBreakdown(
    base: base,
    acquisitionTax: acquisitionTax,
    bondFace: bondFace,
    bondDiscount: bondDiscount,
    registrationFee: registrationFee,
    subtotalTaxes: subtotalTaxes,
    totalPurchase: totalPurchase,
  );
}

String acquisitionTaxLabel({int? engineCc, String? fuelType}) {
  if (engineCc != null && engineCc > 0 && engineCc <= 1000) return '경차 4%';
  if (fuelType == '전기') return '전기 4%';
  return '7%';
}

String bondRateLabel(String region) {
  final pct = (((_bondRate[region] ?? 0.05) * 100).round());
  return '$region $pct%';
}
