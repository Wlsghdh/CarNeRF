import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/dark_card.dart';
import '../../../shared/widgets/loading_shimmer.dart';

class LoadingSectionCard extends StatelessWidget {
  const LoadingSectionCard({super.key, this.height = 96});
  final double height;

  @override
  Widget build(BuildContext context) {
    return DarkCard(
      padding: const EdgeInsets.all(18),
      child: SizedBox(
        height: height,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            LoadingShimmer(height: 14, width: 160),
            SizedBox(height: 10),
            LoadingShimmer(height: 12, width: 220),
            SizedBox(height: 8),
            LoadingShimmer(height: 12, width: 180),
          ],
        ),
      ),
    );
  }
}

class PlaceholderSectionCard extends StatelessWidget {
  const PlaceholderSectionCard({
    super.key,
    required this.label,
    this.icon = Icons.hourglass_empty,
  });

  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return DarkCard(
      padding: const EdgeInsets.all(24),
      child: Row(
        children: [
          Icon(icon, color: AppColors.gold, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: AppColors.muted,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
