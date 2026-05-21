import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../core/models/price_distribution.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/formatters/dates.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/dark_card.dart';

class PriceDistributionChart extends StatelessWidget {
  const PriceDistributionChart({
    super.key,
    required this.distribution,
    required this.ownPrice,
  });

  final PriceDistribution distribution;
  final int ownPrice;

  @override
  Widget build(BuildContext context) {
    final stats = distribution.stats;
    if (stats == null || stats.sampleSize < 5) {
      return DarkCard(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _Header(range: ''),
            const SizedBox(height: 8),
            Text(
              '비교 표본이 부족합니다 (${stats?.sampleSize ?? 0}건)',
              style: const TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ],
        ),
      );
    }

    final now = DateTime.now();
    final dates = [
      ...distribution.transactions.map((t) => t.date.millisecondsSinceEpoch),
      ...distribution.listings.map((l) => l.date.millisecondsSinceEpoch),
    ];
    final oldestMs = dates.isEmpty
        ? now.subtract(const Duration(days: 365)).millisecondsSinceEpoch
        : dates.reduce((a, b) => a < b ? a : b);
    final todayMs = now.millisecondsSinceEpoch;

    final xMin = stats.min * 0.9;
    final xMax = stats.max * 1.05;

    final diff = ((ownPrice - stats.avg) / stats.avg) * 100;
    final absDiff = diff.abs().toStringAsFixed(1);
    final tone = diff < -3
        ? _Tone.cheap
        : diff > 3
            ? _Tone.pricey
            : _Tone.fair;

    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Header(range: distribution.range),
          const SizedBox(height: 12),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _StatChip(label: '평균', value: '${formatKrw(stats.avg.round())}만'),
              _StatChip(label: '최저', value: '${formatKrw(stats.min)}만'),
              _StatChip(label: '최고', value: '${formatKrw(stats.max)}만'),
              _StatChip(label: '중간값', value: '${formatKrw(stats.p50)}만'),
              _StatChip(label: '샘플', value: '${stats.sampleSize}건'),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 200,
            child: _ScatterView(
              distribution: distribution,
              ownPrice: ownPrice.toDouble(),
              avg: stats.avg,
              xMin: xMin,
              xMax: xMax,
              oldestMs: oldestMs,
              todayMs: todayMs,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Icon(
                tone == _Tone.cheap ? Icons.trending_down : Icons.trending_up,
                size: 14,
                color: tone.color,
              ),
              const SizedBox(width: 5),
              Text(
                '평균 대비 $absDiff% ${diff < 0 ? '낮은' : '높은'} 가격 — ${tone.label}',
                style: TextStyle(
                  color: tone.color,
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 14,
            children: const [
              _Legend(color: AppColors.muted, label: '과거 거래'),
              _Legend(color: AppColors.gold, label: '활성 매물', hollow: true),
              _Legend(color: AppColors.gold, label: '내 차'),
            ],
          ),
        ],
      ),
    );
  }
}

enum _Tone { cheap, fair, pricey }

extension on _Tone {
  Color get color {
    switch (this) {
      case _Tone.cheap:
        return const Color(0xFF22C55E);
      case _Tone.pricey:
        return const Color(0xFFEF4444);
      case _Tone.fair:
        return AppColors.gold;
    }
  }

  String get label {
    switch (this) {
      case _Tone.cheap:
        return '저렴';
      case _Tone.pricey:
        return '비쌈';
      case _Tone.fair:
        return '적정';
    }
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.range});
  final String range;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: const [
            Icon(Icons.trending_up, color: AppColors.gold, size: 16),
            SizedBox(width: 6),
            Text(
              '가격 분포',
              style: TextStyle(
                color: AppColors.white,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
        if (range.isNotEmpty)
          Text(
            range,
            style: const TextStyle(color: AppColors.muted, fontSize: 10.5),
          ),
      ],
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: const TextStyle(color: AppColors.muted, fontSize: 10.5),
          ),
          const SizedBox(width: 4),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({
    required this.color,
    required this.label,
    this.hollow = false,
  });
  final Color color;
  final String label;
  final bool hollow;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(
            color: hollow ? Colors.transparent : color,
            shape: BoxShape.circle,
            border: hollow ? Border.all(color: color, width: 1.5) : null,
          ),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: const TextStyle(color: AppColors.muted, fontSize: 10.5),
        ),
      ],
    );
  }
}

class _ScatterView extends StatelessWidget {
  const _ScatterView({
    required this.distribution,
    required this.ownPrice,
    required this.avg,
    required this.xMin,
    required this.xMax,
    required this.oldestMs,
    required this.todayMs,
  });

