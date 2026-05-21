import 'user.dart';
import 'vehicle.dart';

enum ListingStatus { active, reserved, sold }

ListingStatus _listingStatusFromJson(String? raw) {
  switch (raw) {
    case 'reserved':
      return ListingStatus.reserved;
    case 'sold':
      return ListingStatus.sold;
    default:
      return ListingStatus.active;
  }
}

class Listing {
  const Listing({
    required this.id,
    required this.vehicleId,
    required this.sellerId,
    required this.title,
    this.description,
    required this.price,
    required this.isNegotiable,
    required this.status,
    required this.viewCount,
    required this.createdAt,
    this.vehicle,
    this.seller,
  });

  final int id;
  final int vehicleId;
  final int sellerId;
  final String title;
  final String? description;
  final int price;
  final bool isNegotiable;
  final ListingStatus status;
  final int viewCount;
  final DateTime createdAt;
  final Vehicle? vehicle;
  final User? seller;

  factory Listing.fromJson(Map<String, dynamic> json) => Listing(
        id: json['id'] as int,
        vehicleId: (json['vehicle_id'] as num).toInt(),
        sellerId: (json['seller_id'] as num).toInt(),
        title: json['title'] as String,
        description: json['description'] as String?,
        price: (json['price'] as num).toInt(),
        isNegotiable: json['is_negotiable'] as bool? ?? false,
        status: _listingStatusFromJson(json['status'] as String?),
        viewCount: (json['view_count'] as num?)?.toInt() ?? 0,
        createdAt: DateTime.parse(json['created_at'] as String),
        vehicle: json['vehicle'] is Map<String, dynamic>
            ? Vehicle.fromJson(json['vehicle'] as Map<String, dynamic>)
            : null,
        seller: json['seller'] is Map<String, dynamic>
            ? User.fromJson(json['seller'] as Map<String, dynamic>)
            : null,
      );
}
