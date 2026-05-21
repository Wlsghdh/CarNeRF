import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/dark_card.dart';
import '../providers/detail_providers.dart';

class _Pt {
  const _Pt(this.ms, this.price);
  final int ms;
  final int price;
}

class PriceTrendChart extends ConsumerWidget {
  const PriceTrendChart({
    super.key,
    required this.vehicleId,
    required this.ownPrice,
    this.predictedLow,
    this.predictedHigh,
    this.confidence,
    this.viewerIsSeller = false,
  });

  final int vehicleId;
  final int ownPrice;
  final int? predictedLow;
  final int? predictedHigh;
  final double? confidence;
  final bool viewerIsSeller;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(marketTrendProvider(vehicleId));
    return async.when(
      loading: () => _shell(_loadingChart()),
      error: (_, _) => _shell(_emptyChart('시세 데이터를 불러오지 못했습니다')),
      data: (monthly) {
        final points = _parsePoints(monthly);
        return _shell(_buildContent(context, points));
      },
    );
  }

  Widget _shell(Widget child) => DarkCard(
        padding: const EdgeInsets.all(20),
        child: child,
      );

  Widget _emptyChart(String msg) => SizedBox(
        height: 160,
        child: Center(
          child: Text(
            msg,
            style: const TextStyle(color: AppColors.muted, fontSize: 12),
          ),
        ),
      );

  Widget _loadingChart() => const SizedBox(
        height: 160,
        child: Center(
          child: SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(
              strokeWidth: 2.6,
              valueColor: AlwaysStoppedAnimation(AppColors.gold),
            ),
          ),
        ),
      );

  List<_Pt> _parsePoints(List monthly) {
    final now = DateTime.now();
    final startMs = now.subtract(const Duration(days: 365)).millisecondsSinceEpoch;
    final list = <_Pt>[];
    for (final m in monthly) {
      final monthStr = m.month as String;
      final match = RegExp(r'^(\d{4})-(\d{1,2})').firstMatch(monthStr);
      if (match == null) continue;
      final year = int.parse(match.group(1)!);
      final month = int.parse(match.group(2)!);
      if (month < 1 || month > 12) continue;
      final ms = DateTime(year, month, 15).millisecondsSinceEpoch;
      if (ms < startMs - 30 * 86400000) continue;
      final p = m.price as int;
      if (p <= 0) continue;
      list.add(_Pt(ms, p));
    }
    list.sort((a, b) => a.ms.compareTo(b.ms));
    return list;
  }

  Widget _buildContent(BuildContext context, List<_Pt> points) {
    final headerRight = viewerIsSeller
        ? '내 매물 기준'
        : (confidence != null
            ? 'AI 신뢰도 ${(confidence! * 100).round()}%'
            : '');

    final cmp = _comparison(points);
    final latestPrice = points.isEmpty ? null : points.last.price;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              '이 차량 시세',
              style: TextStyle(
                color: AppColors.white,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
            if (headerRight.isNotEmpty)
              Text(
                headerRight,
                style: const TextStyle(
                  color: AppColors.muted,
                  fontSize: 10.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              formatKrw(ownPrice),
              style: const TextStyle(
                color: AppColors.gold,
                fontSize: 28,
                fontWeight: FontWeight.w800,
              ),
            ),
            const Padding(
              padding: EdgeInsets.only(left: 4, bottom: 4),
              child: Text(
                '만 · 판매가',
                style: TextStyle(color: AppColors.muted, fontSize: 11),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Icon(cmp.icon, size: 13, color: cmp.color),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                cmp.text,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: cmp.color,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (cmp.range != null)
              Text(
                cmp.range!,
                style: const TextStyle(color: AppColors.muted, fontSize: 10.5),
              ),
          ],
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 150,
          child: points.length < 2
              ? Center(
                  child: Text(
                    '시세 데이터를 모으는 중입니다',
                    style: const TextStyle(color: AppColors.muted, fontSize: 12),
                  ),
                )
              : _LineChartView(points: points, latestPrice: latestPrice),
        ),
      ],
    );
  }

  _Comparison _comparison(List<_Pt> points) {
    if (viewerIsSeller) {
      return const _Comparison(
        icon: Icons.show_chart,
        color: AppColors.muted,
        text: '최근 12개월 추세를 확인하세요',
      );
    }
    final showAi = predictedLow != null &&
        predictedHigh != null &&
        predictedHigh! > predictedLow!;
    if (showAi && ownPrice > 0) {
      final mid = (predictedLow! + predictedHigh!) / 2;
      final diff = ((ownPrice - mid) / mid) * 100;
      final abs = diff.abs().toStringAsFixed(1);
      final range = 'AI ${formatKrw(predictedLow!)}~${formatKrw(predictedHigh!)}만';
      if (diff < -3) {
        return _Comparison(
          icon: Icons.trending_down,
          color: const Color(0xFF22C55E),
          text: 'AI 공정가 대비 $abs% 저렴 · 합리적',
          range: range,
        );
      }
      if (diff > 3) {
        return _Comparison(
          icon: Icons.trending_up,
          color: const Color(0xFFEF4444),
          text: 'AI 공정가 대비 $abs% 높음 · 협상 여지',
          range: range,
        );
      }
      return _Comparison(
        icon: Icons.remove,
        color: AppColors.gold,
        text: 'AI 공정가 범위 내 · 적정',
        range: range,
      );
    }
    if (points.isNotEmpty && ownPrice > 0) {
      final latest = points.last.price;
      final diff = ((ownPrice - latest) / latest) * 100;
      final abs = diff.abs().toStringAsFixed(1);
      if (diff < -3) {
        return _Comparison(
          icon: Icons.trending_down,
          color: const Color(0xFF22C55E),
          text: '평균 대비 $abs% 낮음 — 저렴',
        );
      }
      if (diff > 3) {
        return _Comparison(
          icon: Icons.trending_up,
          color: const Color(0xFFEF4444),
          text: '평균 대비 $abs% 높음 — 비쌈',
        );
      }
      return _Comparison(
        icon: Icons.remove,
        color: AppColors.gold,
        text: '평균 대비 $abs% — 적정',
      );
    }
    return const _Comparison(
      icon: Icons.hourglass_empty,
      color: AppColors.muted,
      text: '시세 데이터를 모으는 중입니다',
    );
  }
}

