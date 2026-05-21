import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class WishlistEntry {
  const WishlistEntry({
    required this.userId,
    required this.vehicleId,
    required this.createdAt,
  });
  final int userId;
  final int vehicleId;
  final DateTime createdAt;

  factory WishlistEntry.fromJson(Map<String, dynamic> json) => WishlistEntry(
        userId: (json['user_id'] as num).toInt(),
        vehicleId: (json['vehicle_id'] as num).toInt(),
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

class WishlistApi {
  WishlistApi(this._dio);
  final Dio _dio;

  Future<List<WishlistEntry>> list() async {
    final r = await _dio.get<List<dynamic>>('/api/wishlist/');
    return (r.data ?? const [])
        .cast<Map<String, dynamic>>()
        .map(WishlistEntry.fromJson)
        .toList();
  }

  Future<bool> toggle(int vehicleId) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/wishlist/toggle/$vehicleId/',
    );
    return r.data!['wishlisted'] as bool;
  }

  Future<bool> check(int vehicleId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/wishlist/check/$vehicleId/',
    );
    return r.data!['wishlisted'] as bool;
  }

  Future<int> count(int vehicleId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/wishlist/count/$vehicleId/',
    );
    return (r.data!['count'] as num).toInt();
  }
}

final wishlistApiProvider =
    Provider<WishlistApi>((ref) => WishlistApi(ref.watch(apiClientProvider)));
