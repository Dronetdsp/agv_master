# 🚀 로컬 개발 환경 실행 가이드

Docker 없이 직접 실행하는 방법입니다.

## 📋 필수 요구사항

### Backend
- Python 3.10 이상
- pip (Python 패키지 관리자)

### Frontend
- Node.js 18 이상
- npm 또는 yarn

---

## 🔧 Backend 실행

### 1. 가상환경 생성 및 활성화

**Linux/Mac:**
```bash
cd /home/user/agv_master/crack-detection-app/backend

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate
```

**Windows:**
```powershell
cd C:\path\to\crack-detection-app\backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
# .env 파일이 이미 생성되어 있습니다
cp ../.env .env  # 또는 수동으로 복사
```

### 4. 서버 실행

```bash
# 개발 모드 (핫 리로드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**접속:**
- API: http://localhost:8000
- API 문서: http://localhost:8000/api/v1/docs
- Health Check: http://localhost:8000/health

---

## 🎨 Frontend 실행

### 1. 의존성 설치

```bash
cd /home/user/agv_master/crack-detection-app/frontend

npm install
# 또는
yarn install
```

### 2. 개발 서버 실행

```bash
# Vite 개발 서버
npm run dev
# 또는
yarn dev
```

**접속:**
- Frontend: http://localhost:3000 (또는 5173)

---

## 🔥 빠른 실행 스크립트

### Backend 실행 스크립트 (start-backend.sh)

```bash
#!/bin/bash
cd /home/user/agv_master/crack-detection-app/backend

# 가상환경이 없으면 생성
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend 실행 스크립트 (start-frontend.sh)

```bash
#!/bin/bash
cd /home/user/agv_master/crack-detection-app/frontend

# 의존성이 설치되지 않았으면 설치
if [ ! -d "node_modules" ]; then
    npm install
fi

# 개발 서버 실행
npm run dev
```

### 실행 권한 부여 및 실행

```bash
chmod +x start-backend.sh start-frontend.sh

# 터미널 1
./start-backend.sh

# 터미널 2 (새 터미널)
./start-frontend.sh
```

---

## 🐛 문제 해결

### Backend 이슈

**1. 모듈을 찾을 수 없음**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**2. 포트 충돌 (8000 포트 사용 중)**
```bash
# 다른 포트 사용
uvicorn app.main:app --reload --port 8001
```

**3. Python 버전 문제**
```bash
# Python 버전 확인
python3 --version  # 3.10 이상 필요

# pyenv로 Python 버전 관리
pyenv install 3.10.0
pyenv local 3.10.0
```

### Frontend 이슈

**1. npm install 실패**
```bash
# 캐시 삭제 후 재설치
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**2. 포트 충돌**
```bash
# vite.config.ts에서 포트 변경
# server.port를 다른 번호로 수정
```

**3. Node.js 버전 문제**
```bash
# Node.js 버전 확인
node --version  # 18 이상 필요

# nvm으로 Node.js 버전 관리
nvm install 18
nvm use 18
```

---

## 🎯 프로덕션 빌드

### Backend 프로덕션 실행

```bash
# Gunicorn 설치
pip install gunicorn

# Gunicorn으로 실행
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend 프로덕션 빌드

```bash
cd frontend

# 빌드
npm run build

# 빌드된 파일은 dist/ 디렉토리에 생성됨
# 정적 파일 서버로 서빙
npx serve -s dist -p 3000
```

---

## 📊 동시 실행 (선택사항)

**concurrently 사용:**

```bash
# 루트 디렉토리에 package.json 추가
npm install -g concurrently

# 동시 실행 스크립트
concurrently \
  "cd backend && uvicorn app.main:app --reload" \
  "cd frontend && npm run dev"
```

---

## ✅ 실행 확인

### Backend 확인
```bash
curl http://localhost:8000/health
# 응답: {"status":"healthy","version":"2.0.0",...}
```

### Frontend 확인
브라우저에서 http://localhost:3000 접속

---

## 🔐 보안 참고사항

개발 환경에서만 사용하세요:
- DEBUG 모드는 프로덕션에서 비활성화
- SECRET_KEY는 강력한 키로 변경
- CORS 설정을 프로덕션 도메인으로 제한

---

**로컬 개발 환경이 준비되었습니다! 🎉**
