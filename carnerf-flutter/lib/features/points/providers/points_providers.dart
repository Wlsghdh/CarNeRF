import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/points_api.dart';

final pointsBalanceProvider = FutureProvider.autoDispose<int>((ref) async {
  return ref.watch(pointsApiProvider).balance();
});

final pointsHistoryProvider =
    FutureProvider.autoDispose<PointsHistoryPage>((ref) async {
  return ref.watch(pointsApiProvider).history();
});
