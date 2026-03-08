# 팀원 C 업무 계획서
## 담당: 모바일 앱 개발 + 서비스 배포 인프라

---

## 1. 역할 요약

| 항목 | 내용 |
|------|------|
| **담당 분야** | ① React Native 모바일 앱 ② Docker + 클라우드 배포 |
| **최종 산출물** | ① iOS/Android 앱 ② 외부 접속 가능한 프로덕션 서버 |
| **연동 대상** | 팀장(API 소비, 배포 환경 세팅), 전체 팀 (앱에 모든 기능 통합) |
| **주요 기술** | React Native (Expo), TypeScript, Docker, Nginx, GitHub Actions |

--- 

## 2. 왜 모바일 앱이 필요한가?

```
중고차 거래의 현실:
  → 소비자 78%가 모바일로 중고차 검색 (2025 기준)
  → 3D 차량 뷰어를 손에 들고 회전/확대하는 경험 = 강력한 데모
  → 창업동아리 발표 시 심사위원에게 앱 직접 시연 가능
  → 웹보다 앱이 더 "진짜 서비스"처럼 보임
```

---

## 3. 전체 개발 흐름

```
[Week 1] 앱 환경 세팅 + 기본 화면
  Expo 프로젝트 생성 → 네비게이션 → 홈/목록 화면

[Week 2] 핵심 기능 구현
  매물 검색/필터 → 차량 상세 → 3D 뷰어

[Week 3] AI 기능 + 촬영 기능
  카메라로 차량 촬영 → 서버 전송 → 결함 분석 결과 표시

[Week 4] 배포 + 앱 빌드
  Docker 서버 배포 → 앱 빌드 (APK/TestFlight)
```

---

## 4. Sprint 계획 (4주)

### Week 1: 앱 환경 세팅 + 기본 화면

#### 목표
- Expo 프로젝트 생성 + 기본 네비게이션 완성
- 홈화면 + 매물 목록 화면 UI 완성

#### 세부 Task

**[Task C-1-1] 개발 환경 세팅**
```bash
# Node.js 18+ 필요
npm install -g expo-cli

# 프로젝트 생성
npx create-expo-app CarNeRF --template typescript
cd CarNeRF

# 주요 패키지 설치
npx expo install expo-router expo-camera expo-image-picker
npm install @react-navigation/native @react-navigation/bottom-tabs
npm install react-native-reanimated react-native-gesture-handler
npm install axios @tanstack/react-query zustand
npm install nativewind   # Tailwind for React Native
```

**[Task C-1-2] 프로젝트 폴더 구조**
```
mobile-app/
├── app/
│   ├── (tabs)/
│   │   ├── index.tsx          # 홈 탭
│   │   ├── listings.tsx       # 매물 검색 탭
│   │   ├── sell.tsx           # 내 차 팔기 탭
│   │   └── profile.tsx        # 프로필/로그인 탭
│   ├── vehicle/
│   │   └── [id].tsx           # 차량 상세 페이지
│   └── _layout.tsx            # 루트 레이아웃
├── components/
│   ├── CarCard.tsx            # 매물 카드 컴포넌트
│   ├── FilterSheet.tsx        # 필터 바텀시트
│   ├── DefectBadge.tsx        # 결함 심각도 뱃지
│   └── PriceChart.tsx         # 감가상각 그래프
├── api/
│   └── client.ts              # axios 인스턴스 + API 함수
├── store/
│   └── authStore.ts           # Zustand 인증 상태
└── constants/
    └── Colors.ts              # 다크 테마 색상 변수
```

**[Task C-1-3] 다크 테마 색상 정의** (`constants/Colors.ts`)
```typescript
export const Colors = {
  bg:      '#07090F',
  surface: '#0E1117',
  sur2:    '#161B24',
  border:  'rgba(255,255,255,0.08)',
  accent:  '#0EA5E9',
  text:    '#E2E8F0',
  muted:   '#64748B',
  muted2:  '#94A3B8',
};
// 웹과 동일한 디자인 시스템 유지
```