  final PriceDistribution distribution;
  final double ownPrice;
  final double avg;
  final double xMin;
  final double xMax;
  final int oldestMs;
  final int todayMs;

  @override
  Widget build(BuildContext context) {
    final yMin = 0.0;
    final yMax = (todayMs - oldestMs).toDouble().clamp(1.0, double.infinity);

    double yFor(int ms) => (todayMs - ms).toDouble().clamp(0.0, yMax);

    final txnSpots = [
      for (final t in distribution.transactions)
        ScatterSpot(
          t.price.toDouble(),
          yFor(t.date.millisecondsSinceEpoch),
          dotPainter: FlDotCirclePainter(
            radius: 3,
            color: AppColors.muted.withValues(alpha: 0.55),
          ),
        ),
    ];
    final listSpots = [
      for (final l in distribution.listings)
        ScatterSpot(
          l.price.toDouble(),
          yFor(l.date.millisecondsSinceEpoch),
          dotPainter: FlDotCirclePainter(
            radius: 4,
            color: Colors.transparent,
            strokeColor: AppColors.gold,
            strokeWidth: 1.5,
          ),
        ),
    ];
    final mineSpot = ScatterSpot(
      ownPrice,
      yFor(todayMs),
      dotPainter: FlDotCirclePainter(
        radius: 6,
        color: AppColors.gold,
        strokeColor: AppColors.gold.withValues(alpha: 0.25),
        strokeWidth: 8,
      ),
    );

    final xStep = (xMax - xMin) / 4;
    return Stack(
      children: [
        ScatterChart(
          ScatterChartData(
            minX: xMin,
            maxX: xMax,
            minY: yMin,
            maxY: yMax,
            scatterSpots: [...txnSpots, ...listSpots, mineSpot],
            gridData: FlGridData(
              show: true,
              drawHorizontalLine: true,
              drawVerticalLine: false,
              horizontalInterval: yMax / 4,
              getDrawingHorizontalLine: (_) => FlLine(
                color: Colors.white.withValues(alpha: 0.05),
                strokeWidth: 1,
              ),
            ),
            borderData: FlBorderData(show: false),
            scatterTouchData: ScatterTouchData(enabled: false),
            titlesData: FlTitlesData(
              leftTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false),
              ),
              rightTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false),
              ),
              topTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 22,
                  interval: xStep,
                  getTitlesWidget: (value, _) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        formatKrw(value.round()),
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 9.5,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
        Positioned.fill(
          left: 0,
          right: 0,
          child: LayoutBuilder(
            builder: (context, c) {
              final w = c.maxWidth;
              final h = c.maxHeight;
              final axisX = ((avg - xMin) / (xMax - xMin)) * w;
              return Stack(
                children: [
                  Positioned(
                    left: axisX,
                    top: 0,
                    bottom: 22,
                    child: CustomPaint(
                      size: const Size(1, double.infinity),
                      painter: _DashedLinePainter(),
                    ),
                  ),
                  Positioned(
                    left: axisX - 14,
                    top: 0,
                    child: const Text(
                      '평균',
                      style: TextStyle(
                        color: AppColors.gold,
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Positioned(
                    left: 4,
                    top: 0,
                    child: const Text(
                      '오늘',
                      style: TextStyle(color: AppColors.muted, fontSize: 9.5),
                    ),
                  ),
                  Positioned(
                    left: 4,
                    bottom: 22,
                    child: Text(
                      formatYm(DateTime.fromMillisecondsSinceEpoch(oldestMs)),
                      style: const TextStyle(color: AppColors.muted, fontSize: 9.5),
                    ),
                  ),
                  IgnorePointer(
                    child: _MineLabel(x: ((ownPrice - xMin) / (xMax - xMin)) * w, h: h),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _MineLabel extends StatelessWidget {
  const _MineLabel({required this.x, required this.h});
  final double x;
  final double h;

  @override
  Widget build(BuildContext context) {
    final clampedX = x.clamp(20.0, double.maxFinite);
    return Positioned(
      left: clampedX - 12,
      top: 6,
      child: const Text(
        '내 차',
        style: TextStyle(
          color: AppColors.gold,
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _DashedLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.gold.withValues(alpha: 0.4)
      ..strokeWidth = 1;
    const dashH = 4.0;
    const gap = 3.0;
    var y = 0.0;
    while (y < size.height) {
      canvas.drawLine(Offset(0, y), Offset(0, y + dashH), paint);
      y += dashH + gap;
    }
  }

  @override
  bool shouldRepaint(_) => false;
}
