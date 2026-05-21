import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/env.dart';

const _kTokenKey = 'carnerf_jwt';

final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});

class UnauthorizedSignal {
  void Function()? handler;
  void fire() => handler?.call();
}

final unauthorizedSignalProvider = Provider<UnauthorizedSignal>((ref) {
  return UnauthorizedSignal();
});

final apiClientProvider = Provider<Dio>((ref) {
  final storage = ref.watch(secureStorageProvider);
  final tokenStore = ref.watch(tokenStoreProvider);
  final unauthorized = ref.watch(unauthorizedSignalProvider);

  final dio = Dio(
    BaseOptions(
      baseUrl: Env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 20),
      headers: {'Accept': 'application/json'},
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await storage.read(key: _kTokenKey);
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        final method = options.method.toUpperCase();
        if (method == 'GET') {
          final path = options.path;
          if (!path.contains('?') && !path.endsWith('/')) {
            options.path = '$path/';
          }
        }
        handler.next(options);
      },
      onError: (e, handler) async {
        if (e.response?.statusCode == 401) {
          await tokenStore.clear();
          unauthorized.fire();
        }
        handler.next(e);
      },
    ),
  );

  return dio;
});

class TokenStore {
  TokenStore(this._storage);
  final FlutterSecureStorage _storage;

  Future<void> save(String token) => _storage.write(key: _kTokenKey, value: token);
  Future<String?> read() => _storage.read(key: _kTokenKey);
  Future<void> clear() => _storage.delete(key: _kTokenKey);
}

final tokenStoreProvider = Provider<TokenStore>((ref) {
  return TokenStore(ref.watch(secureStorageProvider));
});

String extractApiError(Object err) {
  if (err is DioException) {
    final data = err.response?.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
      final message = data['message'];
      if (message is String && message.isNotEmpty) return message;
    }
    return err.message ?? '네트워크 오류';
  }
  return err.toString();
}