**[Task C-1-4] API 클라이언트** (`api/client.ts`)
```typescript
import axios from 'axios';

// 개발 시: 팀장 서버 IP
// 배포 후: https://carnerf.kr/api
const API_BASE = __DEV__
  ? 'http://서버IP:8000'
  : 'https://carnerf.kr';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  withCredentials: true,  // JWT 쿠키
});

// API 함수들
export const getListings = (params) => api.get('/api/listings/', { params });
export const getVehicle = (id) => api.get(`/api/vehicles/${id}`);
export const analyzeDefect = (formData) => api.post('/api/defect/analyze', formData);
export const predictPrice = (data) => api.post('/api/predict/price', data);
```

**[Task C-1-5] 홈화면 구현** (`app/(tabs)/index.tsx`)
```typescript
// 주요 구성:
// - 상단: CarNeRF 로고 + 검색바
// - 히어로 섹션: "AI가 진단하는 믿을 수 있는 중고차"
// - 주요 기능 카드 3개 (3D 뷰어 / AI 진단 / 가격 예측)
// - 추천 매물 수평 스크롤 카드
// - 하단 탭 바 (홈 / 검색 / 팔기 / 프로필)
```

**[Task C-1-6] 매물 목록 화면** (`app/(tabs)/listings.tsx`)
```typescript
// 주요 구성:
// - 상단 검색바 + 필터 버튼
// - 브랜드/연료/가격 필터 바텀시트 (FilterSheet)
// - FlatList로 CarCard 렌더링
// - 무한 스크롤 (React Query의 useInfiniteQuery)
// - 정렬 선택 (최신순/가격순/주행거리순)
```

---

### Week 2: 차량 상세 + 3D 뷰어

#### 목표
- 차량 상세 페이지 완성
- 모바일 3D 뷰어 (WebView 임베딩)
- AI 진단 리포트 UI

#### 세부 Task

**[Task C-2-1] 차량 상세 페이지** (`app/vehicle/[id].tsx`)
```typescript
// 주요 구성:
// - 상단: 차량 사진 갤러리 (수평 스와이프)
// - "3D로 보기" 버튼 → 3D 뷰어 화면으로 이동
// - 가격 + AI 예측 범위 표시
// - 스펙 카드 (연식/주행거리/연료/변속기/지역)
// - AI 결함 진단 리포트 섹션
//   - 종합 점수 원형 게이지
//   - 결함 종류별 바 차트
//   - 결함 사진 (annotated_image)
// - 판매자 정보 + 문의하기 버튼
// - 가격 협의하기 버튼
```

**[Task C-2-2] 모바일 3D 뷰어**
```typescript
// 방법 1: WebView로 웹 뷰어 임베딩 (빠른 구현)
import { WebView } from 'react-native-webview';

function Viewer3D({ vehicleId }) {
  return (
    <WebView
      source={{ uri: `${API_BASE}/viewer/${vehicleId}` }}
      style={{ flex: 1 }}
      allowsFullscreenVideo
      // 자이로스코프 연동 (기기 기울이면 3D 회전)
      onMessage={handleMessage}
    />
  );
}

// 방법 2: expo-gl + three.js (네이티브 렌더링, 고품질)
// → 구현 복잡도 높음, 시간 여유 있으면 적용
```

**[Task C-2-3] AI 진단 리포트 컴포넌트**
```typescript
// DefectReport.tsx
// - 원형 SVG 게이지 (점수 표시)
// - 결함 항목 리스트 (아이콘 + 이름 + 심각도)
// - 결함 탐지 이미지 (base64 → Image)
// - 팀원 A 가격 예측과 연동:
//   "결함으로 인한 예상 감가: 약 430만원"
```

**[Task C-2-4] PriceChart 컴포넌트 (감가상각 그래프)**
```typescript
import { LineChart } from 'react-native-chart-kit';
// 팀원 A API의 depreciation_curve 데이터 시각화
// X: 연도, Y: 예상 가격
// 현재 연도 포인트 강조 (cyan 점)
```

