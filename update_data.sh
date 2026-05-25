#!/bin/bash

echo "Starting EquityAI Daily Data Update..."

cd backend-ai
source .venv/bin/activate

python scripts/update_daily_data.py

echo "Done! You can now start the backend server."
