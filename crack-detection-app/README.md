# 🏗️ Crack Detection System

**최신 AI 기반 외벽 결함 자동 검출 및 분석 시스템**

Modern full-stack web application for automated crack detection and facade defect analysis using YOLOv8 and computer vision.

---

## ✨ 주요 기능 (Features)

### 🎯 핵심 기능
- **🔍 AI 기반 결함 검출**: YOLOv8 세그멘테이션 + 객체 검출
- **📊 정밀 계측**: Skeleton 기반 crack 길이/폭/면적 자동 측정
- **🎨 다중 결함 분류**: Crack, Spall, Rust, Rebar Exposure 등
- **📈 심각도 분석**: 자동 severity ranking 및 통계 분석
- **📑 리포트 생성**: PDF, HTML, CSV 자동 생성
- **⚙️ 개인 맞춤 설정**: 사용자별 설정 저장/로드

### 🚀 최신 기술 스택
#### Backend
- **FastAPI** - 비동기 고성능 API 서버
- **Pydantic v2** - 타입 안전 데이터 검증
- **SQLAlchemy** - ORM 및 DB 관리
- **Ultralytics YOLOv8** - 최신 객체 검출/세그멘테이션
- **OpenCV** - 이미지 처리 및 skeleton 추출

#### Frontend
- **React 18** - 최신 UI 라이브러리
- **TypeScript** - 타입 안전 개발
- **Vite** - 초고속 빌드 도구
- **TanStack Query** - 서버 상태 관리
- **Zustand** - 경량 전역 상태 관리
- **Tailwind CSS** - 유틸리티 기반 스타일링
- **React Dropzone** - 드래그 앤 드롭 업로드

#### DevOps
- **Docker** - 컨테이너화
- **Docker Compose** - 멀티 컨테이너 오케스트레이션
- **Nginx** - 리버스 프록시 및 정적 파일 서빙

---

## 📦 설치 방법 (Installation)

### 전제 조건 (Prerequisites)
- Docker & Docker Compose (권장)
- 또는 Python 3.10+ & Node.js 18+
- NVIDIA GPU (선택사항, CPU도 가능)

### 🐳 Docker를 사용한 설치 (권장)

1. **저장소 클론**
```bash
git clone <repository-url>
cd crack-detection-app
```

2. **환경 변수 설정**
```bash
cp .env.example .env
# .env 파일 편집 (모델 경로 등)
nano .env
```

3. **모델 경로 설정**
`docker-compose.yml` 파일에서 모델 디렉토리 마운트 경로 수정:
```yaml
volumes:
  - /your/model/path:/models:ro  # 실제 경로로 변경
```

4. **빌드 및 실행**
```bash
docker-compose up -d --build
```

5. **접속**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs

### 🖥️ 로컬 개발 환경 설정

#### Backend 설정
```bash
cd backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp ../.env.example .env
# .env 파일 수정

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend 설정
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

---

## 🎮 사용 방법 (Usage)

### 1. 이미지 업로드
- 웹 브라우저에서 http://localhost:3000 접속
- 건물/프로젝트 이름 입력
- 드래그 앤 드롭 또는 클릭으로 이미지 업로드

### 2. 분석 설정 (선택사항)
- **Image Size**: 입력 이미지 크기 (기본: 1024px)
- **Crack Confidence**: Crack 검출 신뢰도 임계값 (0-1)
- **Detection Confidence**: 기타 결함 검출 신뢰도 (0-1)
- **MM per Pixel**: 픽셀당 mm (GSD, 드론 고도에 따라 조정)
- **Min Box/Mask Size**: 최소 검출 크기 (노이즈 제거)

### 3. 분석 시작
- "Start Analysis" 버튼 클릭
- 실시간 진행 상황 모니터링

### 4. 결과 확인
- **통계 요약**: 총 이미지 수, 결함 수, 평균 심각도
- **결함 유형별 분석**: Crack, Spall, Rust 등 분류별 통계
- **상위 심각 결함**: 이미지별 가장 심각한 결함 자동 선별
- **리포트 다운로드**: PDF, HTML 형식

---

## 📁 프로젝트 구조

```
crack-detection-app/
├── backend/                # FastAPI 백엔드
│   ├── app/
│   │   ├── api/           # API 엔드포인트
│   │   │   └── endpoints/
│   │   │       ├── inference.py
│   │   │       └── preferences.py
│   │   ├── core/          # 핵심 설정
│   │   │   └── config.py
│   │   ├── models/        # DB 모델
│   │   ├── schemas/       # Pydantic 스키마
│   │   │   └── inference.py
│   │   ├── services/      # 비즈니스 로직
│   │   │   ├── inference_service.py
│   │   │   └── report_service.py
│   │   └── main.py        # FastAPI 앱
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/              # React 프론트엔드
│   ├── src/
│   │   ├── components/    # UI 컴포넌트
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ConfigPanel.tsx
│   │   │   └── ProgressBar.tsx
│   │   ├── pages/         # 페이지
│   │   │   ├── HomePage.tsx
│   │   │   └── ResultsPage.tsx
│   │   ├── services/      # API 서비스
│   │   │   └── api.ts
│   │   ├── stores/        # 상태 관리
│   │   │   └── useAppStore.ts
│   │   ├── types/         # TypeScript 타입
│   │   │   └── api.ts
│   │   ├── lib/           # 유틸리티
│   │   │   └── utils.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml     # Docker Compose 설정
├── .env.example           # 환경 변수 예제
└── README.md
```

---

## ⚙️ 환경 변수 설정

`.env` 파일에서 다음 변수들을 설정하세요:

```bash
# Backend
DEBUG=false
HOST=0.0.0.0
PORT=8000

