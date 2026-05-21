import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/listings_api.dart';
import '../../../core/api/search_api.dart';
import '../../../core/models/listing.dart';

const int kListingsPageSize = 20;

class ListingsState {
  const ListingsState({
    this.filters = const ListingQuery(),
    this.sort = ListingSort.newest,
    this.search = '',
    this.items = const [],
    this.page = 1,
    this.hasMore = true,
    this.loading = false,
    this.loadingMore = false,
    this.error,
    this.aiMode = false,
    this.aiPending = false,
    this.aiResult,
  });

  final ListingQuery filters;
  final ListingSort sort;
  final String search;
  final List<Listing> items;
  final int page;
  final bool hasMore;
  final bool loading;
  final bool loadingMore;
  final String? error;
  final bool aiMode;
  final bool aiPending;
  final AiRecommendOutcome? aiResult;

  ListingsState copyWith({
    ListingQuery? filters,
    ListingSort? sort,
    String? search,
    List<Listing>? items,
    int? page,
    bool? hasMore,
    bool? loading,
    bool? loadingMore,
    Object? error = _sentinel,
    bool? aiMode,
    bool? aiPending,
    Object? aiResult = _sentinel,
  }) {
    return ListingsState(
      filters: filters ?? this.filters,
      sort: sort ?? this.sort,
      search: search ?? this.search,
      items: items ?? this.items,
      page: page ?? this.page,
      hasMore: hasMore ?? this.hasMore,
      loading: loading ?? this.loading,
      loadingMore: loadingMore ?? this.loadingMore,
      error: error == _sentinel ? this.error : error as String?,
      aiMode: aiMode ?? this.aiMode,
      aiPending: aiPending ?? this.aiPending,
      aiResult: aiResult == _sentinel
          ? this.aiResult
          : aiResult as AiRecommendOutcome?,
    );
  }
}

const Object _sentinel = Object();

class AiRecommendOutcome {
  const AiRecommendOutcome({
    required this.parsedFilters,
    required this.matches,
    required this.relaxLevel,
  });

  final Map<String, dynamic> parsedFilters;
  final Map<int, double> matches;
  final int relaxLevel;
}

class ListingsController extends Notifier<ListingsState> {
  @override
  ListingsState build() {
    Future.microtask(_loadFirstPage);
    return const ListingsState(loading: true);
  }

  ListingQuery _baseQuery({int? page}) {
    final f = state.filters;
    return ListingQuery(
      brand: f.brand,
      fuelType: f.fuelType,
      region: f.region,
      priceMin: f.priceMin,
      priceMax: f.priceMax,
      yearMin: f.yearMin,
      yearMax: f.yearMax,
      search: state.search.isEmpty ? null : state.search,
      sort: state.sort,
      page: page,
      limit: kListingsPageSize,
    );
  }

  Future<void> _loadFirstPage() async {
    state = state.copyWith(loading: true, error: null);
    try {
      final api = ref.read(listingsApiProvider);
      final list = await api.list(_baseQuery(page: 1));
      state = state.copyWith(
        items: list,
        page: 1,
        hasMore: list.length >= kListingsPageSize,
        loading: false,
      );
    } catch (e) {
      state = state.copyWith(
        loading: false,
        error: extractApiError(e),
        items: const [],
        hasMore: false,
      );
    }
  }

  Future<void> loadMore() async {
    if (state.loading || state.loadingMore || !state.hasMore) return;
    state = state.copyWith(loadingMore: true);
    try {
      final api = ref.read(listingsApiProvider);
      final nextPage = state.page + 1;
      final list = await api.list(_baseQuery(page: nextPage));
      state = state.copyWith(
        items: [...state.items, ...list],
        page: nextPage,
        hasMore: list.length >= kListingsPageSize,
        loadingMore: false,
      );
    } catch (e) {
      state = state.copyWith(loadingMore: false, error: extractApiError(e));
    }
  }

  Future<void> refresh() => _loadFirstPage();

  void setSort(ListingSort sort) {
    if (sort == state.sort) return;
    state = state.copyWith(sort: sort);
    _loadFirstPage();
  }

  void applyFilters(ListingQuery q) {
    state = state.copyWith(filters: q);
    _loadFirstPage();
  }

  void applySearch(String s) {
    state = state.copyWith(search: s.trim());
    _loadFirstPage();
  }

  void clearSearch() {
    state = state.copyWith(search: '', aiResult: null);
    _loadFirstPage();
  }

  void toggleAi() {
    state = state.copyWith(aiMode: !state.aiMode, aiResult: null);
  }

  Future<void> runAiSearch(String query) async {
    final q = query.trim();
    if (q.isEmpty) return;
    state = state.copyWith(search: q, aiPending: true);
    try {
      final api = ref.read(searchApiProvider);
      final r = await api.aiRecommend(q);
      final matches = <int, double>{
        for (final l in r.listings) l.listing.id: l.matchScore,
      };
      state = state.copyWith(
        aiPending: false,
        aiResult: AiRecommendOutcome(
          parsedFilters: r.parsedFilters,
          matches: matches,
          relaxLevel: r.relaxLevel,
        ),
      );
      await _loadFirstPage();
    } catch (e) {
      state = state.copyWith(aiPending: false, error: extractApiError(e));
    }
  }
}

final listingsControllerProvider =
    NotifierProvider<ListingsController, ListingsState>(ListingsController.new);

final popularKeywordsProvider = FutureProvider<List<PopularKeyword>>((ref) async {
  return ref.watch(searchApiProvider).popularKeywords();
});
