import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/ai_summary_api.dart';
import '../../../core/api/defect_api.dart';
import '../../../core/api/listings_api.dart';
import '../../../core/api/market_api.dart';
import '../../../core/api/predict_api.dart';
import '../../../core/api/reviews_api.dart';
import '../../../core/api/wishlist_api.dart';
import '../../../core/models/defect_report.dart';
import '../../../core/models/listing.dart';
import '../../../core/models/market_price.dart';
import '../../../core/models/price_estimate.dart';
import '../../../core/models/vehicle_summary.dart';

final listingDetailProvider =
    FutureProvider.family<Listing, int>((ref, listingId) async {
  return ref.watch(listingsApiProvider).get(listingId);
});

final vehicleSummaryProvider =
    FutureProvider.family<VehicleSummary, int>((ref, vehicleId) async {
  return ref.watch(aiSummaryApiProvider).vehicleSummary(vehicleId);
});

final defectReportProvider =
    FutureProvider.family<DefectReport, int>((ref, vehicleId) async {
  return ref.watch(defectApiProvider).byVehicle(vehicleId);
});

final marketPriceProvider =
    FutureProvider.family<MarketPrice, int>((ref, vehicleId) async {
  return ref.watch(marketApiProvider).price(vehicleId);
});

final priceEstimateProvider =
    FutureProvider.family<PriceEstimate, int>((ref, vehicleId) async {
  return ref.watch(predictApiProvider).byVehicle(vehicleId);
});

final vehicleReviewsProvider =
    FutureProvider.family<ReviewsPage, int>((ref, vehicleId) async {
  return ref.watch(reviewsApiProvider).forVehicle(vehicleId, limit: 5);
});

final wishlistCheckProvider =
    FutureProvider.family<bool, int>((ref, vehicleId) async {
  return ref.watch(wishlistApiProvider).check(vehicleId);
});

Future<void> toggleWishlist(WidgetRef ref, int vehicleId) async {
  await ref.read(wishlistApiProvider).toggle(vehicleId);
  ref.invalidate(wishlistCheckProvider(vehicleId));
}
