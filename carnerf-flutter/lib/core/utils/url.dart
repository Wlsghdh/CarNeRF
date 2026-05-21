import '../config/env.dart';

String? absUrl(String? path) {
  if (path == null || path.isEmpty) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return '${Env.apiBaseUrl}$path';
}
