import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class AppChip extends StatelessWidget {
  const AppChip({
    super.key,
    required this.label,
    this.icon,
    this.selected = false,
    this.onTap,
    this.dense = false,
  });

  final String label;
  final IconData? icon;
  final bool selected;
  final VoidCallback? onTap;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final bg = selected ? AppColors.gold.withValues(alpha: 0.12) : AppColors.surfaceAlt;
    final fg = selected ? AppColors.gold : AppColors.white;
    final borderColor = selected ? AppColors.gold : AppColors.border;
    final pv = dense ? 6.0 : 8.0;
    final ph = dense ? 10.0 : 14.0;

    final body = Container(
      padding: EdgeInsets.symmetric(horizontal: ph, vertical: pv),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: dense ? 12 : 14, color: fg),
            const SizedBox(width: 5),
          ],
          Text(
            label,
            style: TextStyle(
              color: fg,
              fontSize: dense ? 11 : 12.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );

    if (onTap == null) return body;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: body,
      ),
    );
  }
}
