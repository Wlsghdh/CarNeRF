import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/api/search_api.dart';
import '../../core/models/listing.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters/krw.dart';
import '../../shared/widgets/gold_button.dart';
import '../../shared/widgets/krw_text.dart';

const _tagLabel = {
  'lowest_price': '최저가',
  'lowest_mileage': '최소 주행',
  'best_score': '최고 점수',
};

class CompareScreen extends ConsumerStatefulWidget {
  const CompareScreen({super.key});

  @override
  ConsumerState<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends ConsumerState<CompareScreen> {
  final _idInput = TextEditingController();
  final List<int> _ids = [];
  CompareResult? _data;
  bool _loading = false;

  @override
  void dispose() {
    _idInput.dispose();
    super.dispose();
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: AppColors.surface,
        content: Text(msg, style: const TextStyle(color: AppColors.gold)),
      ),
    );
  }

  Future<void> _runCompare(List<int> ids) async {
    if (ids.isEmpty) {
      setState(() => _data = null);
      return;
    }
    setState(() => _loading = true);
    try {
      final r = await ref.read(searchApiProvider).compare(ids);
      if (!mounted) return;
      setState(() => _data = r);
    } catch (e) {
      _toast(extractApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _add() {
    final n = int.tryParse(_idInput.text.trim());
    if (n == null || n <= 0) return;
    if (_ids.contains(n)) return;
    if (_ids.length >= 4) {
      _toast('최대 4대까지 비교 가능합니다');
      return;
    }
    final next = [..._ids, n];
    setState(() {
      _ids
        ..clear()
        ..addAll(next);
      _idInput.clear();
    });
    _runCompare(next);
  }

  void _remove(int n) {
    final next = _ids.where((x) => x != n).toList();
    setState(() {
      _ids
        ..clear()
        ..addAll(next);
    });
    _runCompare(next);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.black,
      appBar: AppBar(
        backgroundColor: AppColors.black,
        elevation: 0,
        foregroundColor: AppColors.white,
        leading: IconButton(
          icon: const Icon(Icons.chevron_left),
          onPressed: () => context.canPop() ? context.pop() : context.go('/'),
        ),
        title: const Text(
          '차량 비교',
          style: TextStyle(fontWeight: FontWeight.w800),
        ),
      ),
      body: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                '차량 ID로 추가 (최대 4대)',
                style: TextStyle(color: AppColors.muted, fontSize: 12.5),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _idInput,
                      keyboardType: TextInputType.number,
                      style: const TextStyle(color: AppColors.white),
                      onSubmitted: (_) => _add(),
                      decoration: const InputDecoration(
                        hintText: '예: 13',
                        hintStyle: TextStyle(color: AppColors.muted),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  GoldButton(
                    label: '추가',
                    icon: Icons.add,
                    onPressed: _add,
                  ),
                ],
              ),
              if (_ids.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _ids
                      .map((n) => _IdChip(id: n, onRemove: () => _remove(n)))
                      .toList(),
                ),
              ],
              const SizedBox(height: 20),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Center(
                    child: SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.4,
                        valueColor: AlwaysStoppedAnimation(AppColors.gold),
                      ),
                    ),
                  ),
                )
              else if (_data != null && _data!.items.isNotEmpty)
                _ComparisonCarousel(data: _data!)
              else if (_ids.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(top: 28),
                  child: Center(
                    child: Text(
                      '차량 ID를 추가하면 비교 결과가 나타납니다',
                      style: TextStyle(color: AppColors.muted, fontSize: 13),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IdChip extends StatelessWidget {
  const _IdChip({required this.id, required this.onRemove});
  final int id;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onRemove,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.gold.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '#$id',
              style: const TextStyle(
                color: AppColors.gold,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(width: 4),
            const Icon(Icons.close, size: 12, color: AppColors.gold),
          ],
        ),
      ),
    );
  }
}

class _ComparisonCarousel extends StatelessWidget {
  const _ComparisonCarousel({required this.data});
  final CompareResult data;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 220,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: data.items.length,
        separatorBuilder: (_, _) => const SizedBox(width: 12),
        itemBuilder: (_, i) => _CompareCard(
          listing: data.items[i],
          tags: data.tags,
        ),
      ),
    );
  }
}

class _CompareCard extends StatelessWidget {
  const _CompareCard({required this.listing, required this.tags});

  final Listing listing;
  final Map<String, int> tags;

  @override
  Widget build(BuildContext context) {
    final v = listing.vehicle;
    final myTags = tags.entries
        .where((e) => e.value == listing.id)
        .map((e) => _tagLabel[e.key] ?? e.key)
        .toList();

    return Container(
      width: 240,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1117),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            listing.title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 14,
              fontWeight: FontWeight.w800,
              height: 1.4,
            ),
          ),
          if (v != null) ...[
            const SizedBox(height: 6),
            Text(
              '${v.year} · ${formatMileageKm(v.mileage)}',
              style: const TextStyle(color: AppColors.muted, fontSize: 11),
            ),
          ],
          const SizedBox(height: 12),
          KrwText.manwon(listing.price, size: 20),
          const SizedBox(height: 12),
          if (myTags.isNotEmpty)
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: myTags
                  .map((t) => Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.gold,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          t,
                          style: const TextStyle(
                            color: AppColors.black,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ))
                  .toList(),
            ),
        ],
      ),
    );
  }
}
