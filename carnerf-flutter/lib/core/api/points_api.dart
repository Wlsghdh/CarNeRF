import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/point_transaction.dart';
import 'api_client.dart';

enum PointUsageType { aiUsage, premiumListing }

String _usageToParam(PointUsageType t) =>
    t == PointUsageType.premiumListing ? 'premium_listing' : 'ai_usage';

class PointsHistoryPage {
  const PointsHistoryPage({required this.items, required this.total});
  final List<PointTransaction> items;
  final int total;
}

class PointsApi {
  PointsApi(this._dio);
  final Dio _dio;

  Future<int> balance() async {
    final r = await _dio.get<Map<String, dynamic>>('/api/points/balance/');
    return (r.data!['balance'] as num).toInt();
  }

  Future<PointsHistoryPage> history({int page = 1}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/points/history/',
      queryParameters: {'page': page},
    );
    final items = (r.data!['items'] as List? ?? [])
        .cast<Map<String, dynamic>>()
        .map(PointTransaction.fromJson)
        .toList();
    return PointsHistoryPage(
      items: items,
      total: (r.data!['total'] as num).toInt(),
    );
  }

  Future<PointTransaction> charge(int amount) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/points/charge/',
      data: {'amount': amount},
    );
    return PointTransaction.fromJson(r.data!);
  }

  Future<PointTransaction> use({
    required int amount,
    required PointUsageType usageType,
    required String description,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/points/use/',
      data: {
        'amount': amount,
        'usage_type': _usageToParam(usageType),
        'description': description,
      },
    );
    return PointTransaction.fromJson(r.data!);
  }
}

final pointsApiProvider =
    Provider<PointsApi>((ref) => PointsApi(ref.watch(apiClientProvider)));
