import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/listing.dart';
import '../models/user.dart';
import 'api_client.dart';

class LoginResponse {
  const LoginResponse({
    required this.accessToken,
    required this.tokenType,
    required this.user,
  });

  final String accessToken;
  final String tokenType;
  final User user;

  factory LoginResponse.fromJson(Map<String, dynamic> json) => LoginResponse(
        accessToken: json['access_token'] as String,
        tokenType: json['token_type'] as String? ?? 'bearer',
        user: User.fromJson(json['user'] as Map<String, dynamic>),
      );
}

class AuthApi {
  AuthApi(this._dio);
  final Dio _dio;

  Future<User> register({
    required String email,
    required String username,
    required String password,
    String? phone,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/auth/register/',
      data: {
        'email': email,
        'username': username,
        'password': password,
        'phone': ?phone,
      },
    );
    return User.fromJson(r.data!);
  }

  Future<LoginResponse> login({
    required String email,
    required String password,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/auth/login/',
      data: {'email': email, 'password': password},
    );
    return LoginResponse.fromJson(r.data!);
  }

  Future<void> logout() async {
    await _dio.post<dynamic>('/api/auth/logout/');
  }

  Future<User> updateProfile({String? username, String? phone, String? region}) async {
    final r = await _dio.put<Map<String, dynamic>>(
      '/api/auth/profile/',
      data: {
        'username': ?username,
        'phone': ?phone,
        'region': ?region,
      },
    );
    return User.fromJson(r.data!);
  }

  Future<List<Listing>> myListings() async {
    final r = await _dio.get<List<dynamic>>('/api/auth/my-listings/');
    return (r.data ?? const [])
        .cast<Map<String, dynamic>>()
        .map(Listing.fromJson)
        .toList();
  }

  Future<void> updateListingStatus(int id, ListingStatus status) async {
    final s = switch (status) {
      ListingStatus.active => 'active',
      ListingStatus.reserved => 'reserved',
      ListingStatus.sold => 'sold',
    };
    await _dio.put<dynamic>('/api/auth/listings/$id/status/', data: {'status': s});
  }

  Future<void> deleteListing(int id) async {
    await _dio.delete<dynamic>('/api/auth/listings/$id/');
  }
}

final authApiProvider = Provider<AuthApi>((ref) => AuthApi(ref.watch(apiClientProvider)));
