import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import 'gold_button.dart';

class ErrorView extends StatelessWidget {
  const ErrorView({
    super.key,
    required this.message,
    this.onRetry,
    this.icon = Icons.error_outline,
  });

  final String message;
  final VoidCallback? onRetry;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: AppColors.gold, size: 48),
            const SizedBox(height: 14),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppColors.white, fontSize: 14),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 18),
              OutlineGoldButton(label: '다시 시도', onPressed: onRetry),
            ],
          ],
        ),
      ),
    );
  }
}
