# 🚀 GitHub 레포지토리 연결 가이드

새로운 독립 Git 레포지토리가 생성되었습니다!

## ✅ 현재 상태
- **로컬 레포지토리**: `/home/user/agv_master/crack-detection-app`
- **브랜치**: `main`
- **커밋**: 1개 (Initial commit)
- **파일**: 37개, 3,469줄

---

## 📋 GitHub에 푸시하는 방법

### 1️⃣ GitHub에서 새 레포지토리 생성

1. https://github.com/new 접속
2. Repository name: `crack-detection-system` (또는 원하는 이름)
3. Description: "AI-Powered Crack Detection Web Application"
4. **중요**: `Initialize this repository with` 옵션들을 **모두 체크 해제**
5. "Create repository" 클릭

### 2️⃣ 원격 저장소 연결 및 푸시

GitHub에서 레포지토리를 생성하면 아래와 같은 명령어가 표시됩니다:

```bash
cd /home/user/agv_master/crack-detection-app

# 원격 저장소 추가 (HTTPS)
git remote add origin https://github.com/YOUR_USERNAME/crack-detection-system.git

# 또는 SSH (추천)
git remote add origin git@github.com:YOUR_USERNAME/crack-detection-system.git

# 푸시
git push -u origin main
```

### 3️⃣ 확인

```bash
# 원격 저장소 확인
git remote -v

# 브랜치 확인
git branch -a
```

---

## 🔧 대안: GitHub CLI 사용 (빠른 방법)

```bash
cd /home/user/agv_master/crack-detection-app

# GitHub CLI로 레포지토리 생성 및 푸시
gh repo create crack-detection-system \
  --public \
  --source=. \
  --remote=origin \
  --push

# 또는 private 레포지토리
gh repo create crack-detection-system \
  --private \
  --source=. \
  --remote=origin \
  --push
```

---

## 📝 추가 설정 (선택사항)

### README Badge 추가

GitHub 레포지토리에 푸시한 후, README.md 상단에 배지 추가:

```markdown
# 🏗️ Crack Detection System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![React](https://img.shields.io/badge/react-18.0+-61dafb.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.0+-3178c6.svg)
![Docker](https://img.shields.io/badge/docker-ready-2496ed.svg)
```

### GitHub Actions CI/CD (향후 추가 가능)

`.github/workflows/ci.yml` 파일을 만들어 자동 빌드/테스트:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build with Docker
        run: docker-compose build
```

---

## 🎉 완료!

이제 독립적인 Git 레포지토리로 관리할 수 있습니다.

### 다음 단계
1. GitHub에 새 레포지토리 생성
2. 원격 저장소 연결
3. `git push -u origin main`
4. 팀원들과 공유!

---

## 💡 Tip

나중에 원격 저장소를 변경하려면:

```bash
# 현재 원격 저장소 제거
git remote remove origin

# 새 원격 저장소 추가
git remote add origin <새로운-저장소-URL>

# 푸시
git push -u origin main
```
