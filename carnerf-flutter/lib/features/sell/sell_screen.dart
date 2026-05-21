import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class SellScreen extends StatelessWidget {
  const SellScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('내 차 팔기')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.videocam_outlined, size: 64, color: AppColors.gold),
              const SizedBox(height: 16),
              const Text(
                '영상 한 번에\n3D 매물로 등록',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                '30~60초 차량 영상 업로드 시\n자동 3D 모델링 + AI 분석',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.muted),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () {},
                child: const Text('영상 촬영 시작'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
