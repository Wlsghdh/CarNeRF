import 'package:flutter/material.dart';

import '../../../core/api/pipeline_api.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/dark_card.dart';

const List<({PipelinePhase key, String label})> _steps = [
  (key: PipelinePhase.extractingFrames, label: '프레임 추출'),
  (key: PipelinePhase.colmap, label: 'SfM (카메라 추정)'),
  (key: PipelinePhase.removingBackground, label: '배경 제거'),
  (key: PipelinePhase.generatingDepth, label: '깊이 추정'),
  (key: PipelinePhase.training, label: '3D 학습'),
  (key: PipelinePhase.exporting, label: '모델 추출'),
  (key: PipelinePhase.completed, label: '완료'),
];

class PipelineStepperView extends StatelessWidget {
  const PipelineStepperView({super.key, this.status});
  final PipelineStatus? status;

  @override
  Widget build(BuildContext context) {
    final idx = status == null
        ? -1
        : _steps.indexWhere((s) => s.key == status!.status);

    return DarkCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '3D 파이프라인 진행률',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                status == null ? '대기 중' : '${status!.progress.round()}%',
                style: const TextStyle(
                  color: AppColors.gold,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          for (var i = 0; i < _steps.length; i++)
            _StepRow(
              index: i + 1,
              label: _steps[i].label,
              done: idx > i || status?.status == PipelinePhase.completed,
              active: idx == i,
            ),
          if (status?.message != null && status!.message!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              status!.message!,
              style: const TextStyle(color: AppColors.muted, fontSize: 11.5),
            ),
          ],
        ],
      ),
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.index,
    required this.label,
    required this.done,
    required this.active,
  });

  final int index;
  final String label;
  final bool done;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: done ? AppColors.gold : Colors.transparent,
              shape: BoxShape.circle,
              border: done
                  ? null
                  : Border.all(
                      color: active
                          ? AppColors.gold
                          : Colors.white.withValues(alpha: 0.15),
                      width: active ? 2 : 1,
                    ),
            ),
            alignment: Alignment.center,
            child: done
                ? const Icon(Icons.check, size: 12, color: AppColors.black)
                : Text(
                    '$index',
                    style: TextStyle(
                      color: active ? AppColors.gold : AppColors.muted,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: done || active ? AppColors.white : AppColors.muted,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (active)
            const Text(
              '진행 중…',
              style: TextStyle(
                color: AppColors.gold,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
        ],
      ),
    );
  }
}
