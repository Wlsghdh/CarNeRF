import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/auth_api.dart';
import '../../../core/api/points_api.dart';
import '../../../core/api/wishlist_api.dart';
import '../../../core/models/listing.dart';

final pointsBalanceProvider = FutureProvider<int>((ref) async {
  return ref.watch(pointsApiProvider).balance();
});

final myListingsProvider = FutureProvider<List<Listing>>((ref) async {
  return ref.watch(authApiProvider).myListings();
});

final myWishlistProvider = FutureProvider<List<WishlistEntry>>((ref) async {
  return ref.watch(wishlistApiProvider).list();
});
