import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/vehicle_summary.dart';
import 'api_client.dart';

class AiSummaryApi {
  AiSummaryApi(this._dio);
  final Dio _dio;

  Future<VehicleSummary> vehicleSummary(int vehicleId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/ai/vehicle-summary/$vehicleId/',
    );
    return VehicleSummary.fromJson(r.data!);
  }
}

final aiSummaryApiProvider =
    Provider<AiSummaryApi>((ref) => AiSummaryApi(ref.watch(apiClientProvider)));
