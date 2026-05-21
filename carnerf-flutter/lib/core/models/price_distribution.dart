class TransactionPoint {
  const TransactionPoint({
    required this.date,
    required this.price,
    required this.mileage,
    required this.source,
  });

  final DateTime date;
  final int price;
  final int mileage;
  final String source;

  factory TransactionPoint.fromJson(Map<String, dynamic> json) =>
      TransactionPoint(
        date: DateTime.parse(json['date'] as String),
        price: (json['price'] as num).toInt(),
        mileage: (json['mileage'] as num).toInt(),
        source: json['source'] as String? ?? '',
      );
}

class ListingPricePoint {
  const ListingPricePoint({required this.date, required this.price});

  final DateTime date;
  final int price;

  factory ListingPricePoint.fromJson(Map<String, dynamic> json) =>
      ListingPricePoint(
        date: DateTime.parse(json['date'] as String),
        price: (json['price'] as num).toInt(),
      );
}

class PriceStats {
  const PriceStats({
    required this.min,
    required this.max,
    required this.avg,
    required this.p25,
    required this.p50,
    required this.p75,
    required this.sampleSize,
  });

  final int min;
  final int max;
  final double avg;
  final int p25;
  final int p50;
  final int p75;
  final int sampleSize;

  factory PriceStats.fromJson(Map<String, dynamic> json) => PriceStats(
        min: (json['min'] as num).toInt(),
        max: (json['max'] as num).toInt(),
        avg: (json['avg'] as num).toDouble(),
        p25: (json['p25'] as num).toInt(),
        p50: (json['p50'] as num).toInt(),
        p75: (json['p75'] as num).toInt(),
        sampleSize: (json['sample_size'] as num).toInt(),
      );
}

class PriceDistribution {
  const PriceDistribution({
    required this.transactions,
    required this.listings,
    this.stats,
    this.currentPrice,
    required this.range,
  });

  final List<TransactionPoint> transactions;
  final List<ListingPricePoint> listings;
  final PriceStats? stats;
  final int? currentPrice;
  final String range;

  factory PriceDistribution.fromJson(Map<String, dynamic> json) =>
      PriceDistribution(
        transactions: (json['transactions'] as List? ?? [])
            .cast<Map<String, dynamic>>()
            .map(TransactionPoint.fromJson)
            .toList(),
        listings: (json['listings'] as List? ?? [])
            .cast<Map<String, dynamic>>()
            .map(ListingPricePoint.fromJson)
            .toList(),
        stats: json['stats'] is Map<String, dynamic>
            ? PriceStats.fromJson(json['stats'] as Map<String, dynamic>)
            : null,
        currentPrice: (json['current_price'] as num?)?.toInt(),
        range: json['range'] as String? ?? '',
      );
}
