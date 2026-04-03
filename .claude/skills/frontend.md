# Frontend Skill

## 역할
Jinja2 템플릿, Tailwind CSS, JS 프론트엔드 관리

## 페이지 구조
| 경로 | 템플릿 | 기능 |
|------|--------|------|
| / | home.html | 히어로, 3D 데모, 인기매물, CTA |
| /listings | listings.html | 검색, 필터, 정렬, 페이지네이션 |
| /vehicles/{id} | vehicle_detail.html | 3D뷰어, AI진단, 시세, 후기, 찜 |
| /sell | sell.html | 5단계 매물등록, 3D스캔 진행UI |
| /login | login.html | 로그인/회원가입, 비밀번호 강도 |
| /mypage | mypage.html | 프로필, 매물관리, 찜, 로그인기록 |
| /viewer/{id} | viewer.html | 전체화면 3D 뷰어 |

## 디자인 시스템
CSS Variables: `--bg, --surface, --sur2, --border, --accent(#0EA5E9), --text, --muted`
다크모드 기본, `html:not(.dark)`로 라이트 오버라이드

## JS 파일
- `sell.js` - 이미지업로드, 3D스캔 폴링, 폼 제출
- `viewer.js` - GaussianSplats3D 뷰어, 결함 마커 시스템
- `listings.js` - 필터/정렬 (인라인)
