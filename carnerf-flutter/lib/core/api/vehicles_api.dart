import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/diagnosis_report.dart';
import '../models/vehicle.dart';
import 'api_client.dart';

class VehiclesApi {
  VehiclesApi(this._dio);
  final Dio _dio;

  Future<List<Vehicle>> list({
    String? brand,
    String? fuelType,
    int? yearMin,
    int? yearMax,
  }) async {
    final r = await _dio.get<List<dynamic>>(
      '/api/vehicles/',
      queryParameters: {
        'brand': ?brand,
        'fuel_type': ?fuelType,
        'year_min': ?yearMin,
        'year_max': ?yearMax,
      },
    );
    return (r.data ?? const [])
        .cast<Map<String, dynamic>>()
        .map(Vehicle.fromJson)
        .toList();
  }

  Future<Vehicle> get(int id) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/vehicles/$id/');
    return Vehicle.fromJson(r.data!);
  }

  Future<DiagnosisReport> diagnosis(int id) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/vehicles/$id/diagnosis/');
    return DiagnosisReport.fromJson(r.data!);
  }
}

final vehiclesApiProvider =
    Provider<VehiclesApi>((ref) => VehiclesApi(ref.watch(apiClientProvider)));
