import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models/listing.dart';
import '../../core/models/vehicle.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/url.dart';
import '../../shared/formatters/krw.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/widgets/gold_button.dart';
import '../../shared/widgets/krw_text.dart';
import 'providers/detail_providers.dart';
import 'widgets/option_matrix.dart';
import 'widgets/placeholder_section.dart';
import 'widgets/reviews_card.dart';
import 'widgets/section_title.dart';
import 'widgets/vehicle_spec_card.dart';
import 'widgets/warranty_card.dart';

class VehicleDetailScreen extends ConsumerWidget {
  const VehicleDetailScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listingId = int.tryParse(id);
    if (listingId == null) {
      return const Scaffold(
        backgroundColor: AppColors.black,
        body: Center(
          child: Text(
            '잘못된 매물 ID입니다',
            style: TextStyle(color: AppColors.muted),
          ),
        ),
      );
    }

    final async = ref.watch(listingDetailProvider(listingId));

    return Scaffold(
      backgroundColor: AppColors.black,
      body: async.when(
        loading: () => const _LoadingState(),
        error: (e, _) => Padding(
          padding: const EdgeInsets.only(top: 80),
          child: ErrorView(
            message: '매물을 불러오지 못했습니다',
            onRetry: () => ref.invalidate(listingDetailProvider(listingId)),
          ),
        ),
        data: (listing) => _DetailBody(listing: listing),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: SizedBox(
        width: 28,
        height: 28,
        child: CircularProgressIndicator(
          strokeWidth: 2.6,
          valueColor: AlwaysStoppedAnimation(AppColors.gold),
        ),
      ),
    );
  }
}

class _DetailBody extends ConsumerWidget {
  const _DetailBody({required this.listing});
  final Listing listing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final v = listing.vehicle;
    final vehicleId = v?.id ?? listing.vehicleId;

    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.only(bottom: 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _Hero(listing: listing, vehicleId: vehicleId),
              const SizedBox(height: 18),
              _Header(listing: listing),
              const SizedBox(height: 24),
              _Section(
                title: 'AI 분석',
                subtitle: '전용 RAG 기반 차량 요약',
                child: _AiSection(vehicleId: vehicleId),
              ),
              _Section(
                title: '구매 시 총비용',
                child: const PlaceholderSectionCard(
                  label: '등록세 · 취득세 · 보험료 합산 (Phase 3.4.4)',
                ),
              ),
              _Section(
                title: '옵션 정보',
                child: OptionMatrix(owned: v?.options ?? const []),
              ),
              if (v != null)
                _Section(
                  title: '차량 정보',
                  child: VehicleSpecCard(vehicle: v),
                ),
              _Section(
                title: '이 차량 시세',
                child: const PlaceholderSectionCard(
                  label: '12개월 실거래 + 예측 범위 (Phase 3.4.3)',
                  icon: Icons.show_chart,
                ),
              ),
              if (v != null)
                _Section(
                  title: 'A/S 보증',
                  child: WarrantyCard(
                    brand: v.brand,
                    firstRegisteredAt: v.firstRegisteredAt,
                    inspectionDate: v.inspectionDate,
                    mileage: v.mileage,
                  ),
                ),
              _Section(
                title: '구매자 후기',
                child: _ReviewsSection(vehicleId: vehicleId),
              ),
            ],
          ),
        ),
        const _BottomBar(),
      ],
    );
  }
}

class _Hero extends ConsumerWidget {
  const _Hero({required this.listing, required this.vehicleId});
  final Listing listing;
  final int vehicleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final v = listing.vehicle;
    final thumb = absUrl(v?.thumbnailUrl);
    final has3d = v?.model3dStatus == Model3DStatus.ready;
    final wished = ref.watch(wishlistCheckProvider(vehicleId)).asData?.value ?? false;

