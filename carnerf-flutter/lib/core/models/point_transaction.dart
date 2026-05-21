enum PointTxType { charge, aiUsage, premiumListing, refund }

PointTxType _typeFromJson(String? raw) {
  switch (raw) {
    case 'ai_usage':
      return PointTxType.aiUsage;
    case 'premium_listing':
      return PointTxType.premiumListing;
    case 'refund':
      return PointTxType.refund;
    default:
      return PointTxType.charge;
  }
}

class PointTransaction {
  const PointTransaction({
    required this.id,
    required this.userId,
    required this.amount,
    required this.balanceAfter,
    required this.transactionType,
    required this.description,
    required this.createdAt,
  });

  final int id;
  final int userId;
  final int amount;
  final int balanceAfter;
  final PointTxType transactionType;
  final String description;
  final DateTime createdAt;

  factory PointTransaction.fromJson(Map<String, dynamic> json) =>
      PointTransaction(
        id: (json['id'] as num).toInt(),
        userId: (json['user_id'] as num).toInt(),
        amount: (json['amount'] as num).toInt(),
        balanceAfter: (json['balance_after'] as num).toInt(),
        transactionType: _typeFromJson(json['transaction_type'] as String?),
        description: json['description'] as String? ?? '',
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
