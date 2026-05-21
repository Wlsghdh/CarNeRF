import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class BrandCount {
  const BrandCount({required this.brand, required this.count});
  final String brand;
  final int count;

  factory BrandCount.fromJson(Map<String, dynamic> json) => BrandCount(
        brand: json['brand'] as String,
        count: (json['count'] as num).toInt(),
      );
}

class DashboardStats {
  const DashboardStats({
    required this.totalListings,
    required this.activeListings,
    required this.soldThisWeek,
    required this.averagePrice,
    required this.brandDistribution,
  });

  final int totalListings;
  final int activeListings;
  final int soldThisWeek;
  final int averagePrice;
  final List<BrandCount> brandDistribution;
}

class TrendPoint {
  const TrendPoint({required this.month, required this.price});
  final String month;
  final int price;

  factory TrendPoint.fromJson(Map<String, dynamic> json) => TrendPoint(
        month: json['month'] as String,
        price: (json['price'] as num).toInt(),
      );
}

class StatsApi {
  StatsApi(this._dio);
  final Dio _dio;

  Future<DashboardStats> dashboard() async {
    final r = await _dio.get<Map<String, dynamic>>('/api/stats/dashboard/');
    return DashboardStats(
      totalListings: (r.data!['total_listings'] as num).toInt(),
      activeListings: (r.data!['active_listings'] as num).toInt(),
      soldThisWeek: (r.data!['sold_this_week'] as num).toInt(),
      averagePrice: (r.data!['average_price'] as num).toInt(),
      brandDistribution: (r.data!['brand_distribution'] as List)
          .cast<Map<String, dynamic>>()
          .map(BrandCount.fromJson)
          .toList(),
    );
  }

  Future<List<TrendPoint>> priceTrends({String? brand, String? model}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/stats/price-trends/',
      queryParameters: {
        'brand': ?brand,
        'model': ?model,
      },
    );
    return (r.data!['trends'] as List)
        .cast<Map<String, dynamic>>()
        .map(TrendPoint.fromJson)
        .toList();
  }
}

final statsApiProvider =
    Provider<StatsApi>((ref) => StatsApi(ref.watch(apiClientProvider)));
