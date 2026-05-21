import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers/auth_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters/krw.dart';
import 'providers/mypage_providers.dart';

class MyPageScreen extends ConsumerWidget {
  const MyPageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.asData?.value.user;
    final isAuthed = user != null;
    final balance =
        isAuthed ? ref.watch(pointsBalanceProvider).asData?.value : null;
    final myListings =
        isAuthed ? ref.watch(myListingsProvider).asData?.value : null;
    final wishlist =
        isAuthed ? ref.watch(myWishlistProvider).asData?.value : null;

    return Scaffold(
      backgroundColor: AppColors.black,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.only(bottom: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 12, 20, 20),
                child: Text(
                  '마이',
                  style: TextStyle(
                    color: AppColors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              _ProfileCard(
                username: user?.username ?? '게스트',
                subtitle: user?.email ?? '로그인하고 모든 기능을 사용해 보세요',
                isAuthed: isAuthed,
                onLogin: () => context.push('/login'),
                onLogout: () => ref.read(authProvider.notifier).logout(),
              ),
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Expanded(
                      child: _StatCard(
                        label: '포인트',
                        value: '${formatKrw(balance ?? 0)} P',
                        onTap: () => context.push('/points'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _StatCard(
                        label: '찜한 매물',
                        value: '${wishlist?.length ?? 0}',
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _StatCard(
                        label: '내 매물',
                        value: '${myListings?.length ?? 0}',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 22),
              _MenuList(
                rows: [
                  _MenuItem(icon: Icons.favorite_outline, label: '찜한 매물'),
                  _MenuItem(icon: Icons.receipt_long_outlined, label: '거래 내역'),
                  _MenuItem(
                    icon: Icons.monetization_on_outlined,
                    label: '포인트 충전/사용',
                    onTap: () => context.push('/points'),
                  ),
                  _MenuItem(icon: Icons.verified_user_outlined, label: '판매자 인증'),
                  _MenuItem(icon: Icons.star_outline, label: '내 리뷰'),
                  _MenuItem(icon: Icons.settings_outlined, label: '설정'),
                ],
              ),
              const SizedBox(height: 14),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: GestureDetector(
                  onTap: () => context.push('/compare'),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0E1117),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                    ),
                    child: Row(
                      children: const [
                        Expanded(
                          child: Text(
                            '차량 비교하기 (최대 4대)',
                            style: TextStyle(
                              color: AppColors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        Icon(Icons.chevron_right, color: AppColors.muted, size: 18),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({
    required this.username,
    required this.subtitle,
    required this.isAuthed,
    required this.onLogin,
    required this.onLogout,
  });

  final String username;
  final String subtitle;
  final bool isAuthed;
  final VoidCallback onLogin;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: const Color(0xFF0E1117),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
        ),
        child: Row(
          children: [
            Container(
              width: 54,
              height: 54,
              decoration: const BoxDecoration(
                color: AppColors.gold,
                shape: BoxShape.circle,
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.person, size: 28, color: AppColors.black),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    username,
                    style: const TextStyle(
                      color: AppColors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(color: AppColors.muted, fontSize: 11.5),
                  ),
                ],
              ),
            ),
            if (isAuthed)
              GestureDetector(
                onTap: onLogout,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.logout, size: 14, color: AppColors.muted),
                ),
              )
            else
              GestureDetector(
                onTap: onLogin,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppColors.gold,
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: const Text(
                    '로그인',
                    style: TextStyle(
                      color: AppColors.black,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, this.onTap});

  final String label;
  final String value;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            color: const Color(0xFF0E1117),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
          ),
          child: Column(
            children: [
              Text(
                value,
                style: const TextStyle(
                  color: AppColors.gold,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: const TextStyle(color: AppColors.muted, fontSize: 11),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MenuItem {
  const _MenuItem({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
}

class _MenuList extends StatelessWidget {
  const _MenuList({required this.rows});
  final List<_MenuItem> rows;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF0E1117),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
        ),
        child: Column(
          children: [
            for (var i = 0; i < rows.length; i++)
              _MenuRow(item: rows[i], showDivider: i < rows.length - 1),
          ],
        ),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({required this.item, required this.showDivider});
  final _MenuItem item;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: item.onTap,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
              child: Row(
                children: [
                  Icon(item.icon, color: AppColors.gold, size: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      item.label,
                      style: const TextStyle(
                        color: AppColors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: AppColors.muted, size: 18),
                ],
              ),
            ),
            if (showDivider)
              Container(
                height: 1,
                margin: const EdgeInsets.symmetric(horizontal: 18),
                color: Colors.white.withValues(alpha: 0.05),
              ),
          ],
        ),
      ),
    );
  }
}
