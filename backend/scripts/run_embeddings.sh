#!/bin/bash

# Script to process content files and populate Pinecone with embeddings
echo "🚀 Starting Content Processing and Embedding Population"
echo "======================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run install_deps.sh first."
    exit 1
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ .env.local file not found. Please create it with your API keys."
    exit 1
fi

# Check if content directory exists
if [ ! -d "content" ]; then
    echo "❌ Content directory not found. Please create content files first."
    exit 1
fi

# Check if content files exist
if [ ! "$(ls -A content/*.txt 2>/dev/null)" ]; then
    echo "❌ No .txt files found in content directory."
    exit 1
fi

# Run the content processing script
echo "📚 Processing content files and creating embeddings..."
python scripts/run_embeddings.py

echo "✅ Content processing completed!"
echo ""
echo "Next steps:"
echo "1. Test your chat functionality"
echo "2. The knowledge base is now ready for RAG queries"
echo "3. Each vector includes category metadata for filtering"
