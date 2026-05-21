import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/models/vehicle.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/insurer_links.dart';
import '../../../core/utils/purchase_cost.dart';

class InsurerDeepLinks extends StatelessWidget {
  const InsurerDeepLinks({
    super.key,
    this.vehicle,
    this.age,
    this.region,
  });

  final Vehicle? vehicle;
  final int? age;
  final String? region;

  @override
  Widget build(BuildContext context) {
    final resolvedRegion = region ?? normalizeRegion(vehicle?.region);

    Future<void> open(InsurerEntry entry) async {
      final url = buildInsurerUrl(
        entry,
        brand: vehicle?.brand,
        model: vehicle?.model,
        year: vehicle?.year,
        age: age,
        region: resolvedRegion,
      );
      final uri = Uri.parse(url);
      try {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } catch (e) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppColors.surface,
            content: Text(
              '이동 실패: $e',
              style: const TextStyle(color: AppColors.gold),
            ),
          ),
        );
      }
    }

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.verified_user_outlined, size: 15, color: AppColors.gold),
              SizedBox(width: 6),
              Text(
                '정확한 견적 받기',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            '보험사 다이렉트로 이동합니다. 차종·연식이 자동으로 전달돼요.',
            style: TextStyle(color: AppColors.muted, fontSize: 10.5),
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, c) {
              final tileWidth = (c.maxWidth - 8) / 2;
              return Wrap(
                spacing: 8,
                runSpacing: 8,
                children: insurers
                    .map((i) => SizedBox(
                          width: tileWidth,
                          child: _InsurerTile(entry: i, onTap: () => open(i)),
                        ))
                    .toList(),
              );
            },
          ),
          const SizedBox(height: 12),
          const Text(
            '외부 사이트로 이동합니다. CarNeRF는 견적/계약 주체가 아니며 일부 보험사는 차량정보 자동입력을 지원하지 않을 수 있어요.',
            style: TextStyle(color: AppColors.muted, fontSize: 10, height: 1.5),
          ),
        ],
      ),
    );
  }
}

class _InsurerTile extends StatelessWidget {
  const _InsurerTile({required this.entry, required this.onTap});
  final InsurerEntry entry;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
          ),
          child: Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: AppColors.gold.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Text(
                  entry.short,
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
                  entry.name,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const Icon(Icons.open_in_new, size: 12, color: AppColors.muted),
            ],
          ),
        ),
      ),
    );
  }
}
