# 3D Pipeline Skill

## 역할
3D Gaussian Splatting 파이프라인 관리, 품질 최적화, 모델 export

## 핵심 명령
```bash
# HQ 학습
python scripts/train_hq.py --source_path data/colmap_output/<name>/dense \
  --output_path data/gaussian_output/<name> --iterations 60000

# 벤치마크 (여러 하이퍼파라미터 비교)
python scripts/benchmark_gs.py --source_path <dense> --configs A B C D

# Export
python scripts/export_model.py --input <ply> --output <dir> --format both \
  --max_gaussians 2000000 --spatial_iqr 4.0
```

## 품질 최적화 파라미터
| 파라미터 | 기본값 | HQ | Ultra |
|---------|--------|-----|-------|
| iterations | 7000 | 60000 | 100000 |
| densify_grad | 0.0002 | 0.00007 | 0.00005 |
| densify_until | 15000 | 35000 | 50000 |
| lambda_dssim | 0.2 | 0.2 | 0.15 |
| antialiasing | OFF | ON | ON |
| optimizer | default | default | sparse_adam |

## 주의사항
- CUDA_HOME=/usr/local/cuda-12.2 필수
- depth_params.json 없으면 depth 비활성화
- 2DGS는 scale_2 없음 → export_model.py에서 자동 처리
