enum ReviewType { buyer, seller }

ReviewType _reviewTypeFromJson(String? raw) =>
    raw == 'seller' ? ReviewType.seller : ReviewType.buyer;

class UserReview {
  const UserReview({
    required this.id,
    required this.vehicleId,
    required this.authorId,
    required this.rating,
    required this.content,
    required this.reviewType,
    required this.createdAt,
  });

  final int id;
  final int vehicleId;
  final int authorId;
  final int rating;
  final String content;
  final ReviewType reviewType;
  final DateTime createdAt;

  factory UserReview.fromJson(Map<String, dynamic> json) => UserReview(
        id: (json['id'] as num).toInt(),
        vehicleId: (json['vehicle_id'] as num).toInt(),
        authorId: (json['author_id'] as num).toInt(),
        rating: (json['rating'] as num).toInt(),
        content: json['content'] as String? ?? '',
        reviewType: _reviewTypeFromJson(json['review_type'] as String?),
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
