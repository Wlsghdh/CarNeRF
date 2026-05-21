import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../shared/widgets/app_chip.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/widgets/loading_shimmer.dart';
import '../vehicle/widgets/vehicle_card.dart';
import 'providers/listings_controller.dart';
import 'widgets/filter_sheet.dart';
import 'widgets/nl_search_bar.dart';
import 'widgets/parsed_filters.dart';
import 'widgets/sort_chips.dart';

const _aiSuggestions = [
  '1500만원 이하 디젤 SUV',
  '주행 5만 이하 그랜저',
  '5년 이내 하이브리드',
  '서울 BMW 4천 이하',
];

class ListingsScreen extends ConsumerStatefulWidget {
  const ListingsScreen({super.key});

  @override
  ConsumerState<ListingsScreen> createState() => _ListingsScreenState();
}

class _ListingsScreenState extends ConsumerState<ListingsScreen> {
  final _searchController = TextEditingController();
  final _scroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scroll.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scroll.position.pixels >
        _scroll.position.maxScrollExtent - 360) {
      ref.read(listingsControllerProvider.notifier).loadMore();
    }
  }

  void _onSubmit() {
    final ctl = ref.read(listingsControllerProvider.notifier);
    final state = ref.read(listingsControllerProvider);
    final q = _searchController.text;
    if (state.aiMode) {
      ctl.runAiSearch(q);
    } else {
      ctl.applySearch(q);
    }
  }

  Future<void> _openFilters() async {
    final state = ref.read(listingsControllerProvider);
    final next = await showFilterSheet(context, initial: state.filters);
    if (next != null && mounted) {
      ref.read(listingsControllerProvider.notifier).applyFilters(next);
    }
  }

  void _onClear() {
    _searchController.clear();
    ref.read(listingsControllerProvider.notifier).clearSearch();
    setState(() {});
  }

  void _toggleAi() {
    ref.read(listingsControllerProvider.notifier).toggleAi();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(listingsControllerProvider);
    final popular = ref.watch(popularKeywordsProvider);

    final items = _filterByAi(state);

    return Scaffold(
      backgroundColor: AppColors.black,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Header(onOpenFilters: _openFilters),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 8),
              child: NLSearchBar(
                controller: _searchController,
                onSubmit: _onSubmit,
                aiMode: state.aiMode,
                onToggleAi: _toggleAi,
                onClear: _onClear,
              ),
            ),
            if (state.aiMode && state.aiResult == null)
              _SectionLabel('AI 추천 검색').padding(
                child: _SuggestionsRow(
                  onPick: (s) {
                    _searchController.text = s;
                    ref.read(listingsControllerProvider.notifier).runAiSearch(s);
                  },
                ),
              ),
            if (!state.aiMode)
              popular.maybeWhen(
                data: (kws) {
                  if (kws.isEmpty) return const SizedBox.shrink();
                  return _SectionLabel('인기 검색어').padding(
                    child: _KeywordsRow(
                      keywords: kws.map((k) => k.text).toList(),
                      active: state.search,
                      onPick: (s) {
                        _searchController.text = s;
                        ref.read(listingsControllerProvider.notifier).applySearch(s);
                      },
                    ),
                  );
                },
                orElse: () => const SizedBox.shrink(),
              ),
            if (state.aiMode && state.aiResult != null)
              _SectionLabel('AI가 이해한 조건').padding(
                child: ParsedFilters(filters: state.aiResult!.parsedFilters),
              ),
            Container(
              height: 1,
              margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              color: Colors.white.withValues(alpha: 0.05),
            ),
            const _SectionLabel('정렬'),
            const SizedBox(height: 6),
            SortChips(
              value: state.sort,
              onChange: ref.read(listingsControllerProvider.notifier).setSort,
            ),
            const SizedBox(height: 8),
            Expanded(child: _ListBody(state: state, items: items, scroll: _scroll)),
          ],
        ),
      ),
    );
  }

  List<_ItemWithScore> _filterByAi(ListingsState state) {
    if (state.aiMode && state.aiResult != null) {
      final matches = state.aiResult!.matches;
      final filtered = state.items
          .where((l) => matches.containsKey(l.id))
          .map((l) => _ItemWithScore(l, matches[l.id]))
          .toList();
      filtered.sort((a, b) => (b.score ?? 0).compareTo(a.score ?? 0));
      return filtered;
    }
    return state.items.map((l) => _ItemWithScore(l, null)).toList();
  }
}

class _ItemWithScore {
  const _ItemWithScore(this.listing, this.score);
  final dynamic listing;
  final double? score;
}

class _Header extends StatelessWidget {
  const _Header({required this.onOpenFilters});
  final VoidCallback onOpenFilters;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '매물 찾기',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
              SizedBox(height: 2),
              Text(
                '3D 검수가 완료된 프리미엄 중고차',
                style: TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
          GestureDetector(
            onTap: onOpenFilters,
            child: Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: const Color(0xFF0E1117),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.tune, size: 18, color: AppColors.gold),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Text(
        text,
        style: const TextStyle(
          color: AppColors.muted,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget padding({required Widget child}) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Text(
              text,
              style: const TextStyle(
                color: AppColors.muted,
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.8,
              ),
            ),
          ),
          const SizedBox(height: 6),
          child,
        ],
      ),
    );
  }
}

class _SuggestionsRow extends StatelessWidget {
  const _SuggestionsRow({required this.onPick});
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 32,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: _aiSuggestions.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final s = _aiSuggestions[i];
          return GestureDetector(
            onTap: () => onPick(s),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.gold.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.auto_awesome, size: 12, color: AppColors.gold),
                  const SizedBox(width: 4),
                  Text(
                    s,
                    style: const TextStyle(
                      color: AppColors.gold,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _KeywordsRow extends StatelessWidget {
  const _KeywordsRow({
    required this.keywords,
    required this.active,
    required this.onPick,
  });

  final List<String> keywords;
  final String active;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 32,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: keywords.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) => AppChip(
          label: '# ${keywords[i]}',
          selected: active == keywords[i],
          onTap: () => onPick(keywords[i]),
          dense: true,
        ),
      ),
    );
  }
}

class _ListBody extends ConsumerWidget {
  const _ListBody({
    required this.state,
    required this.items,
    required this.scroll,
  });

  final ListingsState state;
  final List<_ItemWithScore> items;
  final ScrollController scroll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (state.loading && items.isEmpty) {
      return ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        itemCount: 3,
        separatorBuilder: (_, _) => const SizedBox(height: 14),
        itemBuilder: (_, _) => const LoadingShimmer(height: 240, radius: 16),
      );
    }
    if (state.error != null && items.isEmpty) {
      return ErrorView(
        message: state.error!,
        onRetry: ref.read(listingsControllerProvider.notifier).refresh,
      );
    }
    if (items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.only(top: 60),
        child: Text(
          state.aiMode ? 'AI 검색 결과가 없습니다' : '매물이 없습니다',
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.muted),
        ),
      );
    }
    return ListView.separated(
      controller: scroll,
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
      itemCount: items.length + (state.loadingMore ? 1 : 0),
      separatorBuilder: (_, _) => const SizedBox(height: 14),
      itemBuilder: (_, i) {
        if (i >= items.length) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Center(
              child: SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.4,
                  valueColor: AlwaysStoppedAnimation(AppColors.gold),
                ),
              ),
            ),
          );
        }
        final it = items[i];
        return VehicleCard(
          listing: it.listing,
          matchScore: it.score,
          onPress: () => context.push('/vehicle/${it.listing.id}'),
        );
      },
    );
  }
}
