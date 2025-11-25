# 🚀 빠른 시작 가이드 (Quick Start Guide)

## 5분 안에 시작하기

### 1️⃣ Docker 설치 확인
```bash
docker --version
docker-compose --version
```

### 2️⃣ 프로젝트 준비
```bash
cd crack-detection-app
cp .env.example .env
```

### 3️⃣ 모델 경로 설정
`docker-compose.yml` 파일 수정:
```yaml
volumes:
  # 실제 모델이 저장된 경로로 변경
  - /media/dev/Data/aihub_building_defect/workspace:/models:ro
```

### 4️⃣ 실행
```bash
docker-compose up -d
```

### 5️⃣ 접속
브라우저에서 http://localhost:3000 열기

---

## 📝 첫 번째 분석 실행

1. **건물 이름 입력**: "Test Building"
2. **이미지 업로드**: 드래그 앤 드롭으로 이미지 추가
3. **설정 확인** (선택사항):
   - Image Size: 1024 (기본값)
   - Confidence: 0.25 / 0.35 (기본값)
4. **Start Analysis** 클릭
5. **결과 확인**: 자동으로 결과 페이지 이동

---

## 🛠️ 문제 해결

### Backend가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose logs backend

# 컨테이너 재시작
docker-compose restart backend
```

### Frontend 연결 오류
```bash
# Backend 상태 확인
curl http://localhost:8000/health

# Frontend 재빌드
docker-compose up -d --build frontend
```

### 전체 재시작
```bash
docker-compose down
docker-compose up -d --build
```

---

## 📊 테스트 데이터

테스트용 샘플 이미지가 필요한 경우:
1. 건물 외벽 사진 준비 (JPG, PNG)
2. 최소 해상도: 640x640
3. 권장 해상도: 1920x1080 이상

---

## 🔧 개발 모드

개발 중 핫 리로드가 필요한 경우:

```bash
# Backend 개발 모드
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend 개발 모드
cd frontend
npm install
npm run dev
```

---

## 📞 도움말

- 전체 문서: [README.md](README.md)
- API 문서: http://localhost:8000/api/v1/docs
- 이슈 리포트: GitHub Issues

**Happy Analyzing! 🎉**
