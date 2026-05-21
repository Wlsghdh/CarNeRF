import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class DarkCard extends StatelessWidget {
  const DarkCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin,
    this.radius = 16,
    this.borderColor,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;
  final double radius;
  final Color? borderColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final border = borderColor ?? AppColors.border;
    final shape = BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: border),
    );

    final body = Container(
      padding: padding,
      decoration: shape,
      child: child,
    );

    final inner = onTap == null
        ? body
        : Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(radius),
              onTap: onTap,
              child: body,
            ),
          );

    return margin == null ? inner : Padding(padding: margin!, child: inner);
  }
}
