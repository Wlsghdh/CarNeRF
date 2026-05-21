import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class SellerStatus {
  const SellerStatus({required this.isVerified, required this.pending});
  final bool isVerified;
  final bool pending;
}

class SellerApi {
  SellerApi(this._dio);
  final Dio _dio;

  Future<SellerStatus> status() async {
    final r = await _dio.get<Map<String, dynamic>>('/api/seller/status/');
    return SellerStatus(
      isVerified: r.data!['is_verified'] as bool? ?? false,
      pending: r.data!['pending'] as bool? ?? false,
    );
  }

  Future<void> upgrade({
    required String name,
    required String phone,
    required String vehicleRegistration,
    required String region,
  }) async {
    await _dio.post<dynamic>(
      '/api/seller/upgrade/',
      data: {
        'name': name,
        'phone': phone,
        'vehicle_registration': vehicleRegistration,
        'region': region,
      },
    );
  }
}

final sellerApiProvider =
    Provider<SellerApi>((ref) => SellerApi(ref.watch(apiClientProvider)));
