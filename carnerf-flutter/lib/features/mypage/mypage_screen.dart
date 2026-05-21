import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class MyPageScreen extends StatelessWidget {
  const MyPageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('마이페이지')),
      body: const Center(
        child: Text('마이페이지 (구현 예정)', style: TextStyle(color: AppColors.muted)),
      ),
    );
  }
}
