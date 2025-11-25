#!/bin/bash
set -e

echo "🚀 Starting Crack Detection Backend..."

cd "$(dirname "$0")/backend"

# 가상환경이 없으면 생성
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv

    echo "📥 Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "✅ Virtual environment found"
    source venv/bin/activate
fi

# 데이터 디렉토리 생성
echo "📁 Creating data directories..."
mkdir -p uploads outputs user_preferences

# .env 파일 확인
if [ ! -f "../.env" ]; then
    echo "⚠️  .env file not found! Copying from .env.example..."
    cp ../.env.example ../.env
fi

echo ""
echo "✨ Backend is starting..."
echo "📍 API: http://localhost:8000"
echo "📚 Docs: http://localhost:8000/api/v1/docs"
echo "❤️  Health: http://localhost:8000/health"
echo ""

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
