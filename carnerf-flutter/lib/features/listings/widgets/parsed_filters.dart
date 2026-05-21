import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/formatters/krw.dart';

const Map<String, String> _keyLabels = {
  'brand': '브랜드',
  'model': '모델',
  'fuel_type': '연료',
  'region': '지역',
  'price_min': '최저가',
  'price_max': '최고가',
  'year_min': '연식↑',
  'year_max': '연식↓',
  'mileage_max': '주행↓',
  'keywords': '키워드',
};

String _formatValue(String k, dynamic v) {
  if (v is List) return v.join(',');
  if (v is num) {
    if (k == 'price_min' || k == 'price_max') return '${formatKrw(v)}만';
    if (k == 'mileage_max') return '${formatKrw(v)}km';
    return v.toString();
  }
  return v.toString();
}

class ParsedFilters extends StatelessWidget {
  const ParsedFilters({super.key, required this.filters});

  final Map<String, dynamic> filters;

  @override
  Widget build(BuildContext context) {
    final entries = filters.entries.where((e) {
      final v = e.value;
      if (v == null) return false;
      if (v is String) return v.isNotEmpty;
      if (v is List) return v.isNotEmpty;
      return true;
    }).toList();

    if (entries.isEmpty) return const SizedBox.shrink();

    return SizedBox(
      height: 30,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: entries.length,
        separatorBuilder: (_, _) => const SizedBox(width: 6),
        itemBuilder: (_, i) {
          final e = entries[i];
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.gold.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
            ),
            child: Text(
              '${_keyLabels[e.key] ?? e.key}: ${_formatValue(e.key, e.value)}',
              style: const TextStyle(
                color: AppColors.gold,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          );
        },
      ),
    );
  }
}