# ML Models (실제 경로로 변경)
DEFAULT_CRACK_MODEL=/models/yolov8s_crack_seg4/weights/best.pt
DEFAULT_DET_MODEL=/models/merged_unified6_a10012/weights/best.pt

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB

# Default Parameters
DEFAULT_IMGSZ=1024
DEFAULT_CRACK_CONF=0.25
DEFAULT_DET_CONF=0.35
DEFAULT_MM_PER_PIXEL=1.0
```

---

## 🔧 API 문서

API 자동 문서는 다음 URL에서 확인 가능:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

### 주요 엔드포인트

#### 📤 이미지 업로드
```
POST /api/v1/inference/upload
```

#### 🚀 분석 시작
```
POST /api/v1/inference/start
```

#### 📊 상태 확인
```
GET /api/v1/inference/status/{task_id}
```

#### 💾 사용자 설정
```
GET/POST /api/v1/preferences/
```

---

## 🎨 사용자 인터페이스

### 주요 화면
1. **홈 페이지**: 이미지 업로드 및 설정
2. **결과 페이지**: 실시간 진행 상황 및 분석 결과
3. **통계 대시보드**: 결함 유형별 통계 및 차트
4. **심각 결함 뷰어**: Top K 심각 결함 상세 정보

### 기능
- ✅ 드래그 앤 드롭 파일 업로드
- ✅ 실시간 진행률 표시 (2초마다 폴링)
- ✅ 다크/라이트 모드 전환
- ✅ 반응형 디자인 (모바일/태블릿/데스크톱)
- ✅ 설정 저장/로드 (로컬 스토리지)

---

## 🚀 배포 (Deployment)

### Docker를 사용한 프로덕션 배포

1. **환경 변수 설정**
```bash
# 프로덕션 환경 변수
export DEBUG=false
export SECRET_KEY="강력한-시크릿-키-생성"
```

2. **빌드 및 실행**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Nginx 리버스 프록시 설정** (선택사항)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🧪 테스트

### Backend 테스트
```bash
cd backend
pytest tests/
```

### Frontend 테스트
```bash
cd frontend
npm run test
```

---

## 📊 성능 최적화

### 권장 사항
- **GPU 사용**: NVIDIA GPU가 있을 경우 CUDA 설정
- **배치 처리**: 여러 이미지 동시 처리
- **캐싱**: Redis를 사용한 결과 캐싱
- **CDN**: 정적 파일 CDN 배포

---

## 🔒 보안

- ✅ CORS 설정
- ✅ 파일 크기 제한 (100MB)
- ✅ 파일 타입 검증 (이미지만)
- ⚠️ 프로덕션 환경에서는 HTTPS 필수
- ⚠️ 인증/인가 시스템 추가 권장

---

## 🐛 문제 해결 (Troubleshooting)

### Docker 빌드 실패
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache
```

### 모델 경로 오류
- `docker-compose.yml`의 volume 경로 확인
- `.env` 파일의 모델 경로 확인

### 프론트엔드 연결 오류
- Backend가 실행 중인지 확인: http://localhost:8000/health
- CORS 설정 확인

---

## 📝 라이선스

This project is licensed under the MIT License.

---

## 👥 기여 (Contributing)

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📧 문의

프로젝트 관련 문의사항은 이슈 트래커를 이용해주세요.

---

## 🙏 감사의 말

- **Ultralytics YOLOv8**: 강력한 객체 검출 프레임워크
- **FastAPI**: 현대적인 Python 웹 프레임워크
- **React**: 훌륭한 UI 라이브러리

---

**Built with ❤️ using modern web technologies**
