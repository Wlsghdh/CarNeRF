import 'package:flutter/material.dart';

import '../../../core/models/vehicle_summary.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/dark_card.dart';

class AISummaryCard extends StatelessWidget {
  const AISummaryCard({super.key, required this.summary});

  final VehicleSummary summary;

  @override
  Widget build(BuildContext context) {
    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.gold, size: 16),
              const SizedBox(width: 6),
              const Text(
                'AI 차량 요약',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.gold.withValues(alpha: 0.20),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Text(
                  '전용 RAG · 실제 후기 기반',
                  style: TextStyle(
                    color: AppColors.gold,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (summary.summary.isNotEmpty)
            Text(
              summary.summary,
              style: const TextStyle(
                color: AppColors.white,
                fontSize: 13,
                height: 1.6,
              ),
            ),
          _PointList(
            icon: Icons.thumb_up_outlined,
            iconColor: AppColors.gold,
            title: '장점',
            titleColor: AppColors.gold,
            items: summary.pros,
          ),
          _PointList(
            icon: Icons.thumb_down_outlined,
            iconColor: AppColors.muted,
            title: '단점',
            titleColor: AppColors.muted,
            items: summary.cons,
          ),
          _PointList(
            icon: Icons.warning_amber_outlined,
            iconColor: const Color(0xFFEAB308),
            title: '고질병',
            titleColor: const Color(0xFFFDE68A),
            items: summary.knownIssues,
          ),
          if (summary.reviewSummary != null && summary.reviewSummary!.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.gold.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.gold.withValues(alpha: 0.25)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.menu_book_outlined,
                          size: 12, color: AppColors.gold),
                      SizedBox(width: 4),
                      Text(
                        '실제 오너 후기 RAG 요약',
                        style: TextStyle(
                          color: AppColors.gold,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    summary.reviewSummary!,
                    style: const TextStyle(
                      color: AppColors.white,
                      fontSize: 12,
                      height: 1.55,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PointList extends StatelessWidget {
  const _PointList({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.titleColor,
    required this.items,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final Color titleColor;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 13, color: iconColor),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  color: titleColor,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          for (final it in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '• $it',
                style: const TextStyle(
                  color: AppColors.white,
                  fontSize: 12,
                  height: 1.55,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
