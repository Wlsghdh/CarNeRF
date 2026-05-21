import 'package:flutter/material.dart';

import '../../../core/constants/warranty.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/formatters/dates.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/dark_card.dart';

class _Remain {
  const _Remain({
    required this.daysLeft,
    required this.kmLeft,
    required this.isExpired,
    required this.endDate,
  });
  final int daysLeft;
  final int kmLeft;
  final bool isExpired;
  final DateTime endDate;
}

_Remain? _calcRemain(DateTime? start, int mileage, WarrantyTerm terms) {
  if (start == null) return null;
  final end = DateTime(start.year + terms.years, start.month, start.day);
  final now = DateTime.now();
  final daysLeft = end.difference(now).inDays;
  return _Remain(
    daysLeft: daysLeft < 0 ? 0 : daysLeft,
    kmLeft: (terms.km - mileage) < 0 ? 0 : (terms.km - mileage),
    isExpired: daysLeft <= 0 || (terms.km - mileage) <= 0,
    endDate: end,
  );
}

_Remain? _calcInspectionRemain(DateTime? start, int mileage) {
  if (start == null) return null;
  final end = start.add(Duration(days: inspectionWarranty.days));
  final now = DateTime.now();
  final daysLeft = end.difference(now).inDays;
  return _Remain(
    daysLeft: daysLeft < 0 ? 0 : daysLeft,
    kmLeft: inspectionWarranty.km,
    isExpired: daysLeft <= 0,
    endDate: end,
  );
}

class WarrantyCard extends StatelessWidget {
  const WarrantyCard({
    super.key,
    required this.brand,
    required this.firstRegisteredAt,
    required this.inspectionDate,
    required this.mileage,
  });

  final String brand;
  final DateTime? firstRegisteredAt;
  final DateTime? inspectionDate;
  final int mileage;

  @override
  Widget build(BuildContext context) {
    final terms = warrantyByBrand[brand];

    final general = terms != null
        ? _calcRemain(firstRegisteredAt, mileage, terms.general)
        : null;
    final powertrain = terms != null
        ? _calcRemain(firstRegisteredAt, mileage, terms.powertrain)
        : null;
    final rust = terms?.rust != null
        ? _calcRemain(firstRegisteredAt, mileage, terms!.rust!)
        : null;
    final inspection = _calcInspectionRemain(inspectionDate, mileage);

    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.verified_user_outlined, color: AppColors.gold, size: 16),
              SizedBox(width: 6),
              Text(
                'A/S 보증 정보',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (terms != null && firstRegisteredAt != null) ...[
            const Text(
              '제조사 신차 보증',
              style: TextStyle(
                color: AppColors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            if (general != null) _WarrantyRow(label: '일반 보증', remain: general),
            if (powertrain != null) _WarrantyRow(label: '동력계 보증', remain: powertrain),
            if (rust != null) _WarrantyRow(label: '부식 보증', remain: rust),
            const SizedBox(height: 12),
          ] else
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                terms != null
                    ? '최초 등록일 정보가 없어 신차 보증 잔여를 계산할 수 없습니다.'
                    : '$brand 브랜드의 보증 정보가 등록되어 있지 않습니다.',
                style: const TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ),
          if (inspection != null) ...[
            const Text(
              '성능·상태 점검 보증',
              style: TextStyle(
                color: AppColors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            _InfoRow(
              label: '점검일',
              value: inspectionDate != null ? formatYmd(inspectionDate!) : '-',
            ),
            _InfoRow(
              label: '보증범위',
              value:
                  '${inspectionWarranty.days}일 또는 ${formatKrw(inspectionWarranty.km)}km 이내 발견된 결함 무상 수리',
              valueColor: AppColors.white,
              wrap: true,
            ),
            _WarrantyRow(label: '잔여', remain: inspection),
            const SizedBox(height: 6),
          ],
          const SizedBox(height: 6),
          const Text(
            '※ 보증은 차량 최초 등록일 기준 자동 계산된 예상치입니다. 정확한 보증 범위는 제조사 정책에 따라 상이할 수 있으며, 제조사 보증과 성능·상태 점검 보증은 별도로 운영됩니다.',
            style: TextStyle(
              color: AppColors.muted,
              fontSize: 10.5,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.label,
    required this.value,
    this.valueColor = AppColors.muted,
    this.wrap = false,
  });

  final String label;
  final String value;
  final Color valueColor;
  final bool wrap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 76,
            child: Text(
              label,
              style: const TextStyle(color: AppColors.muted, fontSize: 11),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: valueColor,
                fontSize: 11,
                fontWeight: wrap ? FontWeight.w500 : FontWeight.w700,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _WarrantyRow extends StatelessWidget {
  const _WarrantyRow({required this.label, required this.remain});
  final String label;
  final _Remain remain;

  @override
  Widget build(BuildContext context) {
    final years = remain.daysLeft ~/ 365;
    final months = (remain.daysLeft % 365) ~/ 30;
    final remainText =
        years > 0 ? '$years년 $months개월' : '${remain.daysLeft}일';
    final kmText = remain.kmLeft >= 999000 ? '무제한' : '${formatKrw(remain.kmLeft)}km';

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(
            width: 76,
            child: Text(
              label,
              style: const TextStyle(color: AppColors.muted, fontSize: 11),
            ),
          ),
          if (remain.isExpired)
            const Text(
              '만료됨',
              style: TextStyle(
                color: AppColors.muted,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            )
          else ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.gold.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
              ),
              child: Text(
                '$remainText · $kmText',
                style: const TextStyle(
                  color: AppColors.gold,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '~${formatYmd(remain.endDate)}까지',
                style: const TextStyle(color: AppColors.muted, fontSize: 10),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
