import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../api/auth_api.dart';
import '../models/user.dart';

const _kUserKey = 'carnerf.user';

class AuthState {
  const AuthState({this.user, this.hydrated = false});

  final User? user;
  final bool hydrated;

  bool get isAuthenticated => user != null;

  AuthState copyWith({User? user, bool? hydrated, bool clearUser = false}) {
    return AuthState(
      user: clearUser ? null : (user ?? this.user),
      hydrated: hydrated ?? this.hydrated,
    );
  }
}

class AuthNotifier extends AsyncNotifier<AuthState> {
  @override
  Future<AuthState> build() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kUserKey);
    User? user;
    if (raw != null && raw.isNotEmpty) {
      try {
        user = User.fromJson(jsonDecode(raw) as Map<String, dynamic>);
      } catch (_) {
        await prefs.remove(_kUserKey);
      }
    }
    return AuthState(user: user, hydrated: true);
  }

  Future<void> login(String email, String password) async {
    final api = ref.read(authApiProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    final prefs = await SharedPreferences.getInstance();

    final res = await api.login(email: email, password: password);
    await tokenStore.save(res.accessToken);
    await prefs.setString(_kUserKey, jsonEncode(res.user.toJson()));
    state = AsyncData(AuthState(user: res.user, hydrated: true));
  }

  Future<void> register({
    required String email,
    required String username,
    required String password,
    String? phone,
  }) async {
    final api = ref.read(authApiProvider);
    await api.register(
      email: email,
      username: username,
      password: password,
      phone: phone,
    );
  }

  Future<void> logout() async {
    final api = ref.read(authApiProvider);
    final tokenStore = ref.read(tokenStoreProvider);
    final prefs = await SharedPreferences.getInstance();

    try {
      await api.logout();
    } catch (_) {}
    await tokenStore.clear();
    await prefs.remove(_kUserKey);
    state = const AsyncData(AuthState(hydrated: true));
  }
}

final authProvider =
    AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
