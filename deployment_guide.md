# Deployment Guide

This guide covers deploying the Medical Chatbot API to production environments.

## Production Deployment Options

### 1. Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 chatbot && chown -R chatbot:chatbot /app
USER chatbot

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "app_secure.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  chatbot-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - chatbot-api
    restart: unless-stopped
```

### 2. Production WSGI Server

Install Gunicorn:

```bash
pip install gunicorn
```

Create `gunicorn_config.py`:

```python
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "chatbot-api"

# Server mechanics
daemon = False
pidfile = "/app/chatbot-api.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if using HTTPS directly)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
```

Run with Gunicorn:

```bash
gunicorn --config gunicorn_config.py app_secure:app
```

### 3. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream chatbot_api {
        server chatbot-api:5000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=chat:10m rate=5r/s;

    server {
        listen 80;
        server_name your-domain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";

        # Handle preflight requests
        location / {
            if ($request_method = 'OPTIONS') {
                add_header Access-Control-Allow-Origin *;
                add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
                add_header Access-Control-Allow-Headers "Content-Type, Authorization";
                add_header Access-Control-Max-Age 1728000;
                add_header Content-Type 'text/plain; charset=utf-8';
                add_header Content-Length 0;
                return 204;
            }

            # Rate limiting
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://chatbot_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Special rate limiting for chat endpoints
        location ~* ^/chat/ {
            limit_req zone=chat burst=10 nodelay;
            
            proxy_pass http://chatbot_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check endpoint (no rate limiting)
        location /health {
            proxy_pass http://chatbot_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Environment Configuration

Create `.env` file for production:

```env
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000

# Model Configuration
MODEL_PATH=/app/models/symptom_disease_model
DATASET_CACHE_DIR=/app/cache

# Session Configuration
SESSION_TIMEOUT_MINUTES=30
SESSION_CLEANUP_INTERVAL=300

# Security Configuration
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
RATE_LIMIT_PER_DAY=2000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/chatbot.log
ACCESS_LOG_FILE=/app/logs/access.log

# Database Configuration (if using database for sessions)
DATABASE_URL=postgresql://user:password@localhost/chatbot_db

# Monitoring Configuration
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_METRICS_PORT=9090
```

## Production-Ready Application

Create `app_production.py`:

```python
"""
Production-ready Flask application with enhanced features.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from prometheus_flask_exporter import PrometheusMetrics

from app_secure import *  # Import all from secure app

# Initialize Sentry for error tracking
if os.getenv('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1
    )

# Configure production logging
def setup_logging(app):
    if not app.debug:
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # File handler for application logs
        file_handler = RotatingFileHandler(
            'logs/chatbot.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Set log level
        app.logger.setLevel(logging.INFO)
        app.logger.info('Chatbot API startup')

# Add Prometheus metrics
def setup_metrics(app):
    metrics = PrometheusMetrics(app)
    
    # Custom metrics
    metrics.info('chatbot_api_info', 'Chatbot API Information', version='1.0')
    
    # Track session metrics
    session_counter = metrics.counter(
        'chatbot_sessions_total', 
        'Total number of chat sessions created'
    )
    
    message_counter = metrics.counter(
        'chatbot_messages_total',
        'Total number of messages processed'
    )
    
    prediction_histogram = metrics.histogram(
        'chatbot_prediction_duration_seconds',
        'Time spent on disease prediction'
    )
    
    return metrics

# Enhanced health check
@app.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check for monitoring systems."""
    try:
        # Check all components
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "chatbot": {
                    "status": "healthy" if chatbot else "unhealthy",
                    "ready": chatbot is not None
                },
                "model": model_loader.get_model_info(),
                "sessions": {
                    "active_count": session_manager.get_session_count(),
                    "status": "healthy"
                },
                "security": {
                    "status": "healthy",
                    "stats": security_manager.get_security_stats()
                }
            }
        }
        
        # Determine overall status
        component_statuses = [
            comp.get("status", "unknown") 
            for comp in health_status["components"].values()
        ]
        
        if any(status == "unhealthy" for status in component_statuses):
            health_status["status"] = "degraded"
            return jsonify(health_status), 503
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503

# Graceful shutdown handler
def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Setup logging
    setup_logging(app)
    
    # Setup metrics
    setup_metrics(app)
    
    # Initialize chatbot
    if not initialize_chatbot():
        app.logger.error("Failed to initialize chatbot")
        raise RuntimeError("Chatbot initialization failed")
    
    return app

if __name__ == '__main__':
    # Create application
    app = create_app()
    
    # Get configuration from environment
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        session_manager.stop_cleanup_thread()
        logger.info("Application shutdown complete")
```

## Monitoring and Logging

### 1. Prometheus Metrics

Add to `requirements.txt`:
```
prometheus-flask-exporter==0.20.3
```

### 2. Log Aggregation

Example Fluentd configuration (`fluent.conf`):

```
<source>
  @type tail
  path /app/logs/chatbot.log
  pos_file /var/log/fluentd/chatbot.log.pos
  tag chatbot.application
  format json
</source>

<match chatbot.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name chatbot-logs
  type_name _doc
</match>
```

### 3. Health Check Monitoring

Create monitoring script (`monitor.py`):

```python
#!/usr/bin/env python3
import requests
import time
import sys
import logging

def check_health(url, timeout=10):
    try:
        response = requests.get(f"{url}/health/detailed", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                return True, "Service is healthy"
            else:
                return False, f"Service degraded: {data}"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    while True:
        healthy, message = check_health(api_url)
        
        if healthy:
            print(f"✓ {time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")
        else:
            print(f"✗ {time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")
            
        time.sleep(30)

if __name__ == "__main__":
    main()
```

## Security Considerations

### 1. API Key Authentication (Optional)

Add API key authentication:

```python
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('API_KEY'):
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Apply to sensitive endpoints
@app.route('/admin/stats', methods=['GET'])
@require_api_key
def get_admin_stats():
    # ... existing code
```

### 2. IP Whitelisting

```python
ALLOWED_IPS = os.getenv('ALLOWED_IPS', '').split(',')

def check_ip_whitelist():
    if ALLOWED_IPS and request.remote_addr not in ALLOWED_IPS:
        return False
    return True
```

### 3. SSL/TLS Configuration

Ensure proper SSL configuration in production:

```bash
# Generate SSL certificate (Let's Encrypt example)
certbot certonly --webroot -w /var/www/html -d your-domain.com
```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database migrations run (if applicable)
- [ ] Log directories created with proper permissions
- [ ] Firewall rules configured
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security scan performed
- [ ] Documentation updated

## Scaling Considerations

### Horizontal Scaling

- Use load balancer (Nginx, HAProxy, or cloud load balancer)
- Implement session affinity or external session storage
- Use Redis for shared session management
- Consider microservices architecture for large deployments

### Vertical Scaling

- Monitor CPU and memory usage
- Adjust Gunicorn worker count based on load
- Optimize model loading and caching
- Use GPU acceleration for model inference if available

This deployment guide provides a comprehensive approach to deploying the medical chatbot API in production environments with proper security, monitoring, and scalability considerations.

