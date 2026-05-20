# AI/ML Skill

## 역할
결함 탐지, 가격 예측, 차량 요약 AI 모델 관리

## 모델
| 모델 | 경로 | 용도 |
|------|------|------|
| YOLOv8 | ml_models/defect_detector.pt | 결함 탐지 (dent,scratch,paint,glass,missing) |
| LightGBM | ml_models/price_predictor.pkl | 가격 예측 |
| ChatGPT | api/ai_summary.py | 차량 요약 (OPENAI_API_KEY 필요) |
| Depth Anything V2 | HuggingFace 자동 다운로드 | 깊이 맵 생성 |
| rembg U2Net | pip install rembg | 배경 제거 |

## API
- `GET /api/defect/vehicles/{id}` - 결함 분석
- `POST /api/predict/price` - 가격 예측
- `GET /api/ai/vehicle-summary/{id}` - AI 요약

## 학습 스크립트
```bash
python scripts/train_defect_model.py   # YOLOv8 결함 학습
python scripts/train_price_model.py    # 가격 예측 학습
```
