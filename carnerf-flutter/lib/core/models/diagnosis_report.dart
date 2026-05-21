class DiagnosisReport {
  const DiagnosisReport({
    required this.id,
    required this.vehicleId,
    required this.overallScore,
    required this.exteriorScore,
    required this.interiorScore,
    required this.engineScore,
    required this.accidentHistory,
    required this.estimatedPriceLow,
    required this.estimatedPriceHigh,
    required this.reportSummary,
  });

  final int id;
  final int vehicleId;
  final double overallScore;
  final double exteriorScore;
  final double interiorScore;
  final double engineScore;
  final int accidentHistory;
  final int estimatedPriceLow;
  final int estimatedPriceHigh;
  final String reportSummary;

  factory DiagnosisReport.fromJson(Map<String, dynamic> json) => DiagnosisReport(
        id: (json['id'] as num).toInt(),
        vehicleId: (json['vehicle_id'] as num).toInt(),
        overallScore: (json['overall_score'] as num).toDouble(),
        exteriorScore: (json['exterior_score'] as num).toDouble(),
        interiorScore: (json['interior_score'] as num).toDouble(),
        engineScore: (json['engine_score'] as num).toDouble(),
        accidentHistory: (json['accident_history'] as num).toInt(),
        estimatedPriceLow: (json['estimated_price_low'] as num).toInt(),
        estimatedPriceHigh: (json['estimated_price_high'] as num).toInt(),
        reportSummary: json['report_summary'] as String? ?? '',
      );
}
