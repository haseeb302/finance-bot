# FinanceBot with DynamoDB

This version of FinanceBot uses Amazon DynamoDB for scalable, serverless database operations.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
./install_deps.sh
```

### 2. Start DynamoDB Local

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Initialize Tables

```bash
source venv/bin/activate
python scripts/init_dynamodb.py
```

### 4. Start the Application

```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

## 🗄️ Database Schema

### Tables Created:

- **financebot-users**: User accounts and authentication
- **financebot-chats**: Chat sessions and metadata
- **financebot-messages**: Individual chat messages

### Key Design:

- **Partition Key**: `chat_id` for messages (enables fast message retrieval)
- **Sort Key**: `timestamp_message_id` for messages (enables chronological ordering)
- **Global Secondary Indexes**: For efficient queries by user_id

## 🔧 Configuration

### Environment Variables (.env.local):

```bash
# DynamoDB Configuration
DYNAMODB_ENDPOINT_URL=http://localhost:8000  # Local development
DYNAMODB_REGION=us-east-1
DYNAMODB_ACCESS_KEY=local
DYNAMODB_SECRET_KEY=local
DYNAMODB_TABLE_PREFIX=financebot

# JWT Configuration
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=financebot-embeddings
```

## 🌐 Production Deployment

### AWS DynamoDB Setup:

1. Create DynamoDB tables in AWS Console
2. Set up IAM roles with appropriate permissions
3. Update environment variables:
   ```bash
   DYNAMODB_ENDPOINT_URL=https://dynamodb.us-east-1.amazonaws.com
   DYNAMODB_ACCESS_KEY=your-aws-access-key
   DYNAMODB_SECRET_KEY=your-aws-secret-key
   ```

### Docker Deployment:

```bash
# Build and run with Docker
docker-compose up -d
```

## 📊 Monitoring

- **DynamoDB Admin UI**: http://localhost:8001 (when running locally)
- **DynamoDB Local**: http://localhost:8000
- **FastAPI Docs**: http://localhost:8000/docs

## 🔍 Key Benefits

1. **Scalability**: Auto-scales with traffic
2. **Performance**: Single-digit millisecond latency
3. **Cost**: Pay-per-request pricing
4. **Reliability**: 99.99% availability
5. **No Connection Pooling**: Handles millions of concurrent requests

## 🛠️ Development Tools

- **DynamoDB Local**: For local development
- **DynamoDB Admin**: Web UI for table management
- **AWS CLI**: For production operations
- **boto3**: Python SDK for DynamoDB operations

## 📝 Notes

- Tables are created automatically on first run
- Data is stored in-memory for local development
- Production uses AWS DynamoDB with persistent storage
- All operations are asynchronous for better performance
