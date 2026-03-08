"""
중고차 가격 예측 모델 학습
- 엔카 크롤링 데이터 (data/car_prices.csv) 사용
- LightGBM + XGBoost 비교 → 최적 모델 저장
- 저장 경로: backend/app/ml_models/
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import lightgbm as lgb
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "car_prices.csv")
MODEL_DIR = os.path.join(BASE_DIR, "backend", "app", "ml_models")
os.makedirs(MODEL_DIR, exist_ok=True)


def load_and_clean(path):
    """데이터 로드 + 정제"""
    print(f"[1/6] 데이터 로드: {path}")
    df = pd.read_csv(path)
    print(f"  원본: {len(df):,}건, {len(df.columns)}컬럼")

    # 필수 컬럼 확인
    required = ['brand', 'model', 'year', 'mileage', 'price', 'fuel_type']
    for col in required:
        if col not in df.columns:
            print(f"  [에러] 필수 컬럼 '{col}' 없음")
            sys.exit(1)

    # 타입 변환
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')

    # 결측치/이상치 제거
    df = df.dropna(subset=['year', 'mileage', 'price', 'brand', 'model', 'fuel_type'])
    df = df[(df['price'] > 50) & (df['price'] < 30000)]       # 50만~3억
    df = df[(df['mileage'] >= 0) & (df['mileage'] < 500000)]  # 50만km 미만
    df = df[(df['year'] >= 2000) & (df['year'] <= 2026)]       # 2000~2026년

    # 중복 제거
    df = df.drop_duplicates(subset=['brand', 'model', 'year', 'mileage', 'price'])

    print(f"  정제 후: {len(df):,}건")
    return df


def feature_engineering(df):
    """파생 변수 생성"""
    print("[2/6] Feature Engineering")

    # 차량 나이
    df['car_age'] = 2026 - df['year']
    df['car_age'] = df['car_age'].clip(lower=0)

    # 연간 주행거리
    df['annual_mileage'] = df['mileage'] / (df['car_age'] + 0.5)

    # 브랜드 등급
    luxury = ['제네시스', 'BMW', '벤츠', '아우디', '볼보', '렉서스', '포르쉐',
              '랜드로버', '재규어', '마세라티', '벤틀리', '롤스로이스']
    import_normal = ['폭스바겐', '토요타', '혼다', '미니', '지프', '푸조',
                     '시트로엥', '닛산', '포드', '테슬라', '폴스타']
    domestic = ['현대', '기아', '쉐보레(GM대우)', '르노코리아(삼성)', '쌍용', 'KG모빌리티']

    def brand_tier(b):
        if b in luxury:
            return 3
        elif b in import_normal:
            return 2
        else:
            return 1
    df['brand_tier'] = df['brand'].apply(brand_tier)

    # 연료 타입 인코딩
    fuel_map = {'가솔린': 0, '디젤': 1, '전기': 2, '하이브리드': 3, 'LPG': 4, 'CNG': 5}
    df['fuel_encoded'] = df['fuel_type'].map(fuel_map).fillna(0).astype(int)

    # 배기량 (있으면)
    if 'engine_cc' in df.columns:
        df['engine_cc'] = pd.to_numeric(df['engine_cc'], errors='coerce').fillna(0)
    else:
        df['engine_cc'] = 0

    # 브랜드별 평균 가격 (target encoding 유사)
    brand_mean = df.groupby('brand')['price'].mean()
    df['brand_avg_price'] = df['brand'].map(brand_mean)

    # 모델별 평균 가격
    model_mean = df.groupby('model')['price'].mean()
    df['model_avg_price'] = df['model'].map(model_mean)

    print(f"  생성된 피처: {len(df.columns)}개 컬럼")
    return df


def prepare_features(df):
    """학습용 피처/타겟 분리"""
    print("[3/6] 피처 준비")

    # 카테고리 인코딩
    encoders = {}
    cat_cols = ['brand', 'model', 'fuel_type']

    # region이 있으면 추가
    if 'region' in df.columns:
        df['region'] = df['region'].fillna('미지정')
        cat_cols.append('region')

    for col in cat_cols:
        le = LabelEncoder()
        df[f'{col}_le'] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # 수치형 피처
    feature_cols = [
        'year', 'mileage', 'car_age', 'annual_mileage',
        'brand_tier', 'fuel_encoded', 'engine_cc',
        'brand_avg_price', 'model_avg_price',
        'brand_le', 'model_le', 'fuel_type_le',
    ]
    if 'region_le' in df.columns:
        feature_cols.append('region_le')

    # 실제 존재하는 컬럼만
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols].copy()
    y = df['price'].copy()

    # NaN/Inf 처리
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    print(f"  피처 수: {len(feature_cols)}")
    print(f"  피처 목록: {feature_cols}")
    return X, y, feature_cols, encoders


def train_models(X_train, X_test, y_train, y_test, feature_cols):
    """LightGBM + XGBoost 학습 및 비교"""
    print("[4/6] 모델 학습")
    results = {}

    # --- LightGBM ---
    print("\n  [LightGBM] 학습 중...")
    lgb_params = {
        'objective': 'regression',
        'metric': 'rmse',
        'num_leaves': 127,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'n_estimators': 1000,
        'verbose': -1,
        'random_state': 42,
    }
    lgb_model = lgb.LGBMRegressor(**lgb_params)
    lgb_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
    )
    lgb_pred = lgb_model.predict(X_test)
    lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_pred))
    lgb_mae = mean_absolute_error(y_test, lgb_pred)
    lgb_r2 = r2_score(y_test, lgb_pred)
    lgb_mape = np.mean(np.abs((y_test - lgb_pred) / y_test)) * 100

    results['lgbm'] = {
        'model': lgb_model, 'rmse': lgb_rmse, 'mae': lgb_mae,
        'r2': lgb_r2, 'mape': lgb_mape,
    }
    print(f"    RMSE: {lgb_rmse:.1f}만원 | MAE: {lgb_mae:.1f}만원 | R²: {lgb_r2:.4f} | MAPE: {lgb_mape:.2f}%")

    # --- XGBoost ---
    print("\n  [XGBoost] 학습 중...")
    xgb_params = {
        'objective': 'reg:squarederror',
        'n_estimators': 1000,
        'learning_rate': 0.05,
        'max_depth': 8,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbosity': 0,
        'early_stopping_rounds': 50,
    }
    xgb_model = xgb.XGBRegressor(**xgb_params)
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    xgb_pred = xgb_model.predict(X_test)
    xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
    xgb_mae = mean_absolute_error(y_test, xgb_pred)
    xgb_r2 = r2_score(y_test, xgb_pred)
    xgb_mape = np.mean(np.abs((y_test - xgb_pred) / y_test)) * 100

    results['xgb'] = {
        'model': xgb_model, 'rmse': xgb_rmse, 'mae': xgb_mae,
        'r2': xgb_r2, 'mape': xgb_mape,
    }
    print(f"    RMSE: {xgb_rmse:.1f}만원 | MAE: {xgb_mae:.1f}만원 | R²: {xgb_r2:.4f} | MAPE: {xgb_mape:.2f}%")

    return results


def save_best_model(results, encoders, feature_cols):
    """최적 모델 저장"""
    print("\n[5/6] 최적 모델 선택 및 저장")

    # R² 기준 최적 모델
    best_name = max(results, key=lambda k: results[k]['r2'])
    best = results[best_name]
    print(f"  최적 모델: {best_name.upper()}")
    print(f"  RMSE: {best['rmse']:.1f}만원 | MAE: {best['mae']:.1f}만원 | R²: {best['r2']:.4f} | MAPE: {best['mape']:.2f}%")

    # 저장
    joblib.dump(best['model'], os.path.join(MODEL_DIR, "price_predictor.pkl"))
    joblib.dump(encoders, os.path.join(MODEL_DIR, "price_encoders.pkl"))
    joblib.dump(feature_cols, os.path.join(MODEL_DIR, "price_features.pkl"))

    # 메타데이터
    meta = {
        'best_model': best_name,
        'rmse': round(best['rmse'], 2),
        'mae': round(best['mae'], 2),
        'r2': round(best['r2'], 4),
        'mape': round(best['mape'], 2),
        'feature_cols': feature_cols,
        'n_features': len(feature_cols),
    }
    joblib.dump(meta, os.path.join(MODEL_DIR, "price_meta.pkl"))

    print(f"\n  저장 완료:")
    print(f"    {MODEL_DIR}/price_predictor.pkl")
    print(f"    {MODEL_DIR}/price_encoders.pkl")
    print(f"    {MODEL_DIR}/price_features.pkl")
    print(f"    {MODEL_DIR}/price_meta.pkl")

    return best_name, best


def feature_importance(model, feature_cols, model_name):
    """피처 중요도 출력"""
    print("\n[6/6] 피처 중요도 (Top 10)")
    if model_name == 'lgbm':
        importance = model.feature_importances_
    else:
        importance = model.feature_importances_

    indices = np.argsort(importance)[::-1]
    for i, idx in enumerate(indices[:10]):
        print(f"  {i+1}. {feature_cols[idx]:25s}  {importance[idx]:.0f}")


def main():
    print("=" * 60)
    print("  CarNeRF 중고차 가격 예측 모델 학습")
    print("=" * 60)

    # 1. 데이터 로드
    df = load_and_clean(DATA_PATH)

    # 2. Feature Engineering
    df = feature_engineering(df)

    # 3. 피처 준비
    X, y, feature_cols, encoders = prepare_features(df)

    # 4. Train/Test 분리
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\n  Train: {len(X_train):,}건 | Test: {len(X_test):,}건")

    # 5. 모델 학습
    results = train_models(X_train, X_test, y_train, y_test, feature_cols)

    # 6. 저장
    best_name, best = save_best_model(results, encoders, feature_cols)

    # 7. 피처 중요도
    feature_importance(best['model'], feature_cols, best_name)

    # 비교 요약
    print("\n" + "=" * 60)
    print("  모델 비교 요약")
    print("=" * 60)
    print(f"  {'모델':<12} {'RMSE(만원)':<12} {'MAE(만원)':<12} {'R²':<10} {'MAPE(%)':<10}")
    print(f"  {'-'*52}")
    for name, r in results.items():
        marker = " <-- BEST" if name == best_name else ""
        print(f"  {name.upper():<12} {r['rmse']:<12.1f} {r['mae']:<12.1f} {r['r2']:<10.4f} {r['mape']:<10.2f}{marker}")
    print("=" * 60)


if __name__ == "__main__":
    main()
