import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

enum PipelineQuality { standard, hq, ultra }

String _qualityToParam(PipelineQuality q) {
  switch (q) {
    case PipelineQuality.standard:
      return 'standard';
    case PipelineQuality.hq:
      return 'hq';
    case PipelineQuality.ultra:
      return 'ultra';
  }
}

enum PipelinePhase {
  queued,
  extractingFrames,
  colmap,
  removingBackground,
  generatingDepth,
  training,
  exporting,
  completed,
  failed,
}

PipelinePhase _phaseFromJson(String? raw) {
  switch (raw) {
    case 'extracting_frames':
      return PipelinePhase.extractingFrames;
    case 'colmap':
      return PipelinePhase.colmap;
    case 'removing_background':
      return PipelinePhase.removingBackground;
    case 'generating_depth':
      return PipelinePhase.generatingDepth;
    case 'training':
      return PipelinePhase.training;
    case 'exporting':
      return PipelinePhase.exporting;
    case 'completed':
      return PipelinePhase.completed;
    case 'failed':
      return PipelinePhase.failed;
    default:
      return PipelinePhase.queued;
  }
}

class PipelineStatus {
  const PipelineStatus({
    required this.jobId,
    required this.status,
    required this.progress,
    this.message,
    this.modelUrl,
  });

  final String jobId;
  final PipelinePhase status;
  final double progress;
  final String? message;
  final String? modelUrl;

  factory PipelineStatus.fromJson(Map<String, dynamic> json) => PipelineStatus(
        jobId: json['job_id'] as String,
        status: _phaseFromJson(json['status'] as String?),
        progress: (json['progress'] as num).toDouble(),
        message: json['message'] as String?,
        modelUrl: json['model_url'] as String?,
      );
}

class PipelineApi {
  PipelineApi(this._dio);
  final Dio _dio;

  Future<String> start({
    required String videoPath,
    int? vehicleId,
    required PipelineQuality quality,
  }) async {
    final form = FormData.fromMap({
      'video': await MultipartFile.fromFile(videoPath),
      if (vehicleId != null) 'vehicle_id': vehicleId.toString(),
      'quality': _qualityToParam(quality),
    });
    final r = await _dio.post<Map<String, dynamic>>(
      '/api/pipeline/start/',
      data: form,
      options: Options(
        headers: {'Content-Type': 'multipart/form-data'},
        sendTimeout: const Duration(seconds: 60),
      ),
    );
    return r.data!['job_id'] as String;
  }

  Future<PipelineStatus> status(String jobId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/api/pipeline/status/$jobId/',
    );
    return PipelineStatus.fromJson(r.data!);
  }
}

final pipelineApiProvider =
    Provider<PipelineApi>((ref) => PipelineApi(ref.watch(apiClientProvider)));
