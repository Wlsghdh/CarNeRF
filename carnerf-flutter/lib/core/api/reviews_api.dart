import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/user_review.dart';
import 'api_client.dart';

class ReviewsPage {
  const ReviewsPage({required this.items, required this.total});
  final List<UserReview> items;
  final int total;
}

class ModelReviewSummary {
  const ModelReviewSummary({
    required this.averageRating,
    required this.totalReviews,
    required this.summary,
  });

  final double averageRating;
  final int totalReviews;
  final String summary;

  factory ModelReviewSummary.fromJson(Map<String, dynamic> json) =>
      ModelReviewSummary(
        averageRating: (json['average_rating'] as num).toDouble(),
        totalReviews: (json['total_reviews'] as num).toInt(),
        summary: json['summary'] as String? ?? '',
      );
}

class ReviewsApi {
  ReviewsApi(this._dio);
  final Dio _dio;

  Future<ReviewsPage> forVehicle(int vehicleId, {int page = 1, int limit = 10}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/reviews/vehicle/$vehicleId/',
      queryParameters: {'page': page, 'limit': limit},
    );
    final items = (r.data!['items'] as List? ?? [])
        .cast<Map<String, dynamic>>()
        .map(UserReview.fromJson)
        .toList();
    return ReviewsPage(items: items, total: (r.data!['total'] as num).toInt());
  }

  Future<UserReview> create({
    required int vehicleId,
    required int rating,
    required String content,
    required ReviewType reviewType,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/reviews/',
      data: {
        'vehicle_id': vehicleId,
        'rating': rating,
        'content': content,
        'review_type': reviewType == ReviewType.seller ? 'seller' : 'buyer',
      },
    );
    return UserReview.fromJson(r.data!);
  }

  Future<ModelReviewSummary> modelSummary(String brand, String model) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/reviews/model-summary/$brand/$model/',
    );
    return ModelReviewSummary.fromJson(r.data!);
  }
}

final reviewsApiProvider =
    Provider<ReviewsApi>((ref) => ReviewsApi(ref.watch(apiClientProvider)));
