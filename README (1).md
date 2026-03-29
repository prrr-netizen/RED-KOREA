# ☁️ Cloud Vend Web — 멀티테넌트 디지털 상품 자동판매 SaaS

> **holysharry.co** 기반의 Flask 멀티테넌트 쇼핑몰 플랫폼  
> 각 쇼핑몰이 서브도메인(`shop.your-domain.com`) 형태로 독립 운영됩니다.

---

## 📋 주요 기능

- 🏪 **멀티테넌트 쇼핑몰** — 서브도메인별 독립 쇼핑몰
- 👥 **등급제 회원 관리** — 일반 / 바이어 / VIP / VVIP / 리셀러 / 관리자
- 💳 **자동 입금 처리** — 카카오뱅크 / 토스 실시간 입금 감지 (PushBullet 연동)
- 🎫 **컬처랜드 충전** — 문화상품권 자동 처리
- 📱 **SMS OTP 인증** — Twilio 연동
- 🔔 **Discord 알림** — 입금 / 충전 / 구매 완료 알림
- 🔑 **라이선스 시스템** — 쇼핑몰별 유효기간 관리
- 🚫 **IP 차단 시스템** — ban.db 기반

---

## 🗂️ 프로젝트 구조

```
├── main.py           # Flask 메인 서버 (5,100+ 줄, 60+ API 라우트)
├── push.py           # 은행 자동입금 처리 서버 (포트 4040)
├── codegen.py        # 라이선스 키 생성 CLI 툴
├── randomstring.py   # 랜덤 문자열 생성 유틸
├── wsgi.py           # WSGI 진입점
├── server.wsgi       # uWSGI 설정
├── default           # Nginx 설정 파일
├── .env.example      # 환경변수 예시
├── requirements.txt  # Python 의존성
└── README.md
```

---

## ⚙️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 실제 값으로 수정
```

### 3. 서버 실행
```bash
# 개발 서버
python wsgi.py

# 프로덕션 (uWSGI)
uwsgi --ini server.wsgi

# 은행 자동입금 서버 (별도 실행)
python push.py
```

### 4. 라이선스 키 생성
```bash
python codegen.py
# 생성 기간(일) 및 생성 개수 입력
```

---

## 🗄️ 데이터베이스 구조

| 파일 | 설명 |
|------|------|
| `license.db` | 라이선스 키 관리 |
| `push.db` | 은행 알림 중복처리 방지 |
| `ban.db` | IP 차단 목록 |
| `database/<shopname>.db` | 각 쇼핑몰별 데이터 (자동 생성) |

---

## 🌐 API 주요 라우트

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/<name>/` | GET | 쇼핑몰 메인 |
| `/<name>/login` | GET/POST | 로그인 |
| `/<name>/register` | GET/POST | 회원가입 |
| `/<name>/shop` | GET | 상품 목록 |
| `/<name>/buy` | POST | 구매 |
| `/<name>/charge` | GET/POST | 잔액 충전 |
| `/<name>/admin/` | GET | 관리자 대시보드 |
| `/api` | POST | 은행 입금 처리 (push.py) |

---

## 🔧 Nginx 설정

`default` 파일을 `/etc/nginx/sites-available/default`에 복사 후  
Flask uWSGI 연동 설정 추가:

```nginx
location / {
    include uwsgi_params;
    uwsgi_pass unix:/tmp/flask.sock;
}
```

---

## ⚠️ 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요
- `*.db` 파일은 `.gitignore`에 포함되어 있습니다
- 프로덕션 배포 시 `SECRET_KEY`를 고정된 안전한 값으로 설정하세요
- Twilio / Discord Webhook URL은 반드시 환경변수로 관리하세요

---

## 📄 라이선스

Private Project — 무단 배포 금지