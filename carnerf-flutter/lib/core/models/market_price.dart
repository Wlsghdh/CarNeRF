class MarketPrice {
  const MarketPrice({
    required this.internalAverage,
    this.externalAverage,
    required this.depreciationEstimate,
  });

  final int internalAverage;
  final int? externalAverage;
  final double depreciationEstimate;

  factory MarketPrice.fromJson(Map<String, dynamic> json) => MarketPrice(
        internalAverage: (json['internal_average'] as num).toInt(),
        externalAverage: (json['external_average'] as num?)?.toInt(),
        depreciationEstimate: (json['depreciation_estimate'] as num).toDouble(),
      );
}
