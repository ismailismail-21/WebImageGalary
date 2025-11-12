#!/usr/bin/env python3
"""
WSGI entry point for production deployment with Gunicorn
"""

from app import create_app

# Create the Flask application
app = create_app()

if __name__ == "__main__":
    app.run()