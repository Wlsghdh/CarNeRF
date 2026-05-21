import 'package:flutter/material.dart';

import '../../../core/models/defect_report.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/dark_card.dart';

const Map<DefectSeverity, Color> _severityColor = {
  DefectSeverity.low: Color(0xFF22C55E),
  DefectSeverity.medium: Color(0xFFEAB308),
  DefectSeverity.high: Color(0xFFEF4444),
};

const Map<DefectSeverity, String> _severityLabel = {
  DefectSeverity.low: '경미',
  DefectSeverity.medium: '중간',
  DefectSeverity.high: '심각',
};

const Map<DefectSeverity, String> _severityCode = {
  DefectSeverity.low: 'LOW',
  DefectSeverity.medium: 'MEDIUM',
  DefectSeverity.high: 'HIGH',
};

class DefectBars extends StatelessWidget {
  const DefectBars({super.key, required this.report});

  final DefectReport report;

  @override
  Widget build(BuildContext context) {
    final counts = <DefectSeverity, int>{
      DefectSeverity.low: 0,
      DefectSeverity.medium: 0,
      DefectSeverity.high: 0,
    };
    for (final d in report.defects) {
      counts[d.severity] = (counts[d.severity] ?? 0) + 1;
    }
    final totalForRatio = counts.values.fold<int>(0, (a, b) => a + b);
    final denom = totalForRatio == 0 ? 1 : totalForRatio;

    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                children: const [
                  Icon(Icons.shield_outlined, color: AppColors.gold, size: 16),
                  SizedBox(width: 6),
                  Text(
                    'AI 결함 리포트',
                    style: TextStyle(
                      color: AppColors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              RichText(
                text: TextSpan(
                  text: report.totalDefectScore.toStringAsFixed(1),
                  style: const TextStyle(
                    color: AppColors.gold,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                  ),
                  children: const [
                    TextSpan(
                      text: ' 점',
                      style: TextStyle(
                        color: AppColors.muted,
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          for (final s in DefectSeverity.values)
            _Row(
              label: _severityLabel[s]!,
              color: _severityColor[s]!,
              count: counts[s]!,
              ratio: counts[s]! / denom,
            ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.only(top: 12),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: RichText(
              text: TextSpan(
                style: const TextStyle(color: AppColors.muted, fontSize: 11.5),
                text: '전체 등급:  ',
                children: [
                  TextSpan(
                    text: _severityCode[report.severityLevel],
                    style: TextStyle(
                      color: _severityColor[report.severityLevel],
                      fontSize: 12.5,
                      fontWeight: FontWeight.w800,
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

class _Row extends StatelessWidget {
  const _Row({
    required this.label,
    required this.color,
    required this.count,
    required this.ratio,
  });

  final String label;
  final Color color;
  final int count;
  final double ratio;

  @override
  Widget build(BuildContext context) {
    final pct = (ratio * 100).clamp(4, 100);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: const TextStyle(
                  color: AppColors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '$count건',
                style: const TextStyle(
                  color: AppColors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          LayoutBuilder(
            builder: (context, c) {
              return Stack(
                children: [
                  Container(
                    height: 6,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                  Container(
                    height: 6,
                    width: c.maxWidth * pct / 100,
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
