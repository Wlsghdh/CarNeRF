import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/price_estimate.dart';
import 'api_client.dart';

class PricePredictBody {
  const PricePredictBody({
    required this.brand,
    required this.model,
    required this.year,
    required this.mileage,
    required this.fuelType,
    required this.transmission,
    this.engineCc,
    this.region,
    this.accidentCount,
    this.defectScore,
  });

  final String brand;
  final String model;
  final int year;
  final int mileage;
  final String fuelType;
  final String transmission;
  final int? engineCc;
  final String? region;
  final int? accidentCount;
  final double? defectScore;

  Map<String, dynamic> toJson() => {
        'brand': brand,
        'model': model,
        'year': year,
        'mileage': mileage,
        'fuel_type': fuelType,
        'transmission': transmission,
        if (engineCc != null) 'engine_cc': engineCc,
        if (region != null) 'region': region,
        if (accidentCount != null) 'accident_count': accidentCount,
        if (defectScore != null) 'defect_score': defectScore,
      };
}

class PredictApi {
  PredictApi(this._dio);
  final Dio _dio;

  Future<PriceEstimate> price(PricePredictBody body) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/predict/price/',
      data: body.toJson(),
    );
    return PriceEstimate.fromJson(r.data!);
  }

  Future<PriceEstimate> byVehicle(int id) async {
    final r = await _dio.get<Map<String, dynamic>>('/api/predict/vehicle/$id/');
    return PriceEstimate.fromJson(r.data!);
  }
}

final predictApiProvider =
    Provider<PredictApi>((ref) => PredictApi(ref.watch(apiClientProvider)));
