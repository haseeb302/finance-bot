# FinanceBot with DynamoDB

A RAG-based financial chatbot built with FastAPI, DynamoDB, OpenAI, and Pinecone. Features JWT authentication, chat persistence, and scalable vector search for financial knowledge.

## 🏗️ Architecture

- **Backend**: FastAPI with async/await
- **Database**: Amazon DynamoDB (NoSQL)
- **Vector DB**: Pinecone for embeddings
- **LLM**: OpenAI GPT-4 for responses
- **Frontend**: React with TypeScript
- **Authentication**: JWT with refresh tokens
- **Deployment**: AWS (ECS/App Runner/EC2)

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API Key
- Pinecone API Key

### 1. Clone and Setup Backend

```bash
# Clone repository
git clone <repository-url>
cd FinanceBot/backend

# Install dependencies
./install_deps.sh

# Or manually:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env.local` file:

```bash
# DynamoDB Configuration (Local)
DYNAMODB_ENDPOINT_URL=http://localhost:8001
DYNAMODB_REGION=us-east-1
DYNAMODB_ACCESS_KEY=local
DYNAMODB_SECRET_KEY=local
DYNAMODB_TABLE_PREFIX=

# JWT Configuration
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=2
REFRESH_TOKEN_EXPIRE_MINUTES=5

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=your-pinecone-index-name

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:3000

# Pagination
DEFAULT_PAGE_SIZE=3
MAX_PAGE_SIZE=3
```

### 3. Start Local DynamoDB

```bash
# Start DynamoDB Local and Admin UI
docker-compose -f docker-compose.dev.yml up -d

# Verify services
curl http://localhost:8002  # DynamoDB Admin UI
curl http://localhost:8000  # DynamoDB Local
```

### 4. Initialize Database

```bash
source venv/bin/activate
python scripts/init_dynamodb.py
```

### 5. Populate Knowledge Base

```bash
# Create content embeddings in Pinecone
python scripts/run_embeddings.sh
```

### 6. Start Backend Server

```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Setup Frontend

```bash
# In new terminal
cd ../frontend
npm install
npm run dev
```

### 8. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **DynamoDB Admin**: http://localhost:8002

## 🗄️ Database Schema

### Tables Created:

- **users**: User accounts and authentication
- **chats**: Chat sessions and metadata
- **messages**: Individual chat messages
- **sessions**: User sessions and refresh tokens

### Key Design:

- **Partition Keys**: `user_id`, `chat_id`, `session_id`
- **Sort Keys**: `timestamp_message_id` for chronological ordering
- **GSIs**: For efficient queries by user_id
- **TTL**: Automatic cleanup of expired sessions

## 🌐 Production Deployment

### Option 1: AWS App Runner (Recommended)

#### 1. Prepare for Deployment

```bash
# Create production environment file
cp .env.local .env.production

# Update for production
DYNAMODB_ENDPOINT_URL=https://dynamodb.us-east-1.amazonaws.com
DYNAMODB_ACCESS_KEY=your-aws-access-key
DYNAMODB_SECRET_KEY=your-aws-secret-key
DYNAMODB_TABLE_PREFIX=
ALLOWED_ORIGINS=https://yourdomain.com
```

#### 2. Create App Runner Service

```yaml
# apprunner.yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - echo "Installing dependencies..."
      - pip install -r requirements.txt
run:
  runtime-version: 3.9.16
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000
  network:
    port: 8000
  env:
    - name: DYNAMODB_ENDPOINT_URL
      value: https://dynamodb.us-east-1.amazonaws.com
    - name: DYNAMODB_REGION
      value: us-east-1
    - name: SECRET_KEY
      value: your-production-secret-key
    - name: OPENAI_API_KEY
      value: your-openai-key
    - name: PINECONE_API_KEY
      value: your-pinecone-key
```

#### 3. Deploy to App Runner

```bash
# Using AWS CLI
aws apprunner create-service \
  --service-name financebot \
  --source-configuration '{
    "CodeRepository": {
      "RepositoryUrl": "https://github.com/yourusername/FinanceBot",
      "SourceCodeVersion": {
        "Type": "BRANCH",
        "Value": "main"
      }
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1024",
    "Memory": "2048"
  }'
```

#### 3. Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd FinanceBot

# Setup backend
cd backend
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup environment
cp .env.local .env.production
# Edit .env.production with production values

# Start with systemd
sudo nano /etc/systemd/system/financebot.service
```

#### 4. Create Systemd Service

