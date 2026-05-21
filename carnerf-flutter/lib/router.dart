import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/api/api_client.dart';
import 'core/providers/auth_provider.dart';
import 'features/auth/login_screen.dart';
import 'features/compare/compare_screen.dart';
import 'features/home/home_screen.dart';
import 'features/listings/listings_screen.dart';
import 'features/mypage/mypage_screen.dart';
import 'features/points/points_screen.dart';
import 'features/sell/sell_screen.dart';
import 'features/shell/main_scaffold.dart';
import 'features/vehicle/vehicle_detail_screen.dart';
import 'features/viewer/viewer_screen.dart';

const _protectedPrefixes = <String>['/sell', '/mypage', '/points'];

class _AuthChangeNotifier extends ChangeNotifier {
  _AuthChangeNotifier(Ref ref) {
    ref.listen<AsyncValue<AuthState>>(
      authProvider,
      (_, _) => notifyListeners(),
    );
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final notifier = _AuthChangeNotifier(ref);

  ref.listen<UnauthorizedSignal>(
    unauthorizedSignalProvider,
    (_, signal) {
      signal.handler = () {
        ref.read(authProvider.notifier).logout();
      };
    },
    fireImmediately: true,
  );

  return GoRouter(
    initialLocation: '/',
    refreshListenable: notifier,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final hydrated = auth.asData?.value.hydrated ?? false;
      if (!hydrated) return null;
      final isAuthed = auth.asData?.value.isAuthenticated ?? false;
      final path = state.matchedLocation;
      final isProtected = _protectedPrefixes.any((p) => path.startsWith(p));
      if (isProtected && !isAuthed) {
        return '/login?next=${Uri.encodeComponent(path)}';
      }
      if (path == '/login' && isAuthed) return '/';
      return null;
    },
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
      GoRoute(
        path: '/viewer/:id',
        builder: (_, state) => ViewerScreen(id: state.pathParameters['id']!),
      ),
      GoRoute(path: '/points', builder: (_, _) => const PointsScreen()),
      GoRoute(path: '/compare', builder: (_, _) => const CompareScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
    ],
    errorBuilder: (_, state) => Scaffold(
      body: Center(child: Text('경로를 찾을 수 없습니다: ${state.uri}')),
    ),
  );
});
