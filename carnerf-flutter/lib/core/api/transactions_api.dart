import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/transaction_history.dart';
import 'api_client.dart';

class MonthlyPricePoint {
  const MonthlyPricePoint({required this.month, required this.price});
  final String month;
  final int price;

  factory MonthlyPricePoint.fromJson(Map<String, dynamic> json) =>
      MonthlyPricePoint(
        month: json['month'] as String,
        price: (json['price'] as num).toInt(),
      );
}

class TransactionsApi {
  TransactionsApi(this._dio);
  final Dio _dio;

  Future<List<TransactionHistory>> forVehicle(int id) async {
    final r = await _dio.get<List<dynamic>>('/api/transactions/vehicle/$id/');
    return (r.data ?? const [])
        .cast<Map<String, dynamic>>()
        .map(TransactionHistory.fromJson)
        .toList();
  }

  Future<List<MonthlyPricePoint>> marketPrice(int id) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/transactions/market-price/$id/',
    );
    final monthly = (r.data!['monthly'] as List? ?? [])
        .cast<Map<String, dynamic>>()
        .map(MonthlyPricePoint.fromJson)
        .toList();
    return monthly;
  }
}

final transactionsApiProvider = Provider<TransactionsApi>(
  (ref) => TransactionsApi(ref.watch(apiClientProvider)),
);
