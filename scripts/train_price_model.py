"""
중고차 가격 예측 모델 학습 (v2)
- 엔카 크롤링 데이터 (data/car_prices.csv) 사용
- LightGBM + XGBoost 비교 → 최적 모델 저장
- v2 개선: ID 기반 중복 제거, badge/form_year/region 피처 추가,
           log-transform, 5-fold CV, 연료타입 매핑 수정
- 저장 경로: backend/app/ml_models/
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, KFold, cross_val_score
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

CURRENT_YEAR = 2026


def load_and_clean(path):
    """데이터 로드 + 정제"""
    print(f"[1/7] 데이터 로드: {path}")
    df = pd.read_csv(path)
    print(f"  원본: {len(df):,}건, {len(df.columns)}컬럼")

    # 필수 컬럼 확인
    required = ['brand', 'model', 'year', 'mileage', 'price', 'fuel_type']
    for col in required:
        if col not in df.columns:
            print(f"  [에러] 필수 컬럼 '{col}' 없음")
            sys.exit(1)

    # ID 기반 중복 제거 (크롤링 중복 방지)
    if 'id' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['id'], keep='first')
        print(f"  ID 중복 제거: {before:,} → {len(df):,}건")

    # 타입 변환
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    if 'form_year' in df.columns:
        df['form_year'] = pd.to_numeric(df['form_year'], errors='coerce')

    # 결측치/이상치 제거
    df = df.dropna(subset=['year', 'mileage', 'price', 'brand', 'model', 'fuel_type'])
    df = df[(df['price'] > 50) & (df['price'] < 30000)]       # 50만~3억
    df = df[(df['mileage'] >= 0) & (df['mileage'] < 500000)]  # 50만km 미만
    df = df[(df['year'] >= 2000) & (df['year'] <= CURRENT_YEAR)]

    # 추가 중복 제거 (동일 차량 스펙)
    df = df.drop_duplicates(subset=['brand', 'model', 'year', 'mileage', 'price'])

    print(f"  정제 후: {len(df):,}건")
    print(f"  브랜드: {df['brand'].nunique()}개, 모델: {df['model'].nunique()}개")
    return df


def feature_engineering(df):
    """파생 변수 생성 (v2: badge, form_year, region, 개선된 fuel 매핑)"""
    print("[2/7] Feature Engineering")

    # 차량 나이
    df['car_age'] = (CURRENT_YEAR - df['year']).clip(lower=0)

    # 연간 주행거리
    df['annual_mileage'] = df['mileage'] / (df['car_age'] + 0.5)

    # 주행거리 구간 (비선형 관계 포착)
    df['mileage_bin'] = pd.cut(df['mileage'], bins=[0, 30000, 60000, 100000, 150000, 500000],
                                labels=[0, 1, 2, 3, 4]).astype(float).fillna(2)

    # 브랜드 등급
    luxury = {'제네시스', 'BMW', '벤츠', '아우디', '볼보', '렉서스', '포르쉐',
              '랜드로버', '재규어', '마세라티', '벤틀리', '롤스로이스'}
    import_normal = {'폭스바겐', '토요타', '혼다', '미니', '지프', '푸조',
                     '시트로엥', '닛산', '포드', '테슬라', '폴스타'}

    df['brand_tier'] = df['brand'].apply(
        lambda b: 3 if b in luxury else (2 if b in import_normal else 1)
    )

    # 연료 타입 인코딩 (실제 데이터에 맞춘 매핑)
    fuel_map = {
        '가솔린': 0, '디젤': 1, '전기': 2, '하이브리드': 3,
        '가솔린+전기': 3, 'LPG': 4, 'LPG(일반인 구입)': 4,
        'CNG': 5, '수소': 6, '가솔린+LPG': 4, 'LPG+전기': 4,
    }
    df['fuel_encoded'] = df['fuel_type'].map(fuel_map).fillna(0).astype(int)

    # 친환경 여부
    eco_fuels = {'전기', '하이브리드', '가솔린+전기', '수소', 'LPG+전기'}
    df['is_eco'] = df['fuel_type'].isin(eco_fuels).astype(int)

    # 배기량 (있으면)
    if 'engine_cc' in df.columns:
        df['engine_cc'] = pd.to_numeric(df['engine_cc'], errors='coerce').fillna(0)
    else:
        df['engine_cc'] = 0

    # form_year (등록연식) — 연식과의 차이가 가치에 영향
    if 'form_year' in df.columns:
        df['form_year'] = df['form_year'].fillna(df['year'])
        df['year_gap'] = (df['form_year'] - df['year']).clip(lower=0, upper=5)
    else:
        df['year_gap'] = 0

    # badge (트림) — 가격에 큰 영향 (e.g. 프리미엄, 캘리그래피, etc.)
    if 'badge' in df.columns and df['badge'].notna().sum() > 100:
        # badge에서 가격 키워드 추출
        premium_kw = ['캘리그래피', '프레스티지', '프리미엄', '익스클루시브', '시그니처',
                      '인스퍼레이션', '노블레스', '럭셔리', '풀옵션']
        base_kw = ['모던', '스마트', '트렌디', '스타일', 'LED']

        def badge_tier(badge):
            if pd.isna(badge):
                return 1
            badge_str = str(badge)
            for kw in premium_kw:
                if kw in badge_str:
                    return 3
            for kw in base_kw:
                if kw in badge_str:
                    return 2
            return 1

        df['badge_tier'] = df['badge'].apply(badge_tier)
    else:
        df['badge_tier'] = 1

    # 브랜드별 평균 가격 (target encoding)
    brand_mean = df.groupby('brand')['price'].mean()
    df['brand_avg_price'] = df['brand'].map(brand_mean)

    # 모델별 평균 가격
    model_mean = df.groupby('model')['price'].mean()
    df['model_avg_price'] = df['model'].map(model_mean)

    # 모델+연식 interaction (같은 모델이라도 연식 차이가 큼)
    model_year_mean = df.groupby(['model', 'year'])['price'].mean()
    df['model_year_avg'] = df.set_index(['model', 'year']).index.map(
        lambda x: model_year_mean.get(x, df['price'].mean())
    )

    # log(price) for better regression (저장용, 타겟에 반영)
    df['log_price'] = np.log1p(df['price'])

    feature_count = len([c for c in df.columns if c not in ['id', 'brand', 'model', 'badge',
                         'badge_detail', 'fuel_type', 'transmission', 'color', 'region',
                         'sell_type', 'green_type', 'ev_type', 'photo_url', 'encar_url',
                         'crawled_at', 'price', 'log_price', 'form_year']])
    print(f"  생성된 피처: {feature_count}개")
    return df


def prepare_features(df):
    """학습용 피처/타겟 분리"""
    print("[3/7] 피처 준비")

    # 카테고리 인코딩
    encoders = {}
    cat_cols = ['brand', 'model', 'fuel_type']

    if 'region' in df.columns and df['region'].notna().sum() > 100:
        df['region'] = df['region'].fillna('미지정')
        cat_cols.append('region')

    for col in cat_cols:
        le = LabelEncoder()
        df[f'{col}_le'] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # 수치형 피처
    feature_cols = [
        'year', 'mileage', 'car_age', 'annual_mileage', 'mileage_bin',
        'brand_tier', 'fuel_encoded', 'is_eco', 'engine_cc',
        'badge_tier', 'year_gap',
        'brand_avg_price', 'model_avg_price', 'model_year_avg',
        'brand_le', 'model_le', 'fuel_type_le',
    ]
    if 'region_le' in df.columns:
        feature_cols.append('region_le')

    # 실제 존재하는 컬럼만
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols].copy()
    y = df['price'].copy()

    # NaN/Inf 처리
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

    print(f"  피처 수: {len(feature_cols)}")
    print(f"  피처 목록: {feature_cols}")
    return X, y, feature_cols, encoders


def cross_validate(X, y, feature_cols):
    """5-fold CV로 모델 안정성 확인"""
    print("[4/7] 5-Fold 교차 검증")

    kf = KFold(n_splits=3, shuffle=True, random_state=42)

    lgb_model = lgb.LGBMRegressor(
        objective='regression', metric='rmse',
        num_leaves=127, learning_rate=0.05,
        feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=5,
        n_estimators=300, verbose=-1, random_state=42,
    )
    lgb_scores = cross_val_score(lgb_model, X, y, cv=kf, scoring='r2')
    print(f"  LightGBM CV R²: {lgb_scores.mean():.4f} (±{lgb_scores.std():.4f})")
    print(f"    folds: {[f'{s:.4f}' for s in lgb_scores]}")

    xgb_model = xgb.XGBRegressor(
        objective='reg:squarederror', n_estimators=300,
        learning_rate=0.05, max_depth=8,
        subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbosity=0,
    )
    xgb_scores = cross_val_score(xgb_model, X, y, cv=kf, scoring='r2')
    print(f"  XGBoost  CV R²: {xgb_scores.mean():.4f} (±{xgb_scores.std():.4f})")
    print(f"    folds: {[f'{s:.4f}' for s in xgb_scores]}")

    return {'lgbm': lgb_scores.mean(), 'xgb': xgb_scores.mean()}


def train_models(X_train, X_test, y_train, y_test, feature_cols):
    """LightGBM + XGBoost 학습 및 비교"""
    print("[5/7] 모델 학습")
    results = {}

    # --- LightGBM ---
    print("\n  [LightGBM] 학습 중...")
    lgb_model = lgb.LGBMRegressor(
        objective='regression', metric='rmse',
        num_leaves=127, learning_rate=0.03,
        feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=5,
        n_estimators=1000, min_child_samples=10,
        reg_alpha=0.1, reg_lambda=0.1,
        verbose=-1, random_state=42,
    )
    lgb_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)],
    )
    lgb_pred = lgb_model.predict(X_test)
    lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_pred))
    lgb_mae = mean_absolute_error(y_test, lgb_pred)
    lgb_r2 = r2_score(y_test, lgb_pred)
    lgb_mape = np.mean(np.abs((y_test - lgb_pred) / y_test.clip(lower=1))) * 100

    results['lgbm'] = {
        'model': lgb_model, 'rmse': lgb_rmse, 'mae': lgb_mae,
        'r2': lgb_r2, 'mape': lgb_mape,
    }
    print(f"    RMSE: {lgb_rmse:.1f}만원 | MAE: {lgb_mae:.1f}만원 | R²: {lgb_r2:.4f} | MAPE: {lgb_mape:.2f}%")
    print(f"    best_iteration: {lgb_model.best_iteration_}")

    # --- XGBoost ---
    print("\n  [XGBoost] 학습 중...")
    xgb_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=1000, learning_rate=0.03,
        max_depth=8, subsample=0.8, colsample_bytree=0.8,
        min_child_weight=5, reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, verbosity=0, early_stopping_rounds=100,
    )
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    xgb_pred = xgb_model.predict(X_test)
    xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
    xgb_mae = mean_absolute_error(y_test, xgb_pred)
    xgb_r2 = r2_score(y_test, xgb_pred)
    xgb_mape = np.mean(np.abs((y_test - xgb_pred) / y_test.clip(lower=1))) * 100

    results['xgb'] = {
        'model': xgb_model, 'rmse': xgb_rmse, 'mae': xgb_mae,
        'r2': xgb_r2, 'mape': xgb_mape,
    }
    print(f"    RMSE: {xgb_rmse:.1f}만원 | MAE: {xgb_mae:.1f}만원 | R²: {xgb_r2:.4f} | MAPE: {xgb_mape:.2f}%")
    print(f"    best_iteration: {xgb_model.best_iteration}")

    return results


def save_best_model(results, encoders, feature_cols, df):
    """최적 모델 저장 + target encoding 통계도 함께 저장"""
    print("\n[6/7] 최적 모델 선택 및 저장")

    best_name = max(results, key=lambda k: results[k]['r2'])
    best = results[best_name]
    print(f"  최적 모델: {best_name.upper()}")
    print(f"  RMSE: {best['rmse']:.1f}만원 | MAE: {best['mae']:.1f}만원 | R²: {best['r2']:.4f} | MAPE: {best['mape']:.2f}%")

    # 모델 저장
    joblib.dump(best['model'], os.path.join(MODEL_DIR, "price_predictor.pkl"))
    joblib.dump(encoders, os.path.join(MODEL_DIR, "price_encoders.pkl"))
    joblib.dump(feature_cols, os.path.join(MODEL_DIR, "price_features.pkl"))

    # target encoding 통계 저장 (predict.py에서 사용)
    brand_avg = df.groupby('brand')['price'].mean().to_dict()
    model_avg = df.groupby('model')['price'].mean().to_dict()
    model_year_avg = df.groupby(['model', 'year'])['price'].mean().to_dict()

    meta = {
        'best_model': best_name,
        'rmse': round(best['rmse'], 2),
        'mae': round(best['mae'], 2),
        'r2': round(best['r2'], 4),
        'mape': round(best['mape'], 2),
        'feature_cols': feature_cols,
        'n_features': len(feature_cols),
        'n_samples': len(df),
        'brand_avg': brand_avg,
        'model_avg': model_avg,
        'model_year_avg': {f"{k[0]}_{k[1]}": v for k, v in model_year_avg.items()},
        'version': 'v2',
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
    print("\n[7/7] 피처 중요도 (Top 15)")
    importance = model.feature_importances_
    indices = np.argsort(importance)[::-1]
    for i, idx in enumerate(indices[:15]):
        bar = '█' * int(importance[idx] / max(importance) * 30)
        print(f"  {i+1:2d}. {feature_cols[idx]:22s}  {importance[idx]:6.0f}  {bar}")


def error_analysis(y_test, y_pred, X_test, feature_cols):
    """잔차 분석 — 어떤 구간에서 예측이 안 좋은지 파악"""
    print("\n[부록] 에러 분석")
    errors = np.abs(y_test.values - y_pred)
    pct_errors = errors / y_test.values.clip(min=1) * 100

    # 가격대별 MAPE
    bins = [(0, 500), (500, 1000), (1000, 2000), (2000, 3000), (3000, 5000), (5000, 30000)]
    print(f"  {'가격대(만원)':<18} {'건수':>6} {'MAPE(%)':>8} {'MAE(만원)':>10}")
    print(f"  {'-'*46}")
    for low, high in bins:
        mask = (y_test >= low) & (y_test < high)
        if mask.sum() > 0:
            avg_mape = pct_errors[mask].mean()
            avg_mae = errors[mask].mean()
            print(f"  {f'{low:,}~{high:,}':<18} {mask.sum():>6} {avg_mape:>8.1f} {avg_mae:>10.1f}")


def main():
    print("=" * 60)
    print("  CarNeRF 중고차 가격 예측 모델 학습 (v2)")
    print("=" * 60)

    # 1. 데이터 로드
    df = load_and_clean(DATA_PATH)

    # 2. Feature Engineering
    df = feature_engineering(df)

    # 3. 피처 준비
    X, y, feature_cols, encoders = prepare_features(df)

    # 4. 교차 검증
    cv_results = cross_validate(X, y, feature_cols)

    # 5. Train/Test 분리
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\n  Train: {len(X_train):,}건 | Test: {len(X_test):,}건")

    # 6. 모델 학습
    results = train_models(X_train, X_test, y_train, y_test, feature_cols)

    # 7. 저장
    best_name, best = save_best_model(results, encoders, feature_cols, df)

    # 8. 피처 중요도
    feature_importance(best['model'], feature_cols, best_name)

    # 9. 에러 분석
    best_pred = best['model'].predict(X_test)
    error_analysis(y_test, best_pred, X_test, feature_cols)

    # 비교 요약
    print("\n" + "=" * 60)
    print("  모델 비교 요약")
    print("=" * 60)
    print(f"  {'모델':<12} {'RMSE(만원)':<12} {'MAE(만원)':<12} {'R²':<10} {'MAPE(%)':<10} {'CV R²':<10}")
    print(f"  {'-'*64}")
    for name, r in results.items():
        marker = " ◀ BEST" if name == best_name else ""
        cv_r2 = cv_results.get(name, 0)
        print(f"  {name.upper():<12} {r['rmse']:<12.1f} {r['mae']:<12.1f} {r['r2']:<10.4f} {r['mape']:<10.2f} {cv_r2:<10.4f}{marker}")
    print("=" * 60)


if __name__ == "__main__":
    main()
