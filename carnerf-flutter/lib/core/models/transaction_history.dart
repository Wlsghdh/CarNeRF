enum TransactionSource { carnerf, external }

TransactionSource _sourceFromJson(String? raw) =>
    raw == 'external' ? TransactionSource.external : TransactionSource.carnerf;

class TransactionHistory {
  const TransactionHistory({
    required this.id,
    required this.vehicleId,
    required this.transactionDate,
    required this.price,
    required this.mileageAtSale,
    required this.source,
    this.buyerRegion,
    this.sellerRegion,
  });

  final int id;
  final int vehicleId;
  final DateTime transactionDate;
  final int price;
  final int mileageAtSale;
  final TransactionSource source;
  final String? buyerRegion;
  final String? sellerRegion;

  factory TransactionHistory.fromJson(Map<String, dynamic> json) =>
      TransactionHistory(
        id: (json['id'] as num).toInt(),
        vehicleId: (json['vehicle_id'] as num).toInt(),
        transactionDate: DateTime.parse(json['transaction_date'] as String),
        price: (json['price'] as num).toInt(),
        mileageAtSale: (json['mileage_at_sale'] as num).toInt(),
        source: _sourceFromJson(json['source'] as String?),
        buyerRegion: json['buyer_region'] as String?,
        sellerRegion: json['seller_region'] as String?,
      );
}