    return Stack(
      children: [
        SizedBox(
          height: 300,
          width: double.infinity,
          child: thumb == null
              ? Container(
                  color: const Color(0xFF0A0A0A),
                  alignment: Alignment.center,
                  child: const Icon(Icons.view_in_ar, size: 84, color: AppColors.gold),
                )
              : CachedNetworkImage(
                  imageUrl: thumb,
                  fit: BoxFit.cover,
                  placeholder: (_, _) => Container(color: const Color(0xFF0A0A0A)),
                  errorWidget: (_, _, _) => Container(
                    color: const Color(0xFF0A0A0A),
                    alignment: Alignment.center,
                    child: const Icon(Icons.broken_image, color: AppColors.muted, size: 64),
                  ),
                ),
        ),
        SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _CircleIcon(
                  icon: Icons.chevron_left,
                  onTap: () =>
                      context.canPop() ? context.pop() : context.go('/listings'),
                ),
                Row(
                  children: [
                    _CircleIcon(
                      icon: wished ? Icons.favorite : Icons.favorite_border,
                      iconColor: wished ? AppColors.gold : AppColors.white,
                      onTap: () => toggleWishlist(ref, vehicleId),
                    ),
                    const SizedBox(width: 8),
                    _CircleIcon(icon: Icons.share_outlined, onTap: () {}),
                  ],
                ),
              ],
            ),
          ),
        ),
        if (has3d)
          Positioned(
            left: 16,
            right: 16,
            bottom: 14,
            child: GestureDetector(
              onTap: () => context.push('/viewer/$vehicleId'),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 13),
                decoration: BoxDecoration(
                  color: AppColors.gold,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.view_in_ar, size: 18, color: AppColors.black),
                    SizedBox(width: 8),
                    Text(
                      '3D 모델 보기',
                      style: TextStyle(
                        color: AppColors.black,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _CircleIcon extends StatelessWidget {
  const _CircleIcon({
    required this.icon,
    required this.onTap,
    this.iconColor = AppColors.white,
  });

  final IconData icon;
  final VoidCallback onTap;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: Colors.black.withValues(alpha: 0.6),
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(icon, size: 20, color: iconColor),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.listing});
  final Listing listing;

  @override
  Widget build(BuildContext context) {
    final v = listing.vehicle;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            listing.title,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 22,
              fontWeight: FontWeight.w800,
              height: 1.25,
            ),
          ),
          if (v != null) ...[
            const SizedBox(height: 6),
            Text(
              '${v.brand} ${v.model}${v.trim != null ? ' ${v.trim}' : ''} · ${v.year} · ${formatMileageKm(v.mileage)}',
              style: const TextStyle(color: AppColors.muted, fontSize: 13),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              KrwText.manwon(listing.price, size: 30),
              if (listing.isNegotiable) ...[
                const SizedBox(width: 10),
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      '네고 가능',
                      style: TextStyle(
                        color: AppColors.white,
                        fontSize: 10.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (listing.description != null && listing.description!.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              listing.description!,
              style: const TextStyle(
                color: AppColors.white,
                fontSize: 13,
                height: 1.6,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    this.subtitle,
    required this.child,
  });

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionTitle(title, subtitle: subtitle),
          child,
        ],
      ),
    );
  }
}

class _AiSection extends ConsumerWidget {
  const _AiSection({required this.vehicleId});
  final int vehicleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(vehicleSummaryProvider(vehicleId));
    return async.when(
      loading: () => const LoadingSectionCard(height: 80),
      error: (e, _) => const PlaceholderSectionCard(
        label: 'AI 요약을 불러오지 못했습니다',
        icon: Icons.error_outline,
      ),
      data: (s) => PlaceholderSectionCard(
        label: s.summary.isEmpty
            ? 'AI 요약 준비 중입니다 (Phase 3.4.2)'
            : '${s.summary.split('\n').first}  · Phase 3.4.2에서 풀 UI',
        icon: Icons.auto_awesome,
      ),
    );
  }
}

class _ReviewsSection extends ConsumerWidget {
  const _ReviewsSection({required this.vehicleId});
  final int vehicleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(vehicleReviewsProvider(vehicleId));
    return async.when(
      loading: () => const LoadingSectionCard(height: 80),
      error: (e, _) => const PlaceholderSectionCard(
        label: '후기를 불러오지 못했습니다',
        icon: Icons.error_outline,
      ),
      data: (page) => ReviewsCard(reviews: page.items),
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar();

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: 0,
      right: 0,
      bottom: 0,
      child: Container(
        padding: EdgeInsets.fromLTRB(
          20,
          12,
          20,
          MediaQuery.paddingOf(context).bottom + 16,
        ),
        decoration: const BoxDecoration(
          color: Color(0xFF0A0A0A),
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: GoldButton(
          label: '판매자 문의',
          icon: Icons.chat_bubble_outline,
          expand: true,
          onPressed: () {},
        ),
      ),
    );
  }
}
