class DepreciationPoint {
  const DepreciationPoint({required this.year, required this.price});
  final int year;
  final int price;

  factory DepreciationPoint.fromJson(Map<String, dynamic> json) =>
      DepreciationPoint(
        year: (json['year'] as num).toInt(),
        price: (json['price'] as num).toInt(),
      );
}

class PriceEstimate {
  const PriceEstimate({
    required this.predictedPrice,
    required this.priceRangeLow,
    required this.priceRangeHigh,
    required this.confidence,
    required this.depreciationCurve,
  });

  final int predictedPrice;
  final int priceRangeLow;
  final int priceRangeHigh;
  final double confidence;
  final List<DepreciationPoint> depreciationCurve;

  factory PriceEstimate.fromJson(Map<String, dynamic> json) => PriceEstimate(
        predictedPrice: (json['predicted_price'] as num).toInt(),
        priceRangeLow: (json['price_range_low'] as num).toInt(),
        priceRangeHigh: (json['price_range_high'] as num).toInt(),
        confidence: (json['confidence'] as num).toDouble(),
        depreciationCurve: (json['depreciation_curve'] as List? ?? [])
            .cast<Map<String, dynamic>>()
            .map(DepreciationPoint.fromJson)
            .toList(),
      );
}
