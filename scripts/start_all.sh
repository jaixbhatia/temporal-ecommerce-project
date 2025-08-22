#!/bin/bash

# Colors for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the repository root directory (one level up from scripts/)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Activate virtual environment
echo -e "${BLUE}Activating Python virtual environment...${NC}"
source "$REPO_ROOT/env/bin/activate"

# Verify Python and pip are working
echo -e "${BLUE}Checking Python setup...${NC}"
python --version
pip --version

echo -e "${BLUE}Starting E-commerce Workflow Infrastructure...${NC}"

# 1. Stop any existing containers and clean volumes
echo -e "${BLUE}Cleaning up existing containers...${NC}"
docker compose down -v

# 2. Start infrastructure
echo -e "${BLUE}Starting Temporal and PostgreSQL...${NC}"
docker compose up -d

# 3. Wait for services to be ready
echo -e "${BLUE}Waiting for services to initialize...${NC}"
sleep 5

# 4. Start worker in background
echo -e "${BLUE}Starting Temporal worker...${NC}"
python run_worker.py &
WORKER_PID=$!

# 5. Start API
echo -e "${BLUE}Starting FastAPI server...${NC}"
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000

# 6. Cleanup on exit
trap 'kill $WORKER_PID' EXIT
