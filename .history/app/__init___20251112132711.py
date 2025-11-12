from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import os

db = SQLAlchemy()
cache = Cache()

def create_app():
    app = Flask(__name__)

    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "..", "gallery.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

    # Cache configuration (Redis if available, otherwise simple)
    app.config['CACHE_TYPE'] = 'redis' if os.getenv('REDIS_URL') else 'simple'
    app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    app.config['CACHE_DEFAULT_TIMEOUT'] = 3600  # 1 hour

    # Initialize extensions
    db.init_app(app)
    cache.init_app(app)

    # Import models first
    from .models import Favorite, FileMetadata, ImageMetadata

    # Create tables
    with app.app_context():
        db.create_all()

    # Register blueprints
    from .routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    return app
