enum LicenseGrade { under1y, over1y, over3y }

const Map<LicenseGrade, String> licenseGradeLabel = {
  LicenseGrade.under1y: '1년미만',
  LicenseGrade.over1y: '1년이상',
  LicenseGrade.over3y: '3년이상',
};

enum DriverScope { selfOnly, couple, family, anyone }

const Map<DriverScope, String> driverScopeLabel = {
  DriverScope.selfOnly: '본인한정',
  DriverScope.couple: '부부',
  DriverScope.family: '가족',
  DriverScope.anyone: '누구나',
};

enum AgeLimit { none, age21, age26, age30, age35, age43, age48 }

const Map<AgeLimit, String> ageLimitLabel = {
  AgeLimit.none: '제한없음',
  AgeLimit.age21: '만21세',
  AgeLimit.age26: '만26세',
  AgeLimit.age30: '만30세',
  AgeLimit.age35: '만35세',
  AgeLimit.age43: '만43세',
  AgeLimit.age48: '만48세',
};

const List<int> mileageBands = [3000, 5000, 7000, 10000, 15000, 20000];
const List<int> ncdYears = [0, 1, 2, 3, 5, 7];

class InsuranceInput {
  const InsuranceInput({
    required this.priceManwon,
    this.engineCc,
    this.fuelType,
    required this.year,
    required this.age,
    required this.licenseGrade,
    required this.region,
    this.driverScope,
    this.ageLimit,
    this.noAccidentYears,
    this.annualMileageKm,
    this.hasBlackbox = false,
    this.hasAeb = false,
    this.hasLdwsLka = false,
    this.hasBsd = false,
    this.hasAcc = false,
  });

  final num priceManwon;
  final int? engineCc;
  final String? fuelType;
  final int year;
  final int age;
  final LicenseGrade licenseGrade;
  final String region;
  final DriverScope? driverScope;
  final AgeLimit? ageLimit;
  final int? noAccidentYears;
  final int? annualMileageKm;
  final bool hasBlackbox;
  final bool hasAeb;
  final bool hasLdwsLka;
  final bool hasBsd;
  final bool hasAcc;
}

class InsuranceFactors {
  const InsuranceFactors({
    required this.base,
    required this.ageFactor,
    required this.licenseFactor,
    required this.regionFactor,
    required this.evFactor,
    required this.driverScopeFactor,
    required this.ageLimitFactor,
    required this.ncdFactor,
    required this.mileageFactor,
    required this.safetyDiscount,
    required this.totalDiscountRate,
  });

  final double base;
  final double ageFactor;
  final double licenseFactor;
  final double regionFactor;
  final double evFactor;
  final double driverScopeFactor;
  final double ageLimitFactor;
  final double ncdFactor;
  final double mileageFactor;
  final double safetyDiscount;
  final double totalDiscountRate;
}

class InsuranceQuote {
  const InsuranceQuote({
    required this.annualPremium,
    required this.factors,
    required this.assumptions,
  });

  final int annualPremium;
  final InsuranceFactors factors;
  final List<String> assumptions;
}

double _ageFactor(int age) {
  if (age < 26) return 1.75;
  if (age < 30) return 1.25;
  if (age < 50) return 1.0;
  if (age < 65) return 1.05;
  return 1.3;
}

double _licenseFactor(LicenseGrade g) {
  switch (g) {
    case LicenseGrade.under1y:
      return 1.3;
    case LicenseGrade.over1y:
      return 1.1;
    case LicenseGrade.over3y:
      return 1.0;
  }
}

double _regionFactor(String region) {
  if (region == '서울') return 1.1;
  if (region == '부산' || region == '인천') return 1.05;
  return 1.0;
}

double _evFactor(String? fuel) {
  if (fuel == '전기') return 0.85;
  if (fuel == '하이브리드') return 0.95;
  return 1.0;
}

double _driverScopeFactor(DriverScope? s) {
  switch (s) {
    case DriverScope.selfOnly:
      return 0.78;
    case DriverScope.couple:
      return 0.85;
    case DriverScope.family:
      return 1.0;
    case DriverScope.anyone:
      return 1.32;
    case null:
      return 1.0;
  }
}

const Map<AgeLimit, double> _ageLimitFactors = {
  AgeLimit.none: 1.0,
  AgeLimit.age21: 1.0,
  AgeLimit.age26: 0.92,
  AgeLimit.age30: 0.86,
  AgeLimit.age35: 0.82,
  AgeLimit.age43: 0.78,
  AgeLimit.age48: 0.76,
};

