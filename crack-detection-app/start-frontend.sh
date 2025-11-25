#!/bin/bash
set -e

echo "🎨 Starting Crack Detection Frontend..."

cd "$(dirname "$0")/frontend"

# node_modules가 없으면 설치
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✅ Dependencies already installed"
fi

echo ""
echo "✨ Frontend is starting..."
echo "🌐 URL: http://localhost:3000"
echo "🔥 Vite Dev Server with Hot Module Replacement"
echo ""

# 개발 서버 실행
npm run dev
