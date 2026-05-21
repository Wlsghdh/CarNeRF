import 'package:flutter/material.dart';

import '../../../core/api/listings_api.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_chip.dart';
import '../../../shared/widgets/gold_button.dart';

const _all = '전체';
const _brands = [
  _all, '현대', '기아', '제네시스', '쉐보레', 'BMW', '벤츠', '아우디', '렉서스', '포르쉐'
];
const _fuels = [_all, '가솔린', '디젤', 'LPG', '하이브리드', '전기'];
const _regions = [
  _all, '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산'
];

Future<ListingQuery?> showFilterSheet(
  BuildContext context, {
  required ListingQuery initial,
}) {
  return showModalBottomSheet<ListingQuery>(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColors.black,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (_) => _FilterSheet(initial: initial),
  );
}

class _FilterSheet extends StatefulWidget {
  const _FilterSheet({required this.initial});
  final ListingQuery initial;

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  late String _brand = widget.initial.brand ?? _all;
  late String _fuel = widget.initial.fuelType ?? _all;
  late String _region = widget.initial.region ?? _all;
  late final _priceMin = TextEditingController(
    text: widget.initial.priceMin?.toString() ?? '',
  );
  late final _priceMax = TextEditingController(
    text: widget.initial.priceMax?.toString() ?? '',
  );
  late final _yearMin = TextEditingController(
    text: widget.initial.yearMin?.toString() ?? '',
  );
  late final _yearMax = TextEditingController(
    text: widget.initial.yearMax?.toString() ?? '',
  );

  @override
  void dispose() {
    _priceMin.dispose();
    _priceMax.dispose();
    _yearMin.dispose();
    _yearMax.dispose();
    super.dispose();
  }

  void _reset() {
    setState(() {
      _brand = _all;
      _fuel = _all;
      _region = _all;
      _priceMin.clear();
      _priceMax.clear();
      _yearMin.clear();
      _yearMax.clear();
    });
  }

  void _apply() {
    int? parse(TextEditingController c) {
      final t = c.text.trim();
      if (t.isEmpty) return null;
      return int.tryParse(t);
    }

    final next = ListingQuery(
      brand: _brand == _all ? null : _brand,
      fuelType: _fuel == _all ? null : _fuel,
      region: _region == _all ? null : _region,
      priceMin: parse(_priceMin),
      priceMax: parse(_priceMax),
      yearMin: parse(_yearMin),
      yearMax: parse(_yearMax),
    );
    Navigator.of(context).pop(next);
  }

  @override
  Widget build(BuildContext context) {
    final viewInsets = MediaQuery.viewInsetsOf(context).bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: viewInsets),
      child: SafeArea(
        top: false,
        child: FractionallySizedBox(
          heightFactor: 0.88,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      '필터',
                      style: TextStyle(
                        color: AppColors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: TextButton.styleFrom(foregroundColor: AppColors.muted),
                      child: const Text('닫기'),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _Section(title: '브랜드', child: _ChipRow(
                        items: _brands,
                        active: _brand,
                        onPick: (s) => setState(() => _brand = s),
                      )),
                      _Section(title: '연료', child: _ChipRow(
                        items: _fuels,
                        active: _fuel,
                        onPick: (s) => setState(() => _fuel = s),
                      )),
                      _Section(title: '지역', child: _ChipRow(
                        items: _regions,
                        active: _region,
                        onPick: (s) => setState(() => _region = s),
                      )),
                      _Section(
                        title: '가격 (만원)',
                        child: _NumberPair(min: _priceMin, max: _priceMax),
                      ),
                      _Section(
                        title: '연식',
                        child: _NumberPair(
                          min: _yearMin,
                          max: _yearMax,
                          minHint: '최소 (예: 2018)',
                          maxHint: '최대 (예: 2024)',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 16),
                decoration: const BoxDecoration(
                  border: Border(top: BorderSide(color: AppColors.border)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlineGoldButton(label: '초기화', onPressed: _reset),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: GoldButton(label: '적용하기', onPressed: _apply),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}

class _ChipRow extends StatelessWidget {
  const _ChipRow({
    required this.items,
    required this.active,
    required this.onPick,
  });

  final List<String> items;
  final String active;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (_, i) => AppChip(
          label: items[i],
          selected: active == items[i],
          onTap: () => onPick(items[i]),
        ),
      ),
    );
  }
}

class _NumberPair extends StatelessWidget {
  const _NumberPair({
    required this.min,
    required this.max,
    this.minHint = '최소',
    this.maxHint = '최대',
  });

  final TextEditingController min;
  final TextEditingController max;
  final String minHint;
  final String maxHint;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: _NumberField(controller: min, hint: minHint)),
        const SizedBox(width: 12),
        Expanded(child: _NumberField(controller: max, hint: maxHint)),
      ],
    );
  }
}

class _NumberField extends StatelessWidget {
  const _NumberField({required this.controller, required this.hint});
  final TextEditingController controller;
  final String hint;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: TextInputType.number,
      style: const TextStyle(color: AppColors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AppColors.muted),
      ),
    );
  }
}
