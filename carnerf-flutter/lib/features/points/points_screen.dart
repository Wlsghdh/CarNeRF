import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api/api_client.dart';
import '../../core/api/points_api.dart';
import '../../core/models/point_transaction.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters/krw.dart';
import '../../shared/widgets/app_chip.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/widgets/gold_button.dart';
import '../../shared/widgets/loading_shimmer.dart';
import 'providers/points_providers.dart';

const _chargePresets = [10000, 30000, 50000, 100000];

class PointsScreen extends ConsumerStatefulWidget {
  const PointsScreen({super.key});

  @override
  ConsumerState<PointsScreen> createState() => _PointsScreenState();
}

class _PointsScreenState extends ConsumerState<PointsScreen> {
  final _amount = TextEditingController();
  bool _charging = false;

  @override
  void dispose() {
    _amount.dispose();
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

  Future<void> _charge() async {
    final n = int.tryParse(_amount.text.trim());
    if (n == null || n < 1000 || n > 1000000) {
      _toast('1,000 ~ 1,000,000 사이로 입력하세요');
      return;
    }
    setState(() => _charging = true);
    try {
      await ref.read(pointsApiProvider).charge(n);
      ref.invalidate(pointsBalanceProvider);
      ref.invalidate(pointsHistoryProvider);
      if (!mounted) return;
      _amount.clear();
      _toast('충전이 완료되었습니다');
    } catch (e) {
      _toast(extractApiError(e));
    } finally {
      if (mounted) setState(() => _charging = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final balance = ref.watch(pointsBalanceProvider);
    final history = ref.watch(pointsHistoryProvider);
    final amount = int.tryParse(_amount.text) ?? 0;

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
          '포인트',
          style: TextStyle(fontWeight: FontWeight.w800),
        ),
      ),
      body: SafeArea(
        top: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
              child: _BalanceCard(balance: balance),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '충전 (1,000 ~ 1,000,000)',
                    style: TextStyle(
                      color: AppColors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _chargePresets
                        .map((p) => AppChip(
                              label: '${formatKrw(p)}P',
                              selected: _amount.text == p.toString(),
                              onTap: () => setState(() {
                                _amount.text = p.toString();
                                _amount.selection = TextSelection.fromPosition(
                                  TextPosition(offset: _amount.text.length),
                                );
                              }),
                              dense: true,
                            ))
                        .toList(),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _amount,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(color: AppColors.white),
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(
                      hintText: '직접 입력',
                      hintStyle: TextStyle(color: AppColors.muted),
                    ),
                  ),
                  const SizedBox(height: 14),
                  GoldButton(
                    label: '${formatKrw(amount)}P 충전하기',
                    loading: _charging,
                    expand: true,
                    onPressed: _charge,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text(
                '이력',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            Expanded(child: _HistoryList(async: history)),
          ],
        ),
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  const _BalanceCard({required this.balance});
  final AsyncValue<int> balance;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1117),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.monetization_on_outlined,
                  size: 18, color: AppColors.gold),
              SizedBox(width: 6),
              Text(
                '현재 잔액',
                style: TextStyle(
                  color: AppColors.muted,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          balance.when(
            loading: () => const LoadingShimmer(width: 120, height: 28),
            error: (_, _) => const Text(
              '잔액을 불러오지 못했습니다',
              style: TextStyle(color: AppColors.muted),
            ),
            data: (b) => RichText(
              text: TextSpan(
                text: formatKrw(b),
                style: const TextStyle(
                  color: AppColors.gold,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
                children: const [
                  TextSpan(
                    text: ' P',
                    style: TextStyle(
                      color: AppColors.muted,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryList extends ConsumerWidget {
  const _HistoryList({required this.async});
  final AsyncValue<PointsHistoryPage> async;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return async.when(
      loading: () => ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        itemCount: 4,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (_, _) => const LoadingShimmer(height: 44),
      ),
      error: (e, _) => Padding(
        padding: const EdgeInsets.only(top: 16),
        child: ErrorView(
          message: '이력을 불러오지 못했습니다',
          onRetry: () => ref.invalidate(pointsHistoryProvider),
        ),
      ),
      data: (page) {
        if (page.items.isEmpty) {
          return const Padding(
            padding: EdgeInsets.only(top: 32),
            child: Text(
              '이력이 없습니다',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.muted),
            ),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
          itemCount: page.items.length,
          separatorBuilder: (_, _) => Container(
            height: 1,
            color: Colors.white.withValues(alpha: 0.05),
          ),
          itemBuilder: (_, i) => _HistoryRow(tx: page.items[i]),
        );
      },
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.tx});
  final PointTransaction tx;

  @override
  Widget build(BuildContext context) {
    final isCredit = tx.amount > 0;
    final fmt = DateFormat('yyyy.MM.dd HH:mm', 'ko_KR');
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  tx.description.isEmpty ? '내역' : tx.description,
                  style: const TextStyle(
                    color: AppColors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  fmt.format(tx.createdAt),
                  style: const TextStyle(color: AppColors.muted, fontSize: 11),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${isCredit ? '+' : ''}${formatKrw(tx.amount)}P',
            style: TextStyle(
              color: isCredit ? AppColors.gold : AppColors.muted,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
