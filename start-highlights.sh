#!/bin/bash

# Quick start script for Sports Highlight Channel
# This script helps you start both backend and frontend for user testing

set -e

echo "🚀 Starting Sports Highlight Channel for User Testing"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check PostgreSQL
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is running${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not running${NC}"
    echo "   Start it with: brew services start postgresql@14"
    exit 1
fi

# Check uv
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✅ uv is installed${NC}"
else
    echo -e "${RED}❌ uv is not installed${NC}"
    echo "   Install with: pip install uv"
    exit 1
fi

# Check pnpm
if command -v pnpm &> /dev/null; then
    echo -e "${GREEN}✅ pnpm is installed${NC}"
else
    echo -e "${RED}❌ pnpm is not installed${NC}"
    echo "   Install with: npm install -g pnpm"
    exit 1
fi

# Check .env files
if [ -f "services/theory-engine-api/.env" ]; then
    echo -e "${GREEN}✅ Backend .env file exists${NC}"
else
    echo -e "${RED}❌ Backend .env file missing${NC}"
    echo "   Create it from .env.example"
    exit 1
fi

if [ -f "apps/highlights-web/.env.local" ]; then
    echo -e "${GREEN}✅ Frontend .env.local file exists${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend .env.local missing - creating it...${NC}"
    echo "NEXT_PUBLIC_THEORY_ENGINE_URL=http://localhost:8000" > apps/highlights-web/.env.local
    echo -e "${GREEN}✅ Created .env.local${NC}"
fi

echo ""
echo "📦 Setting up dependencies..."

# Setup backend
echo "   Setting up backend dependencies..."
cd services/theory-engine-api
if [ ! -d ".venv" ]; then
    echo "   Installing Python dependencies..."
    uv sync
    uv pip install -e ../../packages/py-core
fi

# Check if migrations needed
echo "   Checking database migrations..."
if ! alembic current > /dev/null 2>&1; then
    echo "   Running database migrations..."
    alembic upgrade head
else
    echo "   Database is up to date"
fi

cd ../..

# Setup frontend
echo "   Setting up frontend dependencies..."
if [ ! -d "node_modules" ]; then
    echo "   Installing Node.js dependencies..."
    pnpm install
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "🚀 Starting services..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 INSTRUCTIONS:"
echo ""
echo "This script will start both backend and frontend in separate processes."
echo "You'll need TWO terminal windows:"
echo ""
echo "TERMINAL 1 - Backend:"
echo "  cd services/theory-engine-api"
echo "  uv run uvicorn app.main:app --reload --port 8000"
echo ""
echo "TERMINAL 2 - Frontend:"
echo "  cd apps/highlights-web"
echo "  cd apps/highlights-web"
echo "  pnpm dev"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Once both are running:"
echo "  🌐 Frontend: http://localhost:3005"
echo "  🔧 Backend API: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop this script (services will keep running)"
echo ""

# Ask if user wants to start services now
read -p "Start backend server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Starting backend server..."
    echo "   (Press Ctrl+C to stop)"
    echo ""
    cd services/theory-engine-api
    uv run uvicorn app.main:app --reload --port 8000
fi

