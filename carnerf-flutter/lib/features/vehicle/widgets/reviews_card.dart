import 'package:flutter/material.dart';

import '../../../core/models/user_review.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/dark_card.dart';

class ReviewsCard extends StatelessWidget {
  const ReviewsCard({super.key, required this.reviews});

  final List<UserReview> reviews;

  @override
  Widget build(BuildContext context) {
    if (reviews.isEmpty) {
      return const DarkCard(
        padding: EdgeInsets.all(20),
        child: Text(
          '아직 후기가 없습니다',
          style: TextStyle(color: AppColors.muted, fontSize: 12),
        ),
      );
    }

    return DarkCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          for (var i = 0; i < reviews.length; i++) ...[
            if (i > 0)
              Container(
                height: 1,
                margin: const EdgeInsets.symmetric(vertical: 14),
                color: Colors.white.withValues(alpha: 0.05),
              ),
            _ReviewRow(review: reviews[i]),
          ],
        ],
      ),
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({required this.review});
  final UserReview review;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: List.generate(5, (i) {
            final filled = i < review.rating;
            return Padding(
              padding: const EdgeInsets.only(right: 2),
              child: Icon(
                filled ? Icons.star : Icons.star_border,
                size: 13,
                color: filled ? AppColors.gold : const Color(0xFF3A3A3A),
              ),
            );
          }),
        ),
        const SizedBox(height: 6),
        Text(
          review.content,
          style: const TextStyle(
            color: AppColors.white,
            fontSize: 13,
            height: 1.5,
          ),
        ),
      ],
    );
  }
}
