#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Python dependency installation for DynamoDB FinanceBot..."

# Check if virtual environment exists, if not, create it
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

echo "🔄 Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

echo "Installing core dependencies..."
pip install fastapi==0.115.6 uvicorn[standard]==0.32.1 python-multipart==0.0.12

echo "Installing AWS DynamoDB dependencies..."
pip install boto3==1.35.89 botocore==1.35.89

echo "Installing authentication dependencies..."
pip install python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4

echo "Installing AI/ML Services dependencies..."
pip install openai==1.58.1 pinecone-client==3.2.2

echo "Installing data validation dependencies..."
pip install pydantic==2.10.4 pydantic-settings==2.7.0 email-validator==2.2.0

echo "Installing HTTP Client dependencies..."
pip install httpx==0.28.1

echo "Installing utilities..."
pip install python-dotenv==1.0.1

echo "Installing monitoring and logging dependencies..."
pip install structlog==24.4.0

echo "Installing development dependencies..."
pip install pytest==8.3.4 pytest-asyncio==0.24.0 black==24.10.0 isort==5.13.2 flake8==7.1.1

echo "✅ All Python dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "1. Start DynamoDB Local: docker-compose -f docker-compose.dev.yml up -d"
echo "2. Initialize tables: python scripts/init_dynamodb.py"
echo "3. Start the FastAPI app: python -m uvicorn app.main:app --reload"
echo ""
echo "To deactivate the virtual environment, run: deactivate"
