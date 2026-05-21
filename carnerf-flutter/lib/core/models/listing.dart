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

  factory Listing.fromJson(Map<String, dynamic> json) {
    final vehicleMap = json['vehicle'] is Map<String, dynamic>
        ? json['vehicle'] as Map<String, dynamic>
        : null;
    final sellerMap = json['seller'] is Map<String, dynamic>
        ? json['seller'] as Map<String, dynamic>
        : null;

    int? asInt(dynamic v) => v is num ? v.toInt() : null;

    final vehicleId = asInt(json['vehicle_id']) ??
        asInt(vehicleMap?['id']) ??
        0;
    final sellerId =
        asInt(json['seller_id']) ?? asInt(sellerMap?['id']) ?? 0;

    return Listing(
      id: (json['id'] as num).toInt(),
      vehicleId: vehicleId,
      sellerId: sellerId,
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      price: asInt(json['price']) ?? 0,
      isNegotiable: json['is_negotiable'] as bool? ?? false,
      status: _listingStatusFromJson(json['status'] as String?),
      viewCount: asInt(json['view_count']) ?? 0,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
          DateTime.fromMillisecondsSinceEpoch(0),
      vehicle: vehicleMap != null ? Vehicle.fromJson(vehicleMap) : null,
      seller: sellerMap != null ? User.fromJson(sellerMap) : null,
    );
  }
}
