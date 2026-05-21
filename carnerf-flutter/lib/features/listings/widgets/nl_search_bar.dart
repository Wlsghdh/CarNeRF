import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

class NLSearchBar extends StatelessWidget {
  const NLSearchBar({
    super.key,
    required this.controller,
    required this.onSubmit,
    required this.aiMode,
    required this.onToggleAi,
    required this.onClear,
  });

  final TextEditingController controller;
  final VoidCallback onSubmit;
  final bool aiMode;
  final VoidCallback onToggleAi;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1117),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Row(
        children: [
          Icon(
            aiMode ? Icons.auto_awesome : Icons.search,
            size: 18,
            color: aiMode ? AppColors.gold : AppColors.muted,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              controller: controller,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => onSubmit(),
              style: const TextStyle(color: AppColors.white, fontSize: 14),
              decoration: InputDecoration(
                isCollapsed: true,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                hintText: aiMode ? '예: 1500만원 이하 디젤 SUV' : '차량명, 브랜드 검색',
                hintStyle: const TextStyle(color: AppColors.muted),
                filled: false,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          if (controller.text.isNotEmpty)
            GestureDetector(
              onTap: onClear,
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 4),
                child: Icon(Icons.close, size: 16, color: AppColors.muted),
              ),
            ),
          const SizedBox(width: 4),
          GestureDetector(
            onTap: onToggleAi,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: aiMode ? AppColors.gold : Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(999),
                border: aiMode
                    ? null
                    : Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.auto_awesome,
                    size: 12,
                    color: aiMode ? AppColors.black : AppColors.gold,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'AI',
                    style: TextStyle(
                      color: aiMode ? AppColors.black : AppColors.white,
                      fontSize: 11,
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
