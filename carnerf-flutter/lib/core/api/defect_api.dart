import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/defect_report.dart';
import 'api_client.dart';

class DefectApi {
  DefectApi(this._dio);
  final Dio _dio;

  Future<DefectReport> byVehicle(int vehicleId) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/defect/vehicles/$vehicleId/');
    return DefectReport.fromJson(r.data!);
  }
}

final defectApiProvider =
    Provider<DefectApi>((ref) => DefectApi(ref.watch(apiClientProvider)));
