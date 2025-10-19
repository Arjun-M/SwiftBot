# SwiftBot Installation Guide

**Copyright (c) 2025 Arjun-M/SwiftBot**

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Installation](#quick-installation)
3. [Database Setup](#database-setup)
4. [Webhook Setup](#webhook-setup)
5. [Production Deployment](#production-deployment)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **Python**: 3.10 or higher
- **RAM**: 512 MB minimum (1 GB+ recommended)
- **CPU**: 1 core (2+ cores recommended)
- **Storage**: 100 MB for package + storage for data

### Recommended for Production
- **Python**: 3.11 or 3.12
- **RAM**: 2 GB+
- **CPU**: 2+ cores
- **Redis**: 6.0+ or PostgreSQL 12+
- **SSL Certificate**: For webhook mode

---

## Quick Installation

### Step 1: Extract Package

```bash
unzip SwiftBot-v1.0.0.zip
cd SwiftBot
```

### Step 2: Install Core Package

```bash
# Install required dependencies
pip install httpx httpx[http2]

# Or install in editable mode
pip install -e .
```

### Step 3: Test Installation

```python
# test_install.py
from swiftbot import SwiftBot
print("SwiftBot installed successfully!")
```

```bash
python test_install.py
```

---

## Database Setup

### Option 1: Redis (Recommended for Production)

#### Install Redis

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download from: https://github.com/tporadowski/redis/releases

#### Install Python Client

```bash
pip install redis
```

#### Setup in Bot

```python
import redis
from swiftbot.storage import RedisStore

redis_conn = redis.Redis(host='localhost', port=6379, db=0)
storage = RedisStore(connection=redis_conn)
```

#### Interactive Setup

```bash
python setup_database.py
# Choose option 1 (Redis)
```

---

### Option 2: PostgreSQL

#### Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

#### Create Database

```bash
sudo -u postgres psql
CREATE DATABASE swiftbot;
CREATE USER swiftbot_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE swiftbot TO swiftbot_user;
\q
```

#### Install Python Client

```bash
pip install asyncpg
```

#### Setup in Bot

```python
import asyncpg
from swiftbot.storage import PostgresStore

pool = await asyncpg.create_pool(
    "postgresql://swiftbot_user:your_password@localhost/swiftbot"
)
storage = PostgresStore(connection=pool)
```

#### Interactive Setup

```bash
python setup_database.py
# Choose option 2 (PostgreSQL)
```

---

### Option 3: MongoDB

#### Install MongoDB

**Ubuntu/Debian:**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

#### Install Python Client

```bash
pip install motor
```

#### Setup in Bot

```python
import motor.motor_asyncio
from swiftbot.storage import MongoStore

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
storage = MongoStore(connection=client, database="swiftbot")
```

#### Interactive Setup

```bash
python setup_database.py
# Choose option 3 (MongoDB)
```

---

### Option 4: File Storage (Development Only)

No installation required! Just use:

```python
from swiftbot.storage import FileStore

storage = FileStore(base_path="./data")
```

**Note**: File storage is not recommended for production or multiple bot instances.

---

## Webhook Setup

### Prerequisites
1. **Public domain** with HTTPS
2. **SSL certificate** (Let's Encrypt recommended)
3. **Open port**: 443, 8443, 88, or 80

### Step 1: Install AIOHTTP

```bash
pip install aiohttp
```

### Step 2: Get SSL Certificate

#### Using Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install certbot  # Ubuntu/Debian
brew install certbot      # macOS

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com
```

Certificates will be at:
- Certificate: `/etc/letsencrypt/live/yourdomain.com/fullchain.pem`
- Private Key: `/etc/letsencrypt/live/yourdomain.com/privkey.pem`

### Step 3: Configure Bot for Webhook

```python
import asyncio
from swiftbot import SwiftBot

client = SwiftBot(token="YOUR_BOT_TOKEN")

# Add your handlers here
@client.on(Message(F.command("start")))
async def start(ctx):
    await ctx.reply("Hello from webhook!")

async def main():
    await client.run_webhook(
        host="0.0.0.0",
        port=8443,
        webhook_url="https://yourdomain.com:8443/webhook",
        cert_path="/etc/letsencrypt/live/yourdomain.com/fullchain.pem",
        key_path="/etc/letsencrypt/live/yourdomain.com/privkey.pem",
        secret_token="your_random_secret_token",
        drop_pending_updates=True
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Configure Firewall

```bash
# Ubuntu/Debian
sudo ufw allow 8443/tcp
sudo ufw reload

# Or use port 443
sudo ufw allow 443/tcp
```

### Step 5: Run Bot

```bash
python bot_webhook.py
```

---

## Production Deployment

### Using systemd (Linux)

#### Create Service File

```bash
sudo nano /etc/systemd/system/swiftbot.service
```

```ini
[Unit]
Description=SwiftBot Telegram Bot
After=network.target redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/SwiftBot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable swiftbot
sudo systemctl start swiftbot
sudo systemctl status swiftbot
```

#### View Logs

```bash
sudo journalctl -u swiftbot -f
```

---

### Using Docker

#### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

#### Create docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: always
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - REDIS_HOST=redis
    depends_on:
      - redis
    networks:
      - swiftbot-network

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis-data:/data
    networks:
      - swiftbot-network

volumes:
  redis-data:

networks:
  swiftbot-network:
```

#### Run with Docker

```bash
docker-compose up -d
docker-compose logs -f bot
```

---

### Using Supervisor

#### Install Supervisor

```bash
sudo apt install supervisor
```

#### Create Config

```bash
sudo nano /etc/supervisor/conf.d/swiftbot.conf
```

```ini
[program:swiftbot]
command=/path/to/venv/bin/python /path/to/bot.py
directory=/path/to/SwiftBot
user=your_user
autostart=true
autorestart=true
stderr_logfile=/var/log/swiftbot/err.log
stdout_logfile=/var/log/swiftbot/out.log
```

#### Start

```bash
sudo mkdir /var/log/swiftbot
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start swiftbot
```

---

## Environment Variables

Create `.env` file:

```bash
# Bot Configuration
BOT_TOKEN=your_bot_token_here
PARSE_MODE=HTML

# Database
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Webhook (if using)
WEBHOOK_URL=https://yourdomain.com/webhook
WEBHOOK_SECRET=your_secret_token
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# Admin
ADMIN_IDS=123456789,987654321
```

Use in bot:

```python
import os
from dotenv import load_dotenv

load_dotenv()

client = SwiftBot(token=os.getenv("BOT_TOKEN"))
```

Install python-dotenv:
```bash
pip install python-dotenv
```

---

## Troubleshooting

### Issue: Import Error

**Error**: `ModuleNotFoundError: No module named 'swiftbot'`

**Solution**:
```bash
# Install in editable mode
cd SwiftBot
pip install -e .

# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/SwiftBot"
```

### Issue: Redis Connection Failed

**Error**: `redis.exceptions.ConnectionError`

**Solutions**:
1. Check Redis is running: `sudo systemctl status redis`
2. Check Redis port: `redis-cli ping`
3. Check firewall: `sudo ufw status`

### Issue: SSL Certificate Error

**Error**: `ssl.SSLError`

**Solutions**:
1. Check certificate paths are correct
2. Ensure certificate is not expired
3. Use absolute paths, not relative
4. Check file permissions: `chmod 644 cert.pem`

### Issue: Webhook Not Receiving Updates

**Solutions**:
1. Check webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
2. Verify domain is accessible publicly
3. Check firewall allows port
4. Verify SSL certificate is valid
5. Check secret token matches

### Issue: High Memory Usage

**Solutions**:
1. Reduce worker pool: `worker_pool_size=25`
2. Use Redis instead of file storage
3. Clear old data from storage
4. Restart bot periodically

### Issue: Slow Response Time

**Solutions**:
1. Enable HTTP/2: `enable_http2=True`
2. Increase workers: `worker_pool_size=50`
3. Use connection pooling
4. Optimize database queries
5. Use Redis for caching

---

## Performance Tuning

### For High Traffic Bots

```python
client = SwiftBot(
    token="TOKEN",
    worker_pool_size=100,        # More workers
    max_connections=200,         # More connections
    enable_http2=True,           # HTTP/2
    connection_pool={
        'max_connections': 200,
        'max_keepalive_connections': 100,
        'keepalive_expiry': 60.0,
    },
)
```

### For Low Resource Servers

```python
client = SwiftBot(
    token="TOKEN",
    worker_pool_size=10,         # Fewer workers
    max_connections=25,          # Fewer connections
    enable_http2=False,          # HTTP/1.1 uses less memory
)
```

---

## Monitoring

### Health Check Endpoint

In webhook mode, access:
```
http://your-server:8443/health
```

### Metrics

```python
stats = client.get_stats()
print(f"Workers: {stats['worker_pool']['num_workers']}")
print(f"Processed: {stats['worker_pool']['processed']}")
print(f"Failed: {stats['worker_pool']['failed']}")
```

### Logging

```python
from swiftbot.middleware import Logger

client.use(Logger(
    level="INFO",
    format="json",
    include_updates=True
))
```

---

## Next Steps

1. ✅ Complete installation
2. ✅ Setup database
3. ✅ Create your bot
4. ✅ Test locally
5. ✅ Deploy to production
6. ✅ Monitor and scale

**Need Help?** Check the USAGE.md and DOCUMENTATION.md files.

---

**Copyright (c) 2025 Arjun-M/SwiftBot**  
**License: MIT**
