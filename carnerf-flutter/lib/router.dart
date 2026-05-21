import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';
import 'features/listings/listings_screen.dart';
import 'features/mypage/mypage_screen.dart';
import 'features/sell/sell_screen.dart';
import 'features/shell/main_scaffold.dart';
import 'features/vehicle/vehicle_detail_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    ShellRoute(
      builder: (context, state, child) => MainScaffold(child: child),
      routes: [
        GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
        GoRoute(path: '/listings', builder: (_, __) => const ListingsScreen()),
        GoRoute(path: '/sell', builder: (_, __) => const SellScreen()),
        GoRoute(path: '/mypage', builder: (_, __) => const MyPageScreen()),
      ],
    ),
    GoRoute(
      path: '/vehicle/:id',
      builder: (_, state) => VehicleDetailScreen(id: state.pathParameters['id']!),
    ),
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
  ],
  errorBuilder: (_, state) => Scaffold(
    body: Center(child: Text('경로를 찾을 수 없습니다: ${state.uri}')),
  ),
);
