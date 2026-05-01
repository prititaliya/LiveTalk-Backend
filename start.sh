#!/bin/bash

# LiveTalk - Start All Services
# This script starts the backend API, LiveKit agent, and frontend concurrently

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting LiveTalk Services...${NC}\n"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [ ! -d "Backend" ] || [ ! -d "Frontend" ]; then
    echo -e "${YELLOW}❌ Error: Please run this script from the LiveTalk root directory${NC}"
    exit 1
fi

# Start Backend API Server
echo -e "${GREEN}📡 Starting Backend API Server (port 8000)...${NC}"
cd Backend
# Try uvicorn first, fallback to python
if command -v uvicorn &> /dev/null; then
    uvicorn api:app --host 0.0.0.0 --port 8000 &
else
    python api.py &
fi
API_PID=$!
cd ..

# Wait a moment for API to start
sleep 2

# Start LiveKit Agent
echo -e "${GREEN}🤖 Starting LiveKit Agent...${NC}"
cd Backend
python main.py &
AGENT_PID=$!
cd ..

# Wait a moment for agent to initialize
sleep 2

# Start Frontend
echo -e "${GREEN}🌐 Starting Frontend (port 3000)...${NC}"
cd Frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "\n${BLUE}✅ All services started!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Backend API:${NC}    http://localhost:8000"
echo -e "${GREEN}Frontend:${NC}       http://localhost:3000"
echo -e "${GREEN}API Health:${NC}     http://localhost:8000/health"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all background jobs
wait

