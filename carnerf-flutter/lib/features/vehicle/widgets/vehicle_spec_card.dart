import 'package:flutter/material.dart';

import '../../../core/models/vehicle.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/formatters/dates.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/dark_card.dart';

const Map<VehicleBodyType, String> _bodyTypeLabel = {
  VehicleBodyType.sedan: '세단',
  VehicleBodyType.suv: 'SUV',
  VehicleBodyType.hatchback: '해치백',
  VehicleBodyType.coupe: '쿠페',
  VehicleBodyType.wagon: '왜건',
};

const Map<VehicleDriveType, String> _driveTypeLabel = {
  VehicleDriveType.twoWd: '2WD',
  VehicleDriveType.fourWd: '4WD',
  VehicleDriveType.awd: 'AWD',
};

class VehicleSpecCard extends StatelessWidget {
  const VehicleSpecCard({super.key, required this.vehicle});

  final Vehicle vehicle;

  @override
  Widget build(BuildContext context) {
    final v = vehicle;
    final accident = v.accidentCount ?? 0;
    final flood = v.floodHistory == true;
    final ownerChange = v.ownerChangeCount ?? 0;

    final rows = <({String label, String? value})>[
      (label: '브랜드', value: v.brand),
      (label: '모델', value: '${v.model}${v.trim != null ? ' ${v.trim}' : ''}'),
      (label: '연식', value: '${v.year}년'),
      (label: '차종', value: v.bodyType != null ? _bodyTypeLabel[v.bodyType] : null),
      (label: '연료', value: v.fuelType),
      (label: '변속기', value: v.transmission),
      (label: '구동방식', value: v.driveType != null ? _driveTypeLabel[v.driveType] : null),
      (label: '배기량', value: v.engineCc != null ? '${formatKrw(v.engineCc!)}cc' : null),
      (label: '주행거리', value: formatMileageKm(v.mileage)),
      (label: '색상', value: v.color),
      (label: '승차정원', value: v.seats != null ? '${v.seats}인승' : null),
      (label: '차량번호', value: v.plateNumberMasked),
      (label: 'VIN', value: v.vinLast4 != null ? '**** **** ***${v.vinLast4}' : null),
      (label: '최초 등록일', value: v.firstRegisteredAt != null ? formatYmd(v.firstRegisteredAt!) : null),
      (label: '성능·상태 점검일', value: v.inspectionDate != null ? formatYmd(v.inspectionDate!) : null),
      (label: '지역', value: v.region),
    ].where((r) => r.value != null && r.value!.isNotEmpty).toList();

    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.info_outline, color: AppColors.gold, size: 16),
              SizedBox(width: 6),
              Text(
                '차량 정보',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _HistoryBadge(
                icon: accident > 0 ? Icons.warning_amber : Icons.verified_user,
                label: accident > 0 ? '사고 $accident회' : '무사고',
                danger: accident > 0,
              ),
              _HistoryBadge(
                icon: Icons.water_drop_outlined,
                label: flood ? '침수 이력' : '침수無',
                danger: flood,
              ),
              _HistoryBadge(
                icon: Icons.group_outlined,
                label: ownerChange == 0
                    ? '소유자 1명'
                    : '소유자 ${ownerChange + 1}명',
                danger: false,
              ),
            ],
          ),
          const SizedBox(height: 16),
          for (final r in rows) _SpecRow(label: r.label, value: r.value!),
        ],
      ),
    );
  }
}

class _SpecRow extends StatelessWidget {
  const _SpecRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 92,
            child: Text(
              label,
              style: const TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: AppColors.white,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryBadge extends StatelessWidget {
  const _HistoryBadge({
    required this.icon,
    required this.label,
    required this.danger,
  });

  final IconData icon;
  final String label;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    const dangerColor = Color(0xFFEF4444);
    final color = danger ? dangerColor : AppColors.gold;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
