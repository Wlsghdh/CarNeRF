import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class VehicleDetailScreen extends StatelessWidget {
  const VehicleDetailScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('차량 #$id')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: Container(
                height: 220,
                alignment: Alignment.center,
                child: const Text(
                  '3D 뷰어 (WebView 예정)',
                  style: TextStyle(color: AppColors.muted),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('AI 진단 요약',
                        style: TextStyle(
                            color: AppColors.gold, fontWeight: FontWeight.w600)),
                    SizedBox(height: 8),
                    Text(
                      'YOLOv8 결함 탐지 + 가격 예측 결과가 여기 표시됩니다.',
                      style: TextStyle(color: AppColors.white),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