**[Task C-2-5] 찜/비교 기능**
```typescript
// Zustand로 로컬 상태 관리
// 찜한 차량 목록 → AsyncStorage 영구 저장
// 최대 2대 비교 (스펙 나란히 표시)
```

---

### Week 3: 카메라 촬영 + 결함 분석

#### 목표
- 차량 촬영 → 즉시 결함 분석
- 내 차 팔기 플로우 완성

#### 세부 Task

**[Task C-3-1] 차량 촬영 기능** (`app/(tabs)/sell.tsx`)
```typescript
import { Camera, CameraType } from 'expo-camera';

// 촬영 가이드 오버레이 (차량 외곽선 가이드)
// 촬영 각도 안내: 정면/좌측면/우측면/후면/실내 (5컷)
// 각 컷마다 실시간 결함 분석 (찍는 즉시)
```

**[Task C-3-2] 실시간 결함 분석 플로우**
```typescript
async function captureAndAnalyze() {
  // 1. 카메라로 사진 촬영
  const photo = await camera.takePictureAsync({ quality: 0.8 });

  // 2. 서버로 전송 (팀원 B API)
  const formData = new FormData();
  formData.append('file', { uri: photo.uri, type: 'image/jpeg', name: 'car.jpg' });
  const result = await analyzeDefect(formData);

  // 3. 결과 표시 (결함 bbox 오버레이 이미지 + 심각도)
  setDefectResult(result);

  // 4. 결함 점수 → 팀원 A 가격 예측에 전달
  const price = await predictPrice({ ...carInfo, defect_score: result.defect_score });
  setPredictedPrice(price);
}
```

**[Task C-3-3] 차량 등록 멀티스텝 폼**
```
Step 1: 기본 정보 (브랜드/모델/연식/주행거리)
Step 2: 차량 사진 촬영 (5컷 가이드)
Step 3: AI 결함 분석 결과 확인 + 가격 제안
Step 4: 가격 입력 + 설명 작성
Step 5: 등록 완료 + 3D 스캔 안내
```

**[Task C-3-4] 3D 스캔 촬영 가이드**
```typescript
// 팀장의 영상 업로드 기능과 연동
// 360도 촬영 가이드 (화살표 방향 안내)
// 촬영 완료 → MP4 파일 서버 전송
// 변환 진행률 실시간 표시 (polling)
```

**[Task C-3-5] 푸시 알림 설정**
```typescript
import * as Notifications from 'expo-notifications';
// 3D 변환 완료 시 푸시 알림
// "차량 3D 모델 생성 완료! 지금 확인해보세요 🚗"
```

---

### Week 4: 배포 인프라 + 앱 빌드

#### 목표
- Docker로 서버 컨테이너화
- 외부 도메인 접속 가능한 프로덕션 환경
- 앱 APK + TestFlight 빌드

#### 세부 Task

**[Task C-4-1] Dockerfile 작성** (`backend/Dockerfile`)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

**[Task C-4-2] docker-compose.yml**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: carnerf-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./backend/carnerf.db:/app/carnerf.db
      - ./backend/app/static/models:/app/app/static/models
      - ./backend/app/models:/app/app/models
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production

  nginx:
    image: nginx:alpine
    container_name: carnerf-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
