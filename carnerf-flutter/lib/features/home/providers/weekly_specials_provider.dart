import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/listings_api.dart';
import '../../../core/models/listing.dart';
import '../../../core/utils/week.dart';

class SpecialListing {
  const SpecialListing({
    required this.listing,
    required this.discountRate,
    required this.originalPrice,
    required this.specialPrice,
    required this.weekLabel,
  });

  final Listing listing;
  final double discountRate;
  final int originalPrice;
  final int specialPrice;
  final String weekLabel;

  int get discountPercent => (discountRate * 100).round();
}

const _pickCount = 8;

final weeklySpecialsProvider = FutureProvider<List<SpecialListing>>((ref) async {
  final api = ref.watch(listingsApiProvider);
  final pool = await api.list(
    const ListingQuery(sort: ListingSort.newest, limit: 60),
  );
  if (pool.isEmpty) return const [];

  final wk = weekKey();
  final rand = mulberry32(hashSeed(wk));

  final arr = [...pool];
  for (var i = arr.length - 1; i > 0; i--) {
    final j = (rand() * (i + 1)).floor();
    final tmp = arr[i];
    arr[i] = arr[j];
    arr[j] = tmp;
  }

  final picked = arr.take(_pickCount).toList();

  return picked.map((l) {
    final discount = 0.10 + rand() * 0.15;
    final rate = (discount * 100).round() / 100;
    final special = l.price;
    final original = (special / (1 - rate)).round();
    return SpecialListing(
      listing: l,
      discountRate: rate,
      originalPrice: original,
      specialPrice: special,
      weekLabel: wk,
    );
  }).toList();
});
