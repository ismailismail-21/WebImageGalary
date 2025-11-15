#!/bin/bash

# Production optimization script for large folders (10,000+ files)
# Run this after setup.sh to optimize for production use

echo "🚀 Production Optimization for Large Folders"
echo "==========================================="
echo ""

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
else
    echo "❌ Please activate the virtual environment first:"
    echo "   source venv/bin/activate"
    exit 1
fi

echo ""

# Install Redis if not present (optional but recommended)
if ! command -v redis-server &> /dev/null; then
    echo "📦 Installing Redis (recommended for caching)..."
    if command -v apt &> /dev/null; then
        # Ubuntu/Debian
        sudo apt update
        sudo apt install -y redis-server
        sudo systemctl enable redis-server
        sudo systemctl start redis-server
        echo "✅ Redis installed and started"
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y redis
        sudo systemctl enable redis
        sudo systemctl start redis
        echo "✅ Redis installed and started"
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf install -y redis
        sudo systemctl enable redis
        sudo systemctl start redis
        echo "✅ Redis installed and started"
    else
        echo "⚠️  Please install Redis manually for optimal performance"
        echo "   Ubuntu/Debian: sudo apt install redis-server"
        echo "   CentOS/RHEL: sudo yum install redis"
        echo "   Fedora: sudo dnf install redis"
    fi
else
    echo "✅ Redis found"
fi

echo ""

# Run database migration
echo "🗄️  Running database migration..."
python migrate_db.py

echo ""

# Create production startup script
echo "📜 Creating production startup script..."
cat > start_production.sh << 'EOF'
#!/bin/bash

# Production startup script for Web Image Gallery
# Optimized for large folders with 10,000+ files

echo "🚀 Starting Web Image Gallery (Production Mode)"
echo "=============================================="

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Please activate the virtual environment:"
    echo "   source venv/bin/activate"
    exit 1
fi

# Set production environment
export FLASK_ENV=production
export HOST=0.0.0.0
export PORT=8000

# Set Redis URL if Redis is running
if command -v redis-cli &> /dev/null && redis-cli ping &> /dev/null; then
    export REDIS_URL=redis://localhost:6379/0
    echo "✅ Redis detected and configured"
else
    echo "⚠️  Redis not detected - using simple caching"
fi

# Start with Gunicorn
echo "🌐 Starting server on http://0.0.0.0:8000"
echo "   Workers: 4"
echo "   Press Ctrl+C to stop"
echo ""

gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    wsgi:app

EOF

chmod +x start_production.sh
echo "✅ Created start_production.sh"

echo ""

# Create background scanner script
echo "🔄 Creating background scanner script..."
cat > scan_folders.sh << 'EOF'
#!/bin/bash

# Background folder scanner for Web Image Gallery
# Run this to precompute metadata and thumbnails for large folders

echo "🔍 Scanning folders for metadata and thumbnails..."
echo "================================================="

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Please activate the virtual environment:"
    echo "   source venv/bin/activate"
    exit 1
fi

# Set dataset path
DATASET_PATH=${DATASET_PATH:-dataset}

echo "📁 Scanning dataset: $DATASET_PATH"
echo ""

python3 -c "
import os
import sys
sys.path.insert(0, '.')
from app import create_app
from app.utils import scan_folder_background

app = create_app()

with app.app_context():
    # Scan all folders
    for root, dirs, files in os.walk('$DATASET_PATH'):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Check if this directory has supported files
        has_supported_files = any(
            f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webm'))
            for f in files
        )
        
        if has_supported_files:
            rel_path = os.path.relpath(root, '$DATASET_PATH')
            if rel_path == '.':
                rel_path = ''
            print(f'📂 Scanning: {rel_path or \"root\"}')
            scan_folder_background('$DATASET_PATH', rel_path)

print('✅ Background scanning initiated')
print('   Check server logs for progress')
"

EOF

chmod +x scan_folders.sh
echo "✅ Created scan_folders.sh"

echo ""
echo "🎉 Production optimization complete!"
echo ""
echo "To start in production mode:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: ./start_production.sh"
echo ""
echo "To scan folders for metadata/thumbnails:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: ./scan_folders.sh"
echo ""
echo "Performance tips:"
echo "  - Redis should be running automatically (systemctl status redis-server)"
echo "  - Monitor memory usage with large folders"
echo "  - Use SSD storage for faster thumbnail generation"
echo "  - Consider using a CDN for static files in production"