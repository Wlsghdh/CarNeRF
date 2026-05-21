import 'package:flutter/material.dart';

import '../../../core/api/listings_api.dart';
import '../../../shared/widgets/app_chip.dart';

const List<({ListingSort value, String label})> _items = [
  (value: ListingSort.newest, label: '최신순'),
  (value: ListingSort.priceAsc, label: '낮은가격'),
  (value: ListingSort.priceDesc, label: '높은가격'),
  (value: ListingSort.mileage, label: '주행거리'),
  (value: ListingSort.regionMatch, label: '지역순'),
];

class SortChips extends StatelessWidget {
  const SortChips({super.key, required this.value, required this.onChange});

  final ListingSort value;
  final ValueChanged<ListingSort> onChange;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 34,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: _items.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final it = _items[i];
          return AppChip(
            label: it.label,
            selected: it.value == value,
            onTap: () => onChange(it.value),
            dense: true,
          );
        },
      ),
    );
  }
}
