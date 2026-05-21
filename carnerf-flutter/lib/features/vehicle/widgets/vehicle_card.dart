import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../../core/models/listing.dart';
import '../../../core/models/vehicle.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/utils/url.dart';
import '../../../shared/formatters/krw.dart';
import '../../../shared/widgets/krw_text.dart';

class VehicleCard extends StatelessWidget {
  const VehicleCard({
    super.key,
    required this.listing,
    this.matchScore,
    this.onPress,
  });

  final Listing listing;
  final double? matchScore;
  final VoidCallback? onPress;

  @override
  Widget build(BuildContext context) {
    final v = listing.vehicle;
    final thumb = absUrl(v?.thumbnailUrl);
    final has3d = v?.model3dStatus == Model3DStatus.ready;

    return Material(
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
              _Thumb(thumbUrl: thumb, has3d: has3d, matchScore: matchScore),
              Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      listing.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (v != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        '${v.year} · ${formatMileageKm(v.mileage)} · ${v.fuelType} · ${v.region ?? '-'}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 11.5,
                        ),
                      ),
                    ],
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        KrwText.manwon(listing.price, size: 19),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.star, size: 12, color: AppColors.gold),
                            const SizedBox(width: 3),
                            Text(
                              '조회 ${listing.viewCount}',
                              style: const TextStyle(
                                color: AppColors.muted,
                                fontSize: 11,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
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
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({
    required this.thumbUrl,
    required this.has3d,
    this.matchScore,
  });
  final String? thumbUrl;
  final bool has3d;
  final double? matchScore;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
          child: SizedBox(
            height: 160,
            width: double.infinity,
            child: thumbUrl == null
                ? Container(
                    color: const Color(0xFF1A1A1A),
                    alignment: Alignment.center,
                    child: const Icon(Icons.view_in_ar, size: 56, color: AppColors.gold),
                  )
                : CachedNetworkImage(
                    imageUrl: thumbUrl!,
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
          child: Row(
            children: [
              if (has3d)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.7),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.view_in_ar, size: 12, color: AppColors.gold),
                      SizedBox(width: 4),
                      Text(
                        '3D',
                        style: TextStyle(
                          color: AppColors.gold,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              if (matchScore != null) ...[
                if (has3d) const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.gold,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.auto_awesome, size: 12, color: AppColors.black),
                      const SizedBox(width: 3),
                      Text(
                        '매칭 ${matchScore!.round()}%',
                        style: const TextStyle(
                          color: AppColors.black,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        Positioned(
          top: 10,
          right: 10,
          child: Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.7),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.favorite_border, color: AppColors.white, size: 16),
          ),
        ),
      ],
    );
  }
}