class _Comparison {
  const _Comparison({
    required this.icon,
    required this.color,
    required this.text,
    this.range,
  });
  final IconData icon;
  final Color color;
  final String text;
  final String? range;
}

class _LineChartView extends StatelessWidget {
  const _LineChartView({required this.points, required this.latestPrice});
  final List<_Pt> points;
  final int? latestPrice;

  @override
  Widget build(BuildContext context) {
    final minX = points.first.ms.toDouble();
    final maxX = points.last.ms.toDouble();
    final prices = points.map((p) => p.price.toDouble()).toList();
    var minY = prices.reduce((a, b) => a < b ? a : b);
    var maxY = prices.reduce((a, b) => a > b ? a : b);
    if (maxY - minY < 1) {
      final c = (maxY + minY) / 2;
      minY = c * 0.9;
      maxY = c * 1.1;
    } else {
      final pad = (maxY - minY) * 0.1;
      minY = (minY - pad).clamp(0, double.infinity).toDouble();
      maxY = maxY + pad;
    }

    final spots = [
      for (final p in points) FlSpot(p.ms.toDouble(), p.price.toDouble()),
    ];

    return LineChart(
      LineChartData(
        minX: minX,
        maxX: maxX,
        minY: minY,
        maxY: maxY,
        gridData: const FlGridData(show: false),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 18,
              getTitlesWidget: (value, _) {
                if (value == minX) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text(
                      '12개월 전',
                      style: TextStyle(color: AppColors.muted, fontSize: 9.5),
                    ),
                  );
                }
                if (value == maxX) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text(
                      '오늘',
                      style: TextStyle(color: AppColors.muted, fontSize: 9.5),
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
          ),
        ),
        lineTouchData: const LineTouchData(enabled: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            curveSmoothness: 0.18,
            color: AppColors.gold,
            barWidth: 2.2,
            isStrokeCapRound: true,
            dotData: FlDotData(
              show: true,
              checkToShowDot: (spot, _) => spot.x == maxX,
              getDotPainter: (spot, _, _, _) => FlDotCirclePainter(
                radius: 4,
                color: AppColors.gold,
                strokeColor: AppColors.gold.withValues(alpha: 0.4),
                strokeWidth: 6,
              ),
            ),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  AppColors.gold.withValues(alpha: 0.35),
                  AppColors.gold.withValues(alpha: 0.0),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
