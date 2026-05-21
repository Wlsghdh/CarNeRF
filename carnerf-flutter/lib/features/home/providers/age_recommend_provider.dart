import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/listings_api.dart';
import '../../../core/models/listing.dart';

enum AgeGroup { twenties, thirties, forties, fifties, sixtiesPlus }

extension AgeGroupX on AgeGroup {
  String get label {
    switch (this) {
      case AgeGroup.twenties:
        return '20대';
      case AgeGroup.thirties:
        return '30대';
      case AgeGroup.forties:
        return '40대';
      case AgeGroup.fifties:
        return '50대';
      case AgeGroup.sixtiesPlus:
        return '60대+';
    }
  }
}

ListingQuery _filterFor(AgeGroup g) {
  switch (g) {
    case AgeGroup.twenties:
      return const ListingQuery(priceMax: 2000, sort: ListingSort.newest, limit: 10);
    case AgeGroup.thirties:
      return const ListingQuery(
        priceMin: 2000,
        priceMax: 4000,
        fuelType: '하이브리드',
        limit: 10,
      );
    case AgeGroup.forties:
      return const ListingQuery(
        priceMin: 3000,
        priceMax: 6000,
        brand: '제네시스',
        limit: 10,
      );
    case AgeGroup.fifties:
      return const ListingQuery(priceMin: 4000, fuelType: '가솔린', limit: 10);
    case AgeGroup.sixtiesPlus:
      return const ListingQuery(priceMax: 3000, fuelType: '가솔린', limit: 10);
  }
}

final ageRecommendProvider =
    FutureProvider.family<List<Listing>, AgeGroup>((ref, group) async {
  final api = ref.watch(listingsApiProvider);
  return api.list(_filterFor(group));
});