int _ageLimitMinAge(AgeLimit limit) {
  switch (limit) {
    case AgeLimit.none:
      return 0;
    case AgeLimit.age21:
      return 21;
    case AgeLimit.age26:
      return 26;
    case AgeLimit.age30:
      return 30;
    case AgeLimit.age35:
      return 35;
    case AgeLimit.age43:
      return 43;
    case AgeLimit.age48:
      return 48;
  }
}

double _ageLimitFactor(AgeLimit? limit, int? driverAge) {
  if (limit == null) return 1.0;
  if (driverAge != null && driverAge < _ageLimitMinAge(limit)) return 1.0;
  return _ageLimitFactors[limit] ?? 1.0;
}

double _ncdFactor(int? years) {
  if (years == null) return 1.0;
  if (years <= 0) return 1.1;
  if (years == 1) return 1.0;
  if (years == 2) return 0.92;
  if (years == 3) return 0.83;
  if (years <= 4) return 0.83;
  if (years <= 6) return 0.72;
  return 0.63;
}

double _mileageFactor(int? km) {
  if (km == null) return 1.0;
  if (km <= 3000) return 0.78;
  if (km <= 5000) return 0.85;
  if (km <= 7000) return 0.92;
  if (km <= 10000) return 0.96;
  if (km <= 15000) return 1.0;
  return 1.06;
}

double _safetyDiscount(InsuranceInput input) {
  var sum = 0.0;
  if (input.hasBlackbox) sum += 0.03;
  if (input.hasAeb) sum += 0.04;
  if (input.hasLdwsLka) sum += 0.03;
  if (input.hasBsd) sum += 0.02;
  if (input.hasAcc) sum += 0.02;
  return sum > 0.15 ? 0.15 : sum;
}

InsuranceQuote quoteInsurance(InsuranceInput input) {
  final cc = input.engineCc ?? 1600;
  final rawBase = input.priceManwon * 0.022 + cc * 0.012;
  final base = rawBase < 40 ? 40.0 : rawBase.toDouble();

  final a = _ageFactor(input.age);
  final l = _licenseFactor(input.licenseGrade);
  final r = _regionFactor(input.region);
  final e = _evFactor(input.fuelType);
  final ds = _driverScopeFactor(input.driverScope);
  final al = _ageLimitFactor(input.ageLimit, input.age);
  final nc = _ncdFactor(input.noAccidentYears);
  final mi = _mileageFactor(input.annualMileageKm);
  final sd = _safetyDiscount(input);

  final raw = base * a * l * r * e * ds * al * nc * mi;
  final annual = (raw * (1 - sd)).round();
  final baseline = (base * a * l * r * e).round();
  final totalDiscount = baseline > 0 ? annual / baseline - 1 : 0.0;

  final assumptions = <String>[
    '만 ${input.age}세, 1종 보통 ${licenseGradeLabel[input.licenseGrade]} 경력 가정',
    '${input.region} 거주, 대인 무한 / 대물 5억 / 자손 1.5억 기본 담보 가정',
    '차량가 ${input.priceManwon.round()}만, 배기량 ${cc}cc 기준',
  ];
  if (input.fuelType == '전기' || input.fuelType == '하이브리드') {
    assumptions.add('${input.fuelType} 차량 특약 할인 반영');
  }
  assumptions.add('할인할증 등급 11Z(평균) 가정 — 사고 이력 미반영');
  if (input.driverScope != null) {
    assumptions.add('운전자 범위: ${driverScopeLabel[input.driverScope]}');
  }
  if (input.ageLimit != null && input.ageLimit != AgeLimit.none) {
    assumptions.add('연령 한정: ${ageLimitLabel[input.ageLimit]}');
  }
  if (input.noAccidentYears != null) {
    assumptions.add('무사고 ${input.noAccidentYears}년 (NCD 반영)');
  }
  if (input.annualMileageKm != null) {
    assumptions.add('연 주행 약 ${input.annualMileageKm}km 가정');
  }
  final anySafety = input.hasBlackbox ||
      input.hasAeb ||
      input.hasLdwsLka ||
      input.hasBsd ||
      input.hasAcc;
  if (anySafety) {
    assumptions.add('안전옵션 할인 −${(sd * 100).round()}% 반영');
  }

  return InsuranceQuote(
    annualPremium: annual < 20 ? 20 : annual,
    factors: InsuranceFactors(
      base: (base * 10).round() / 10,
      ageFactor: a,
      licenseFactor: l,
      regionFactor: r,
      evFactor: e,
      driverScopeFactor: ds,
      ageLimitFactor: al,
      ncdFactor: nc,
      mileageFactor: mi,
      safetyDiscount: sd,
      totalDiscountRate: totalDiscount.toDouble(),
    ),
    assumptions: assumptions,
  );
}
