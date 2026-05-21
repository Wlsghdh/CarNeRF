import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/market_price.dart';
import '../models/price_distribution.dart';
import 'api_client.dart';

class MarketAverage {
  const MarketAverage({required this.averagePrice, required this.sampleSize});
  final int averagePrice;
  final int sampleSize;
}

class MarketApi {
  MarketApi(this._dio);
  final Dio _dio;

  Future<MarketPrice> price(int vehicleId) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/market/price/$vehicleId/');
    return MarketPrice.fromJson(r.data!);
  }

  Future<MarketAverage> average({
    required String brand,
    required String model,
    int? yearMin,
    int? yearMax,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/market/average/',
      queryParameters: {
        'brand': brand,
        'model': model,
        'year_min': ?yearMin,
        'year_max': ?yearMax,
      },
    );
    return MarketAverage(
      averagePrice: (r.data!['average_price'] as num).toInt(),
      sampleSize: (r.data!['sample_size'] as num).toInt(),
    );
  }

  Future<PriceDistribution> distribution(int vehicleId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/market/distribution/$vehicleId',
    );
    return PriceDistribution.fromJson(r.data!);
  }
}

final marketApiProvider =
    Provider<MarketApi>((ref) => MarketApi(ref.watch(apiClientProvider)));
