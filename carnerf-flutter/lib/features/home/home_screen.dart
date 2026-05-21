import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/week.dart';
import '../../shared/widgets/error_view.dart';
import '../../shared/widgets/loading_shimmer.dart';
import '../vehicle/widgets/vehicle_card.dart';
import 'providers/age_recommend_provider.dart';
import 'providers/weekly_specials_provider.dart';
import 'widgets/special_deal_card.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.black,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.only(bottom: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: const [
              _TopBar(),
              SizedBox(height: 8),
              _HeroCard(),
              SizedBox(height: 20),
              _FeatureChips(),
              SizedBox(height: 28),
              _WeeklySpecialsSection(),
              SizedBox(height: 28),
              _AgeRecommendSection(),
              SizedBox(height: 32),
              _HowItWorksSection(),
            ],
          ),
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 16, 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: AppColors.gold,
                  borderRadius: BorderRadius.circular(6),
                ),
                alignment: Alignment.center,
                child: const Text(
                  'C',
                  style: TextStyle(
                    color: AppColors.black,
                    fontWeight: FontWeight.w900,
                    fontSize: 14,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              const Text(
                'CarNeRF',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.notifications_outlined, color: AppColors.white),
          ),
        ],
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => context.go('/listings'),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFF0E1117),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'CARNERF · LUXURY 3D',
                style: TextStyle(
                  color: AppColors.gold,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 2.5,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                '영상 한 번에\n3D 중고차를 만나다',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                '전용 RAG 기반 AI 요약 · 결함 탐지 · 시세 예측까지\n한 화면에서.',
                style: TextStyle(
                  color: AppColors.muted,
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
                decoration: BoxDecoration(
                  color: AppColors.gold,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '매물 둘러보기',
                      style: TextStyle(
                        color: AppColors.black,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    SizedBox(width: 6),
                    Icon(Icons.arrow_forward, size: 16, color: AppColors.black),
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

class _FeatureChips extends StatelessWidget {
  const _FeatureChips();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: const [
          Expanded(child: _FeatureChip(icon: Icons.view_in_ar_outlined, label: '3D 뷰어')),
          SizedBox(width: 12),
          Expanded(child: _FeatureChip(icon: Icons.shield_outlined, label: 'AI 결함')),
          SizedBox(width: 12),
          Expanded(child: _FeatureChip(icon: Icons.trending_up, label: '시세 예측')),
        ],
      ),
    );
  }
}

class _FeatureChip extends StatelessWidget {
  const _FeatureChip({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1117),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
      ),
      child: Column(
        children: [
          Icon(icon, color: AppColors.gold, size: 22),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _WeeklySpecialsSection extends ConsumerStatefulWidget {
  const _WeeklySpecialsSection();

  @override
  ConsumerState<_WeeklySpecialsSection> createState() => _WeeklySpecialsSectionState();
}

class _WeeklySpecialsSectionState extends ConsumerState<_WeeklySpecialsSection> {
  CountdownParts _remain = timeToNextMondayKst();
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => setState(() => _remain = timeToNextMondayKst()),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String _two(int n) => n.toString().padLeft(2, '0');

  @override
  Widget build(BuildContext context) {
    final hms = '${_two(_remain.hours)}:${_two(_remain.minutes)}:${_two(_remain.seconds)}';
    final label = _remain.days > 0 ? '${_remain.days}일 $hms' : hms;
    final asyncSpecials = ref.watch(weeklySpecialsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            children: [
              const Icon(Icons.local_fire_department, color: AppColors.gold, size: 20),
              const SizedBox(width: 6),
              const Text(
                '이번 주 특가',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppColors.gold.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
                ),
                child: Text(
                  label,
                  style: const TextStyle(
                    color: AppColors.gold,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 20),
          child: Text(
            '매주 월요일 0시 새 특가로 교체',
            style: TextStyle(color: AppColors.muted, fontSize: 12),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 248,
          child: asyncSpecials.when(
            data: (list) {
              if (list.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  child: Text(
                    '이번 주 특가가 준비 중입니다',
                    style: TextStyle(color: AppColors.muted),
                  ),
                );
              }
              return ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                scrollDirection: Axis.horizontal,
                itemCount: list.length,
                separatorBuilder: (_, _) => const SizedBox(width: 12),
                itemBuilder: (_, i) {
                  final it = list[i];
                  return SpecialDealCard(
                    item: it,
                    onPress: () => context.push('/vehicle/${it.listing.id}'),
                  );
                },
              );
            },
            loading: () => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: List.generate(2, (i) => Padding(
                  padding: EdgeInsets.only(right: i == 0 ? 12 : 0),
                  child: const LoadingShimmer(width: 280, height: 220, radius: 16),
                )),
              ),
            ),
            error: (e, _) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: ErrorView(
                message: '특가를 불러오지 못했습니다',
                onRetry: () => ref.invalidate(weeklySpecialsProvider),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _AgeRecommendSection extends ConsumerStatefulWidget {
  const _AgeRecommendSection();

  @override
  ConsumerState<_AgeRecommendSection> createState() => _AgeRecommendSectionState();
}

class _AgeRecommendSectionState extends ConsumerState<_AgeRecommendSection> {
  AgeGroup _group = AgeGroup.thirties;

  @override
  Widget build(BuildContext context) {
    final asyncList = ref.watch(ageRecommendProvider(_group));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '연령대별 인기 차량',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                ),
              ),
              GestureDetector(
                onTap: () => context.go('/listings'),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '전체보기',
                      style: TextStyle(
                        color: AppColors.gold,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    SizedBox(width: 2),
                    Icon(Icons.arrow_forward, size: 12, color: AppColors.gold),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 20),
          child: Text(
            '또래가 가장 많이 찾은 매물',
            style: TextStyle(color: AppColors.muted, fontSize: 12),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 36,
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            scrollDirection: Axis.horizontal,
            itemCount: AgeGroup.values.length,
            separatorBuilder: (_, _) => const SizedBox(width: 8),
            itemBuilder: (_, i) {
              final g = AgeGroup.values[i];
              final selected = g == _group;
              return GestureDetector(
                onTap: () => setState(() => _group = g),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: selected ? AppColors.gold.withValues(alpha: 0.12) : AppColors.surfaceAlt,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: selected ? AppColors.gold : AppColors.border),
                  ),
                  child: Text(
                    g.label,
                    style: TextStyle(
                      color: selected ? AppColors.gold : AppColors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 290,
          child: asyncList.when(
            data: (list) {
              if (list.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    '해당 연령대 추천 매물이 없습니다',
                    style: TextStyle(color: AppColors.muted),
                  ),
                );
              }
              return ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                scrollDirection: Axis.horizontal,
                itemCount: list.length,
                separatorBuilder: (_, _) => const SizedBox(width: 12),
                itemBuilder: (_, i) {
                  final l = list[i];
                  return SizedBox(
                    width: 280,
                    child: Stack(
                      children: [
                        VehicleCard(
                          listing: l,
                          onPress: () => context.push('/vehicle/${l.id}'),
                        ),
                        Positioned(
                          top: 10,
                          left: 10,
                          child: IgnorePointer(
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppColors.gold,
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                '${_group.label} 추천',
                                style: const TextStyle(
                                  color: AppColors.black,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              );
            },
            loading: () => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: List.generate(2, (i) => Padding(
                  padding: EdgeInsets.only(right: i == 0 ? 12 : 0),
                  child: const LoadingShimmer(width: 280, height: 260, radius: 16),
                )),
              ),
            ),
            error: (e, _) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: ErrorView(
                message: '추천 매물을 불러오지 못했습니다',
                onRetry: () => ref.invalidate(ageRecommendProvider(_group)),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _HowItWorksSection extends StatelessWidget {
  const _HowItWorksSection();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'CarNeRF 작동 방식',
            style: TextStyle(
              color: AppColors.white,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF0E1117),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
            ),
            child: Column(
              children: [
                _Step(n: '1', title: '영상 촬영', desc: '차 한 바퀴 30~60초 영상'),
                _Divider(),
                _Step(n: '2', title: '자동 3D 모델링', desc: 'COLMAP → Gaussian Splatting'),
                _Divider(),
                _Step(n: '3', title: 'AI 분석', desc: '결함 탐지 · 시세 예측 · RAG 요약'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.n, required this.title, required this.desc});
  final String n;
  final String title;
  final String desc;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: const BoxDecoration(
            color: AppColors.gold,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Text(
            n,
            style: const TextStyle(
              color: AppColors.black,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: AppColors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                desc,
                style: const TextStyle(
                  color: AppColors.muted,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Divider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 1,
      margin: const EdgeInsets.symmetric(vertical: 14),
      color: Colors.white.withValues(alpha: 0.05),
    );
  }
}
