import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';

class ListingsScreen extends StatelessWidget {
  const ListingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('매물')),
      body: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: 6,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (context, i) => Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            title: Text('샘플 매물 #${i + 1}', style: const TextStyle(color: AppColors.white)),
            subtitle: const Text('연식 / 주행거리 / 가격', style: TextStyle(color: AppColors.muted)),
            trailing: const Icon(Icons.chevron_right, color: AppColors.gold),
            onTap: () => context.push('/vehicle/${i + 1}'),
          ),
        ),
      ),
    );
  }
}