```

**[Task C-4-3] Nginx 설정** (`nginx/nginx.conf`)
```nginx
server {
    listen 80;
    server_name carnerf.kr www.carnerf.kr;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name carnerf.kr;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # 3D 모델 파일 (대용량) 전용 설정
    location /static/models/ {
        proxy_pass http://backend:8000;
        proxy_read_timeout 300;
        client_max_body_size 500M;
    }

    # 영상 업로드 (대용량)
    location /api/pipeline/ {
        proxy_pass http://backend:8000;
        client_max_body_size 500M;
        proxy_read_timeout 600;
    }

    # 일반 요청
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**[Task C-4-4] GitHub Actions CI/CD** (`.github/workflows/deploy.yml`)
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /home/jjh0709/Project_2026_1
            git pull origin main
            docker-compose down
            docker-compose up -d --build
            echo "Deploy complete"
```

**[Task C-4-5] 앱 빌드** (EAS Build 사용)
```bash
# EAS CLI 설치
npm install -g eas-cli
eas login

# eas.json 설정
{
  "build": {
    "preview": {
      "android": { "buildType": "apk" }   # 내부 테스트용 APK
    },
    "production": {
      "android": { "buildType": "app-bundle" },
      "ios": { "simulator": false }
    }
  }
}

# 빌드 실행
eas build --platform android --profile preview
# → QR코드로 APK 다운로드 + 설치
```

**[Task C-4-6] 앱 스토어 배포 준비 (시간 여유 시)**
```
Android: Google Play Console → Internal Testing 트랙
iOS: App Store Connect → TestFlight 베타
→ 창업동아리 발표 심사위원에게 TestFlight 링크 공유
```

**[Task C-4-7] SSL 인증서 (Let's Encrypt)**
```bash
# Certbot으로 무료 SSL
docker run -it --rm \
  -v $(pwd)/nginx/ssl:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  -d carnerf.kr -d www.carnerf.kr
```

---

## 5. 최종 산출물 목록

| 산출물 | 경로 | 설명 |
|--------|------|------|
| 모바일 앱 | `mobile-app/` | React Native (Expo) |
| Dockerfile | `backend/Dockerfile` | 백엔드 컨테이너 |
| docker-compose | `docker-compose.yml` | 전체 스택 |
| Nginx 설정 | `nginx/nginx.conf` | 리버스 프록시 + SSL |
| CI/CD | `.github/workflows/deploy.yml` | 자동 배포 |
| APK 파일 | EAS Build URL | 안드로이드 앱 |

---

## 6. 팀장과 협업 포인트

```
팀장 (백엔드 API) → 팀원 C (모바일 앱) 연동:
  - API 엔드포인트 문서화 (Swagger: /docs)
  - CORS 설정 (모바일 앱 오리진 허용)
  - JWT 쿠키 → Authorization Bearer 헤더 방식으로 변경 (모바일 호환)

팀원 C (배포) → 전체 팀 지원:
  - 프로덕션 서버 URL 제공 (https://carnerf.kr)
  - 팀원 A, B 모델 파일 → Docker 볼륨으로 배포
  - 서버 모니터링 (CPU/GPU/메모리 대시보드)
```

---

## 7. 발표용 데모 시나리오

```
[심사위원 앞에서 앱 시연 - 3분]

1. 앱 실행 → 홈화면 (다크 테마, 3D 차량 배경)
   "안녕하세요, CarNeRF 앱입니다"

2. 매물 검색 탭 → 차량 선택
   "원하는 차량을 검색하고..."

3. 차량 상세 → "3D로 보기" 탭
   "손가락으로 직접 회전해보실 수 있습니다" (실제 조작)

4. AI 결함 리포트 스크롤
   "AI가 스크래치와 덴트를 자동 탐지했고, 종합 점수 37점입니다"

5. 예측 가격 확인
   "결함을 반영한 적정가는 2,420만원으로 예측됩니다"

6. 내 차 팔기 탭 → 카메라로 차량 촬영
   "지금 이 차를 찍어보겠습니다" (실시간 결함 분석)
```

---

## 8. 참고 자료

| 자료 | 링크 |
|------|------|
| Expo 공식 문서 | https://docs.expo.dev |
| Expo Router | https://expo.github.io/router |
| React Native Reanimated | https://docs.swmansion.com/react-native-reanimated |
| EAS Build | https://docs.expo.dev/build/introduction |
| Docker 공식 문서 | https://docs.docker.com |
| Let's Encrypt | https://letsencrypt.org |
| Nginx 설정 참고 | https://nginx.org/en/docs |
