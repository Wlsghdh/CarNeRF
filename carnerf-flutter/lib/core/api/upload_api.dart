import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

class ImageUploadResult {
  const ImageUploadResult({required this.urls, required this.thumbnails});
  final List<String> urls;
  final List<String> thumbnails;
}

class UploadApi {
  UploadApi(this._dio);
  final Dio _dio;

  Future<ImageUploadResult> images(List<String> filePaths) async {
    final files = await Future.wait(
      filePaths.map((p) => MultipartFile.fromFile(p)),
    );
    final form = FormData();
    for (final f in files) {
      form.files.add(MapEntry('files', f));
    }
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/upload/images/',
      data: form,
      options: Options(
        headers: {'Content-Type': 'multipart/form-data'},
        sendTimeout: const Duration(seconds: 60),
      ),
    );
    return ImageUploadResult(
      urls: (r.data!['urls'] as List).cast<String>(),
      thumbnails: (r.data!['thumbnails'] as List).cast<String>(),
    );
  }
}

final uploadApiProvider =
    Provider<UploadApi>((ref) => UploadApi(ref.watch(apiClientProvider)));
