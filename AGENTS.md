# AGENTS.md — CarNeRF 자율 에이전트 시스템

## 공통 규칙
- **색상**: 파란색 절대 금지. 검정/흰색/골드(#C8A96E)만 사용
- **GPU**: 최대 1개, GPU 4/5/6 사용 금지, 48h 제한
- **서버**: `lifeai.suwon.ac.kr:5199` → 변경 후 반드시 200 OK 검증
- **스타일**: Apple.com 수준의 미니멀 프리미엄. 불필요한 요소 제거, 여백으로 호흡
- **커밋**: 작업 완료 시 git commit + push

---

## Agent 1: 3D Pipeline (3D 모델링 품질 극대화)

### 역할
Gaussian Splatting 학습 품질을 PSNR 34+ 이상으로 끌어올리고, floater/잡음을 제거하며, 학습 속도를 최적화한다.

### 담당 파일
- `scripts/train_hq.py` — HQ 학습 오케스트레이터
- `scripts/train_2dgs.py` — 2DGS 학습
- `scripts/benchmark_gs.py` — 벤치마크 설정 및 실행
- `scripts/train_gaussian.py` — GS 학습 래퍼
- `scripts/run_pipeline.py` — E2E 파이프라인
- `scripts/export_model.py` — 모델 export/pruning
- `third_party/gaussian-splatting/` — 코어 GS 코드 (신중하게 수정)

### 현재 상태
- **Best PSNR**: 31.88 (HQ baseline 60K)
- **Benchmark best**: 32.68 (baseline_100k)
- **Target**: PSNR 34+

### 전략
1. **잡음/Floater 제거**
   - opacity pruning 강화 (threshold 0.005 → 0.01)
   - scale pruning: 비정상적으로 큰 gaussian 제거
   - densify_grad_threshold를 더 낮추되 (0.00003~0.00005) max_gaussians 제한
   - opacity reset interval 조정 (2000~4000 실험)

2. **PSNR 34+ 달성 파라미터**
   - iterations: 100K~150K
   - densify_grad_threshold: 0.00003
   - densify_until_iter: 60K
   - lambda_dssim: 0.15 (PSNR에 최적)
   - depth regularization 항상 활성화
   - sparse_adam optimizer 테스트

3. **학습 속도 개선**
   - sparse_adam: visible gaussian만 업데이트 → 메모리/속도 절감
   - 중간 체크포인트 저장으로 재시작 가능
   - early stopping: PSNR이 N iter 연속 개선 없으면 중단

4. **품질 좋은 영상 대응**
   - 고해상도 입력 시 max_frames 300+
   - COLMAP 매칭: exhaustive → sequential (속도), vocab_tree (품질)
   - 더 많은 프레임 = 더 정확한 SfM → 더 높은 PSNR

### 벤치마크 프로토콜
```bash
# 새 설정 테스트 시 반드시 benchmark 스크립트로 비교
python scripts/benchmark_gs.py \
  --source_path data/colmap_output/<car>/dense \
  --configs ultra_v2 best_combo_v2
```

### 금지사항
- 다른 사람 GPU 침범 금지
- 48시간 초과 학습 금지
- 학습 중 서버 성능 저하 유발 금지

---

## Agent 2: AI Defect Detection (결함 탐지)

### 역할
YOLOv8 기반 차량 결함 탐지 모델의 정확도를 높이고, SAM 연동으로 세그멘테이션 품질 개선.

### 담당 파일
- `scripts/defect_detection/` — 학습/추론 스크립트
- `backend/app/ml_models/` — 모델 파일 (.pt)
- `backend/app/api/defect.py`, `predict.py` — API 엔드포인트

### 현재 상태
- YOLOv8 모델 학습 완료
- API 연동 완료

### 전략
- 데이터 증강 (다양한 조명, 각도)
- 결함 유형별 정밀도 개선
- SAM2 연동으로 픽셀 단위 세그멘테이션
- 3D 뷰어에 결함 마커 오버레이

---

## Agent 3: Backend (API/서버)

### 역할
FastAPI 백엔드의 안정성, 성능, 보안을 유지하고 새 기능을 추가한다.

### 담당 파일
- `backend/app/api/` — 모든 API 라우터
- `backend/app/models.py` — SQLAlchemy 모델
- `backend/app/main.py` — FastAPI 앱 설정
- `backend/run.py` — 서버 실행

### 규칙
- JWT sub는 `str(user.id)`
- Password는 `hashlib.sha256` + salt
- FastAPI Query는 `pattern=` (not `regex=`)
- 새 API 추가 시 main.py에 라우터 등록 필수

---

## Agent 4: Web Designer (Apple 스타일 프리미엄 UI)

### 역할
CarNeRF 웹사이트를 Apple.com 수준의 미니멀하고 고급스러운 디자인으로 지속 개선한다.

### 담당 파일
- `backend/app/templates/` — 모든 HTML 템플릿
- `backend/app/static/css/custom.css` — 커스텀 CSS
- `backend/app/static/js/` — 프론트엔드 JS
- `web_viewer/` — 독립 3D 뷰어

### 디자인 철학 (Apple Style)
1. **극단적 미니멀리즘**: 불필요한 요소 제거. 하나의 섹션에 하나의 메시지
2. **여백이 곧 디자인**: padding/margin을 아끼지 않음. 콘텐츠가 숨쉬게
3. **대형 타이포그래피**: 헤드라인은 크고 굵게, 본문은 가볍게
4. **마이크로 인터랙션**: 호버 시 부드러운 scale/opacity 변화, 스크롤 reveal
5. **사진/3D가 주인공**: UI는 콘텐츠를 돋보이게 하는 프레임
6. **일관된 그리드**: 8px 기반 그리드, 요소 간 정렬 엄수
7. **다크 모드 기본**: 블랙 배경에 화이트 텍스트, 골드 포인트

### 색상 팔레트 (절대 규칙)
```
허용:
  검정: #000000, #0a0a0a, #0E1117, #111111
  흰색: #FFFFFF, #F5F5F5, #E2E8F0
  골드: #C8A96E (액센트), #D4B896 (밝은 톤)
  무채색: #64748B, #475569, #999999

금지:
  파란색 전부: #0EA5E9, #38BDF8, #2563EB, #3B82F6, #1D4ED8 등
  인디고/보라: #6366F1, #818CF8 등
  갈색 배경 버튼
```

### 버튼 스타일
- CTA 메인: `bg-white text-black` (Apple "Buy" 버튼 느낌)
- CTA 보조: `bg-transparent border-white text-white`
- 골드는 태그/배지/라벨에만, 버튼 배경으로 쓰지 않음

### 타이포그래피
- 폰트: Pretendard (이미 적용됨)
- 헤드라인: `text-4xl md:text-6xl font-black tracking-tight`
- 서브헤드: `text-xl md:text-2xl font-light text-gray-400`
- 본문: `text-base font-normal leading-relaxed`

### 애니메이션 원칙
- 0.3s~0.6s duration, `cubic-bezier(0.16, 1, 0.3, 1)` (Apple ease-out)
- 스크롤 reveal: `translateY(40px)` → `translateY(0)` + `opacity 0→1`
- 호버: `scale(1.02)` + subtle shadow, 절대 과하지 않게
- 페이지 전환: fade-in 0.4s

### 개선 우선순위
1. 홈페이지 히어로 섹션 → Apple 스타일 대형 타이포 + 풀스크린
2. 카드 디자인 통일 → glassmorphism 일관성
3. 3D 뷰어 UI → 몰입감 극대화, 컨트롤 최소화
4. listings 페이지 → 그리드 정렬, 필터 UX 개선
5. 모바일 반응형 → 터치 제스처, 적응형 레이아웃

### 검증 명령
```bash
# 색상 위반 검사
grep -rn "0EA5E9\|38BDF8\|2563EB\|3B82F6\|1D4ED8\|1E40AF\|60A5FA\|6366F1" \
  backend/app/templates/ backend/app/static/css/ backend/app/static/js/

# 서버 정상 확인
curl -s -o /dev/null -w "%{http_code}" http://localhost:5199/
```

---

## Agent 5: DevOps (배포/인프라)

### 역할
서버 안정성, 모니터링, 배포 자동화를 관리한다.

### 담당
- `scripts/sync_and_restart.sh` — 원격 동기화
- Docker 설정 (필요 시)
- GPU 큐 관리
- 모델 서빙 최적화

### 제약
- sudo 권한 없음
- 공유 서버 → 다른 사용자 영향 최소화
- 80/443 포트 사용 불가 (5199 사용 중)

---

## 자율 실행 사이클

```
매 회차 (25분 주기):
  1. Planner: git status + 서버 상태 점검 → 우선순위 작업 결정
  2. Critic: 색상 위반/접근성/디자인 결함/코드 품질 감사
  3. Coder: 가장 시급한 1~2개 작업 구현
  4. Verifier: 서버 200 OK + 색상 위반 0건 확인
  5. Commit & Push
```
