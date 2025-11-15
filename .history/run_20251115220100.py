#!/usr/bin/env python
"""
Web Image Gallery - Main Entry Point
"""
import os
import sys
from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Configuration
    debug = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '127.0.0.1')
    
    print(f"🖼️  Starting Web Image Gallery...")
    print(f"📁 Dataset path: {os.getenv('DATASET_PATH', os.path.join(os.path.dirname(__file__), 'dataset'))}")
    print(f"🌐 Server: http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug, use_reloader=True)
