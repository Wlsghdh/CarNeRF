enum UserRole { buyer, seller }

UserRole _userRoleFromJson(String? raw) =>
    raw == 'seller' ? UserRole.seller : UserRole.buyer;

String _userRoleToJson(UserRole role) =>
    role == UserRole.seller ? 'seller' : 'buyer';

class User {
  const User({
    required this.id,
    required this.email,
    required this.username,
    this.phone,
    required this.role,
    required this.points,
    required this.isVerified,
    this.region,
    required this.createdAt,
  });

  final int id;
  final String email;
  final String username;
  final String? phone;
  final UserRole role;
  final int points;
  final bool isVerified;
  final String? region;
  final DateTime createdAt;

  factory User.fromJson(Map<String, dynamic> json) => User(
        id: json['id'] as int,
        email: json['email'] as String,
        username: json['username'] as String,
        phone: json['phone'] as String?,
        role: _userRoleFromJson(json['role'] as String?),
        points: (json['points'] as num?)?.toInt() ?? 0,
        isVerified: json['is_verified'] as bool? ?? false,
        region: json['region'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'username': username,
        if (phone != null) 'phone': phone,
        'role': _userRoleToJson(role),
        'points': points,
        'is_verified': isVerified,
        if (region != null) 'region': region,
        'created_at': createdAt.toIso8601String(),
      };
}
