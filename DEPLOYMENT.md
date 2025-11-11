# 🚀 Deployment Guide

## Local Development (Current Setup)

You're already running it! The app is available at **http://localhost:5000**

### Commands:
```bash
# Development server (with hot reload)
source venv/bin/activate
python run.py

# Or using the helper script
./dev.sh run
```

---

## Production Deployment

### Option 1: Using Gunicorn (Recommended)

#### 1. Install Gunicorn
```bash
source venv/bin/activate
pip install gunicorn
```

#### 2. Create a startup script (`start.sh`)
```bash
#!/bin/bash
source venv/bin/activate
export FLASK_ENV=production
export DATASET_PATH=/path/to/dataset
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 "app:create_app()"
```

#### 3. Make it executable
```bash
chmod +x start.sh
./start.sh
```

### Option 2: Using uWSGI

#### 1. Install uWSGI
```bash
pip install uwsgi
```

#### 2. Create config file (`uwsgi.ini`)
```ini
[uwsgi]
module = wsgi:app
master = true
processes = 4
socket = 127.0.0.1:5000
chmod-socket = 666
vacuum = true
die-on-term = true
```

#### 3. Run
```bash
uwsgi --ini uwsgi.ini
```

### Option 3: Using systemd (for Linux servers)

#### 1. Create service file (`/etc/systemd/system/gallery.service`)
```ini
[Unit]
Description=Web Image Gallery
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/WebImageGalary
Environment="PATH=/path/to/WebImageGalary/venv/bin"
Environment="FLASK_ENV=production"
Environment="DATASET_PATH=/path/to/dataset"
ExecStart=/path/to/WebImageGalary/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app()"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and start
```bash
sudo systemctl daemon-reload
sudo systemctl enable gallery
sudo systemctl start gallery
sudo systemctl status gallery
```

---

## Docker Deployment

### 1. Create `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopenjp2-7 \
    libtiff6 \
    libwebp7 \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Create database
RUN mkdir -p /app/data

# Expose port
EXPOSE 5000

# Run
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "app:create_app()"]
```

### 2. Create `docker-compose.yml`
```yaml
version: '3.8'

services:
  gallery:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATASET_PATH=/data/images
    volumes:
      - ./dataset:/data/images
      - ./gallery.db:/app/gallery.db
    restart: unless-stopped
```

### 3. Run
```bash
docker-compose up -d
```

---

## Nginx Reverse Proxy Setup

### 1. Install Nginx
```bash
sudo apt-get install nginx
```

### 2. Create config (`/etc/nginx/sites-available/gallery`)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /static {
        alias /path/to/WebImageGalary/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. Enable and restart
```bash
sudo ln -s /etc/nginx/sites-available/gallery /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL/HTTPS with Let's Encrypt

### 1. Install Certbot
```bash
sudo apt-get install certbot python3-certbot-nginx
```

### 2. Get certificate
```bash
sudo certbot --nginx -d your-domain.com
```

### 3. Auto-renewal
```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Performance Optimization

### 1. Enable Caching
Edit `.env`:
```env
SEND_FILE_MAX_AGE_DEFAULT=86400  # 24 hours
```

### 2. Compress responses
In Flask app, add:
```python
from flask_compress import Compress
Compress(app)
```

### 3. Database optimization
```bash
# Rebuild database indexes
sqlite3 gallery.db "VACUUM;"
```

### 4. Image optimization
Before deploying, optimize images:
```bash
# Install ImageMagick
brew install imagemagick

# Batch resize
mogrify -resize 2000x2000> -quality 85 dataset/**/*.jpg
```

---

## Monitoring & Logging

### 1. Check application logs
```bash
# If using systemd
sudo journalctl -u gallery -f

# If using Gunicorn with file logging
tail -f app.log
```

### 2. Monitor system resources
```bash
# CPU and memory usage
top | grep gunicorn

# Disk usage
du -sh /path/to/WebImageGalary
```

### 3. Database maintenance
```bash
# Backup database
cp gallery.db gallery.db.backup

# Analyze database
sqlite3 gallery.db ".tables"
```

---

## Troubleshooting

### Port already in use
```bash
# Find process using port 5000
lsof -i :5000

# Kill it
kill -9 <PID>

# Or use different port
PORT=5001 gunicorn "app:create_app()"
```

### Permission denied
```bash
# Set correct permissions
chmod 755 /path/to/WebImageGalary
chmod 755 /path/to/dataset
chmod 644 gallery.db
```

### Out of memory
```bash
# Reduce worker processes
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"

# Enable memory optimization
export PYTHONOPTIMIZE=2
```

### Slow response times
```bash
# Check database size
sqlite3 gallery.db ".dbinfo"

# Run VACUUM to optimize
sqlite3 gallery.db "VACUUM;"
```

---

## Backup & Recovery

### 1. Backup everything
```bash
# Full backup
tar -czf gallery-backup.tar.gz \
    gallery.db \
    dataset/ \
    app/

# Upload to cloud storage
aws s3 cp gallery-backup.tar.gz s3://bucket-name/
```

### 2. Restore from backup
```bash
# Extract backup
tar -xzf gallery-backup.tar.gz

# Restart service
systemctl restart gallery
```

---

## Security Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Use strong database password
- [ ] Enable HTTPS with SSL certificate
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Backup data regularly
- [ ] Monitor access logs
- [ ] Use strong admin credentials
- [ ] Keep Python dependencies updated
- [ ] Disable debug mode in production

---

## Scaling for Large Deployments

### Database Scaling
- Migrate to PostgreSQL for better concurrency
- Implement connection pooling
- Add caching layer (Redis)

### Application Scaling
- Use load balancer (HAProxy, AWS ELB)
- Deploy multiple instances
- Use CDN for static files
- Implement image caching

### Storage Scaling
- Use object storage (S3, Google Cloud Storage)
- Implement image thumbnails
- Archive old images separately

---

## Example: Full Production Setup

```bash
# 1. Create deployment directory
mkdir /var/www/gallery
cd /var/www/gallery

# 2. Clone/copy application
# (copy your WebImageGalary folder here)

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
pip install gunicorn

# 5. Create systemd service
sudo cp gallery.service /etc/systemd/system/

# 6. Create nginx config
sudo cp nginx-config /etc/nginx/sites-available/gallery
sudo ln -s /etc/nginx/sites-available/gallery /etc/nginx/sites-enabled/

# 7. Set up SSL
sudo certbot --nginx -d your-domain.com

# 8. Start services
sudo systemctl enable gallery
sudo systemctl start gallery
sudo systemctl restart nginx

# 9. Verify
curl https://your-domain.com
```

---

## Support

For deployment issues:
1. Check logs: `journalctl -u gallery -f`
2. Verify configuration: `cat .env`
3. Test connectivity: `curl localhost:5000`
4. Check file permissions: `ls -la`

Happy deploying! 🚀
