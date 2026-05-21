class WarrantyTerm {
  const WarrantyTerm({required this.years, required this.km});
  final int years;
  final int km;
}

class WarrantyTerms {
  const WarrantyTerms({
    required this.general,
    required this.powertrain,
    this.rust,
  });

  final WarrantyTerm general;
  final WarrantyTerm powertrain;
  final WarrantyTerm? rust;
}

const int kUnlimitedKm = 999999;

const Map<String, WarrantyTerms> warrantyByBrand = {
  '현대': WarrantyTerms(
    general: WarrantyTerm(years: 3, km: 60000),
    powertrain: WarrantyTerm(years: 5, km: 100000),
    rust: WarrantyTerm(years: 5, km: kUnlimitedKm),
  ),
  '기아': WarrantyTerms(
    general: WarrantyTerm(years: 3, km: 60000),
    powertrain: WarrantyTerm(years: 5, km: 100000),
    rust: WarrantyTerm(years: 5, km: kUnlimitedKm),
  ),
  '제네시스': WarrantyTerms(
    general: WarrantyTerm(years: 5, km: 100000),
    powertrain: WarrantyTerm(years: 5, km: 100000),
    rust: WarrantyTerm(years: 7, km: kUnlimitedKm),
  ),
  '쉐보레': WarrantyTerms(
    general: WarrantyTerm(years: 5, km: 100000),
    powertrain: WarrantyTerm(years: 5, km: 100000),
  ),
  'BMW': WarrantyTerms(
    general: WarrantyTerm(years: 3, km: kUnlimitedKm),
    powertrain: WarrantyTerm(years: 3, km: kUnlimitedKm),
  ),
  '벤츠': WarrantyTerms(
    general: WarrantyTerm(years: 3, km: kUnlimitedKm),
    powertrain: WarrantyTerm(years: 3, km: kUnlimitedKm),
  ),
  '아우디': WarrantyTerms(
    general: WarrantyTerm(years: 3, km: kUnlimitedKm),
    powertrain: WarrantyTerm(years: 3, km: kUnlimitedKm),
  ),
  '렉서스': WarrantyTerms(
    general: WarrantyTerm(years: 4, km: 100000),
    powertrain: WarrantyTerm(years: 6, km: 120000),
  ),
  '포르쉐': WarrantyTerms(
    general: WarrantyTerm(years: 4, km: kUnlimitedKm),
    powertrain: WarrantyTerm(years: 4, km: kUnlimitedKm),
  ),
};

class InspectionWarranty {
  const InspectionWarranty({required this.days, required this.km});
  final int days;
  final int km;
}

const InspectionWarranty inspectionWarranty = InspectionWarranty(days: 30, km: 2000);
