import 'package:flutter/material.dart';

import '../../../core/constants/car_options.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/dark_card.dart';
import '../../../shared/widgets/gold_button.dart';

class OptionMatrix extends StatefulWidget {
  const OptionMatrix({super.key, required this.owned});

  final List<String> owned;

  @override
  State<OptionMatrix> createState() => _OptionMatrixState();
}

class _OptionMatrixState extends State<OptionMatrix> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final ownedSet = widget.owned.toSet();
    final total = carOptions.length;
    final ownedItems = carOptions.where((o) => ownedSet.contains(o.key)).toList();
    final ownedCount = ownedItems.length;

    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: const [
                  Icon(Icons.auto_awesome, color: AppColors.gold, size: 16),
                  SizedBox(width: 6),
                  Text(
                    '보유 옵션',
                    style: TextStyle(
                      color: AppColors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              RichText(
                text: TextSpan(
                  text: '$ownedCount',
                  style: const TextStyle(
                    color: AppColors.gold,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                  children: [
                    TextSpan(
                      text: ' / $total',
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (!_expanded)
            ownedItems.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 6),
                    child: Text(
                      '등록된 보유 옵션이 없습니다',
                      style: TextStyle(color: AppColors.muted, fontSize: 12),
                    ),
                  )
                : Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: ownedItems
                        .map((o) => _OptionPill(
                              option: o,
                              active: true,
                              onTap: () => _openOption(o, true),
                            ))
                        .toList(),
                  )
          else
            ...categoryOrder.map((cat) {
              final items = carOptions.where((o) => o.category == cat).toList();
              if (items.isEmpty) return const SizedBox.shrink();
              final catOwned = items.where((o) => ownedSet.contains(o.key)).length;
              return Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          categoryLabel[cat]!,
                          style: const TextStyle(
                            color: AppColors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          '$catOwned/${items.length}',
                          style: const TextStyle(
                            color: AppColors.muted,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: items
                          .map((o) => _OptionPill(
                                option: o,
                                active: ownedSet.contains(o.key),
                                onTap: () =>
                                    _openOption(o, ownedSet.contains(o.key)),
                              ))
                          .toList(),
                    ),
                  ],
                ),
              );
            }),
          const SizedBox(height: 14),
          GestureDetector(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _expanded ? '접기' : '전체 옵션 보기 ($total개)',
                    style: const TextStyle(
                      color: AppColors.gold,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    size: 14,
                    color: AppColors.gold,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            const SizedBox(height: 10),
            const Text(
              '※ 골드는 보유 · 회색은 미보유',
              style: TextStyle(color: AppColors.muted, fontSize: 10),
            ),
          ],
        ],
      ),
    );
  }

  void _openOption(CarOption option, bool owned) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => _OptionDetailSheet(option: option, owned: owned),
    );
  }
}

class _OptionPill extends StatelessWidget {
  const _OptionPill({
    required this.option,
    required this.active,
    required this.onTap,
  });

  final CarOption option;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fg = active ? AppColors.gold : AppColors.muted;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
        decoration: BoxDecoration(
          color: active
              ? AppColors.gold.withValues(alpha: 0.15)
              : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: active
                ? AppColors.gold.withValues(alpha: 0.5)
                : Colors.white.withValues(alpha: 0.1),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(option.icon, size: 11, color: fg),
            if (active) ...[
              const SizedBox(width: 2),
              const Icon(Icons.check, size: 11, color: AppColors.gold),
            ],
            const SizedBox(width: 4),
            Text(
              option.label,
              style: TextStyle(
                color: fg,
                fontSize: 11,
                fontWeight: active ? FontWeight.w800 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OptionDetailSheet extends StatelessWidget {
  const _OptionDetailSheet({required this.option, required this.owned});
  final CarOption option;
  final bool owned;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF0E1117),
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      padding: EdgeInsets.fromLTRB(
        24,
        14,
        24,
        MediaQuery.paddingOf(context).bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: 18),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: AppColors.gold.withValues(alpha: 0.18),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(option.icon, size: 28, color: AppColors.gold),
          ),
          const SizedBox(height: 14),
          Text(
            option.label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
              color: owned
                  ? AppColors.gold.withValues(alpha: 0.15)
                  : Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: owned
                    ? AppColors.gold.withValues(alpha: 0.4)
                    : Colors.white.withValues(alpha: 0.1),
              ),
            ),
            child: Text(
              owned ? '이 차량 보유' : '미보유',
              style: TextStyle(
                color: owned ? AppColors.gold : AppColors.muted,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            option.description,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 13.5,
              height: 1.55,
            ),
          ),
          const SizedBox(height: 26),
          OutlineGoldButton(
            label: '닫기',
            expand: true,
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
}
