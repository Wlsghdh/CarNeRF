import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../formatters/krw.dart';

class KrwText extends StatelessWidget {
  const KrwText.manwon(
    this.value, {
    super.key,
    this.size = 16,
    this.weight = FontWeight.w800,
    this.color = AppColors.gold,
    this.unitColor = AppColors.muted,
    this.compactEok = false,
  }) : asManwon = true;

  const KrwText.won(
    this.value, {
    super.key,
    this.size = 14,
    this.weight = FontWeight.w700,
    this.color = AppColors.white,
    this.unitColor = AppColors.muted,
  })  : asManwon = false,
        compactEok = false;

  final num value;
  final double size;
  final FontWeight weight;
  final Color color;
  final Color unitColor;
  final bool asManwon;
  final bool compactEok;

  @override
  Widget build(BuildContext context) {
    if (asManwon) {
      if (compactEok && value >= 10000) {
        return Text(
          compactKrwMan(value),
          style: TextStyle(color: color, fontSize: size, fontWeight: weight),
        );
      }
      return RichText(
        text: TextSpan(
          style: TextStyle(color: color, fontSize: size, fontWeight: weight),
          text: formatKrw(value),
          children: [
            TextSpan(
              text: ' 만원',
              style: TextStyle(
                color: unitColor,
                fontSize: size * 0.6,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }
    return RichText(
      text: TextSpan(
        style: TextStyle(color: color, fontSize: size, fontWeight: weight),
        text: formatKrw(value),
        children: [
          TextSpan(
            text: ' 원',
            style: TextStyle(
              color: unitColor,
              fontSize: size * 0.7,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
