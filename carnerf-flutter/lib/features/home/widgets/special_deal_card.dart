import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/utils/url.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/krw_text.dart';
import '../providers/weekly_specials_provider.dart';

class SpecialDealCard extends StatelessWidget {
  const SpecialDealCard({super.key, required this.item, this.onPress});

  final SpecialListing item;
  final VoidCallback? onPress;

  @override
  Widget build(BuildContext context) {
    final v = item.listing.vehicle;
    final thumb = absUrl(v?.thumbnailUrl);

    return SizedBox(
      width: 280,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onPress,
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFF0E1117),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _Thumb(url: thumb, pct: item.discountPercent),
                Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.listing.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      if (v != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          '${v.year} · ${formatMileageKm(v.mileage)} · ${v.fuelType}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: AppColors.muted,
                            fontSize: 11,
                          ),
                        ),
                      ],
                      const SizedBox(height: 10),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${formatKrw(item.originalPrice)}만',
                                style: const TextStyle(
                                  color: AppColors.muted,
                                  fontSize: 12,
                                  decoration: TextDecoration.lineThrough,
                                ),
                              ),
                              KrwText.manwon(item.specialPrice, size: 19),
                            ],
                          ),
                          Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.star, size: 12, color: AppColors.gold),
                                const SizedBox(width: 3),
                                Text(
                                  '조회 ${item.listing.viewCount}',
                                  style: const TextStyle(
                                    color: AppColors.muted,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.url, required this.pct});
  final String? url;
  final int pct;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
          child: SizedBox(
            height: 140,
            width: double.infinity,
            child: url == null
                ? Container(
                    color: const Color(0xFF1A1A1A),
                    alignment: Alignment.center,
                    child: const Icon(Icons.view_in_ar, size: 48, color: AppColors.gold),
                  )
                : CachedNetworkImage(
                    imageUrl: url!,
                    fit: BoxFit.cover,
                    placeholder: (_, _) => Container(color: const Color(0xFF1A1A1A)),
                    errorWidget: (_, _, _) => Container(
                      color: const Color(0xFF1A1A1A),
                      alignment: Alignment.center,
                      child: const Icon(Icons.broken_image, color: AppColors.muted),
                    ),
                  ),
          ),
        ),
        Positioned(
          top: 10,
          left: 10,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.gold,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.local_fire_department, size: 12, color: AppColors.black),
                const SizedBox(width: 3),
                Text(
                  '-$pct%',
                  style: const TextStyle(
                    color: AppColors.black,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ),
        Positioned(
          top: 10,
          right: 10,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
            ),
            child: const Text(
              '이번 주 특가',
              style: TextStyle(
                color: AppColors.gold,
                fontSize: 10,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