```ini
[Unit]
Description=FinanceBot FastAPI Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/FinanceBot/backend
Environment=PATH=/home/ubuntu/FinanceBot/backend/venv/bin
ExecStart=/home/ubuntu/FinanceBot/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable financebot
sudo systemctl start financebot
sudo systemctl status financebot
```

#### 5. Setup Nginx Reverse Proxy

```bash
# Install Nginx
sudo apt install nginx -y

# Configure Nginx
sudo nano /etc/nginx/sites-available/financebot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/financebot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔐 AWS IAM Permissions

### DynamoDB Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/users",
        "arn:aws:dynamodb:us-east-1:*:table/chats",
        "arn:aws:dynamodb:us-east-1:*:table/messages",
        "arn:aws:dynamodb:us-east-1:*:table/sessions"
      ]
    }
  ]
}
```

### Secrets Manager Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:aws:secretsmanager:us-east-1:*:secret:financebot/*"]
    }
  ]
}
```

## 📊 Monitoring & Logging

### CloudWatch Logs

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/financebot

# View logs
aws logs tail /ecs/financebot --follow
```

### CloudWatch Metrics

- DynamoDB: Read/Write capacity, throttling
- ECS: CPU/Memory utilization
- Application: Custom metrics for API calls

### Health Checks

```bash
# Health check endpoint
curl https://your-domain.com/health

# Expected response
{"status": "healthy", "timestamp": "2025-01-19T10:00:00Z"}
```

## 🔧 Environment Variables Reference

### Required Variables

| Variable              | Description         | Example                 |
| --------------------- | ------------------- | ----------------------- |
| `SECRET_KEY`          | JWT secret key      | `your-super-secret-key` |
| `OPENAI_API_KEY`      | OpenAI API key      | `sk-...`                |
| `PINECONE_API_KEY`    | Pinecone API key    | `...`                   |
| `PINECONE_INDEX_NAME` | Pinecone index name | `financebot-embeddings` |

### Optional Variables

| Variable                       | Default | Description             |
| ------------------------------ | ------- | ----------------------- |
| `DYNAMODB_TABLE_PREFIX`        | `""`    | Table name prefix       |
| `ACCESS_TOKEN_EXPIRE_MINUTES`  | `2`     | Access token expiry     |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `5`     | Refresh token expiry    |
| `DEFAULT_PAGE_SIZE`            | `3`     | Default pagination size |

## 🚨 Troubleshooting

### Common Issues

1. **DynamoDB Connection Failed**

   ```bash
   # Check AWS credentials
   aws sts get-caller-identity

   # Check DynamoDB endpoint
   aws dynamodb list-tables --endpoint-url http://localhost:8001
   ```

2. **Pinecone Connection Failed**

   ```bash
   # Test Pinecone connection
   python -c "import pinecone; print('Pinecone OK')"
   ```

3. **CORS Issues**

   ```bash
   # Check ALLOWED_ORIGINS in .env
   echo $ALLOWED_ORIGINS
   ```

4. **Token Refresh Issues**
   ```bash
   # Check token expiry settings
   grep -E "(ACCESS|REFRESH)_TOKEN_EXPIRE" .env
   ```

### Debug Commands

```bash
# Check DynamoDB tables
aws dynamodb list-tables --endpoint-url http://localhost:8001

# Check table structure
aws dynamodb describe-table --table-name users --endpoint-url http://localhost:8001

# Test API endpoints
curl -X GET http://localhost:8000/health
curl -X POST http://localhost:8000/auth/signin -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password"}'
```

## 📈 Performance Optimization

### DynamoDB Optimization

- Use appropriate read/write capacity
- Implement pagination for large datasets
- Use GSI for complex queries
- Enable TTL for automatic cleanup

### Application Optimization

- Use connection pooling for external APIs
- Implement caching for frequently accessed data
- Use async/await for I/O operations
- Monitor memory usage and optimize

## 🔒 Security Best Practices

1. **Environment Variables**: Use AWS Secrets Manager
2. **HTTPS**: Always use SSL/TLS in production
3. **CORS**: Restrict allowed origins
4. **Rate Limiting**: Implement API rate limiting
5. **Input Validation**: Validate all user inputs
6. **Logging**: Log security events
7. **Updates**: Keep dependencies updated

## 📝 Development Notes

- Tables are created automatically on first run
- Local development uses in-memory DynamoDB
- Production uses AWS DynamoDB with persistent storage
- All operations are asynchronous for better performance
- JWT tokens are stateless but refresh tokens are stored in sessions table
