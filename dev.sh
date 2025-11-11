#!/bin/bash

# Development commands helper

case "$1" in
  setup)
    echo "Setting up development environment..."
    chmod +x setup.sh
    ./setup.sh
    ;;
  run)
    echo "Starting development server..."
    source venv/bin/activate
    FLASK_ENV=development python run.py
    ;;
  clean)
    echo "Cleaning up..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete
    rm -f gallery.db
    echo "✅ Cleaned!"
    ;;
  *)
    echo "Usage: $0 {setup|run|clean}"
    echo ""
    echo "Commands:"
    echo "  setup  - Install dependencies and setup virtual environment"
    echo "  run    - Start development server"
    echo "  clean  - Remove cache and database"
    ;;
esac
