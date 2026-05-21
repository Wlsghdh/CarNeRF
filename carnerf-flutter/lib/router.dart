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
        GoRoute(path: '/', builder: (_, _) => const HomeScreen()),
        GoRoute(path: '/listings', builder: (_, _) => const ListingsScreen()),
        GoRoute(path: '/sell', builder: (_, _) => const SellScreen()),
        GoRoute(path: '/mypage', builder: (_, _) => const MyPageScreen()),
      ],
    ),
    GoRoute(
      path: '/vehicle/:id',
      builder: (_, state) => VehicleDetailScreen(id: state.pathParameters['id']!),
    ),
    GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
  ],
  errorBuilder: (_, state) => Scaffold(
    body: Center(child: Text('경로를 찾을 수 없습니다: ${state.uri}')),
  ),
);
