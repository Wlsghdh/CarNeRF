import 'package:flutter/material.dart';

import '../../../core/models/vehicle.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/purchase_cost.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/dark_card.dart';
import 'insurer_deep_links.dart';

class PurchaseCostCard extends StatefulWidget {
  const PurchaseCostCard({
    super.key,
    required this.listingPrice,
    this.vehicle,
  });

  final int listingPrice;
  final Vehicle? vehicle;

  @override
  State<PurchaseCostCard> createState() => _PurchaseCostCardState();
}

class _PurchaseCostCardState extends State<PurchaseCostCard> {
  bool _discountBond = true;
  bool _expanded = true;
  bool _showInsurer = false;

  @override
  Widget build(BuildContext context) {
    final v = widget.vehicle;
    final fuel = normalizeFuel(v?.fuelType);
    final region = normalizeRegion(v?.region);
    final year = v?.year ?? DateTime.now().year;
    final engineCc = v?.engineCc;

    final cost = computePurchaseCost(
      PurchaseCostInput(
        priceManwon: widget.listingPrice,
        engineCc: engineCc,
        fuelType: fuel,
        year: year,
        region: region,
        discountBond: _discountBond,
      ),
    );

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
                  Icon(Icons.receipt_long_outlined, color: AppColors.gold, size: 16),
                  SizedBox(width: 6),
                  Text(
                    '총 구매 비용',
                    style: TextStyle(
                      color: AppColors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              GestureDetector(
                onTap: () => setState(() => _discountBond = !_discountBond),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                  decoration: BoxDecoration(
                    color: _discountBond
                        ? AppColors.gold.withValues(alpha: 0.15)
                        : Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: _discountBond
                          ? AppColors.gold.withValues(alpha: 0.4)
                          : Colors.white.withValues(alpha: 0.1),
                    ),
                  ),
                  child: Text(
                    '공채 즉시할인 ${_discountBond ? 'ON' : 'OFF'}',
                    style: TextStyle(
                      color: _discountBond ? AppColors.gold : AppColors.muted,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            '구매 시 일시금 (차량가 + 부대비용)',
            style: TextStyle(color: AppColors.muted, fontSize: 11),
          ),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                formatKrw(cost.totalPurchase.round()),
                style: const TextStyle(
                  color: AppColors.gold,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(left: 4, bottom: 4),
                child: Text(
                  '만원',
                  style: TextStyle(color: AppColors.muted, fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '차량가 ${formatKrw(cost.base.round())}만 + 부대 ${formatKrw(cost.subtotalTaxes.round())}만',
            style: const TextStyle(color: AppColors.white, fontSize: 11),
          ),
          GestureDetector(
            onTap: () => setState(() => _expanded = !_expanded),
            behavior: HitTestBehavior.opaque,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    '세부 내역',
                    style: TextStyle(
                      color: AppColors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Icon(
                    _expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    size: 16,
                    color: AppColors.muted,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  _Row(label: '차량가', amount: cost.base),
                  _Row(
                    label:
                        '취득세 (${acquisitionTaxLabel(engineCc: engineCc, fuelType: fuel)})',
                    amount: cost.acquisitionTax,
                    plus: true,
                  ),
                  if (_discountBond)
                    _Row(
                      label:
                          '공채 (${bondRateLabel(region)} · 즉시할인 $bondDiscountPercent%)',
                      amount: cost.bondDiscount,
                      plus: true,
                      sub:
                          '면가 ${formatKrw(cost.bondFace.round())}만 중 실부담',
                    )
                  else
                    _Row(
                      label: '공채 매입 (${bondRateLabel(region)})',
                      amount: cost.bondFace,
                      plus: true,
                      sub: '만기까지 보유 시 일부 회수',
                    ),
                  _Row(
                    label: '등록·번호판·인지',
                    amount: cost.registrationFee,
                    plus: true,
                  ),
                  Container(
                    height: 1,
                    margin: const EdgeInsets.symmetric(vertical: 8),
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                  _Row(label: '구매 시 일시금', amount: cost.totalPurchase, bold: true),
                ],
              ),
            ),
          GestureDetector(
            onTap: () => setState(() => _showInsurer = !_showInsurer),
            child: Container(
              margin: const EdgeInsets.only(top: 12),
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    _showInsurer ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    size: 13,
                    color: AppColors.gold,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _showInsurer ? '보험사 다이렉트 접기' : '전체보기 (정확한 견적 받기)',
                    style: const TextStyle(
                      color: AppColors.gold,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_showInsurer) InsurerDeepLinks(vehicle: v),
          const SizedBox(height: 12),
          const Text(
            '보험료는 보험사별 요율·운전자 조건에 따라 달라요. 정확한 금액은 위 다이렉트 견적을 확인해주세요.',
            style: TextStyle(color: AppColors.muted, fontSize: 10, height: 1.5),
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({
    required this.label,
    required this.amount,
    this.plus = false,
    this.bold = false,
    this.sub,
  });

  final String label;
  final num amount;
  final bool plus;
  final bool bold;
  final String? sub;

  @override
  Widget build(BuildContext context) {
    final amountColor = bold || plus ? AppColors.gold : AppColors.white;
    final sign = plus ? '+' : '';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    color: bold ? AppColors.white : AppColors.white.withValues(alpha: 0.85),
                    fontSize: 12,
                    fontWeight: bold ? FontWeight.w800 : FontWeight.w500,
                  ),
                ),
                if (sub != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      sub!,
                      style: const TextStyle(color: AppColors.muted, fontSize: 10),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '$sign${formatKrw(amount.round())}만',
            style: TextStyle(
              color: amountColor,
              fontSize: bold ? 14 : 12,
              fontWeight: bold ? FontWeight.w800 : FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
