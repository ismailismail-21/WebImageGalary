from . import db
from datetime import datetime

class Favorite(db.Model):
    """Store favorite images"""
    id = db.Column(db.Integer, primary_key=True)
    folder_path = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('folder_path', 'filename', name='unique_favorite'),)

    def to_dict(self):
        return {
            'id': self.id,
            'folder_path': self.folder_path,
            'filename': self.filename,
            'created_at': self.created_at.isoformat()
        }

class FileMetadata(db.Model):
    """Store comprehensive file metadata for fast loading (supports images, videos, GIFs)"""
    id = db.Column(db.Integer, primary_key=True)
    folder_path = db.Column(db.String(500), nullable=False, index=True)
    filename = db.Column(db.String(500), nullable=False, index=True)
    file_type = db.Column(db.String(10), nullable=False, index=True)  # 'image', 'video', 'gif'
    file_size = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Float, nullable=True)  # for videos/GIFs in seconds
    fps = db.Column(db.Float, nullable=True)  # for videos
    thumbnail_path = db.Column(db.String(500), nullable=True)  # relative path to thumbnail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.Index('idx_folder_filename', 'folder_path', 'filename'),
        db.Index('idx_folder_modified', 'folder_path', 'modified_at'),
        db.Index('idx_file_type', 'file_type'),
        db.Index('idx_modified_at', 'modified_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'folder_path': self.folder_path,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'fps': self.fps,
            'thumbnail_path': self.thumbnail_path,
            'aspect_ratio': self.width / self.height if self.width and self.height and self.height > 0 else 1,
            'is_video': self.file_type == 'video',
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }

# Keep ImageMetadata for backward compatibility but mark as deprecated
class ImageMetadata(db.Model):
    """Legacy model - use FileMetadata instead"""
    id = db.Column(db.Integer, primary_key=True)
    folder_path = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('folder_path', 'filename', name='unique_image'),)

    def to_dict(self):
        return {
            'filename': self.filename,
            'width': self.width,
            'height': self.height,
            'aspect_ratio': self.width / self.height if self.height > 0 else 1
        }

class Tag(db.Model):
    """Store image tags"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#667eea')  # Hex color
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at.isoformat()
        }

class ImageTag(db.Model):
    """Many-to-many relationship between images and tags"""
    id = db.Column(db.Integer, primary_key=True)
    folder_path = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    tag = db.relationship('Tag', backref=db.backref('images', lazy='dynamic'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('folder_path', 'filename', 'tag_id', name='unique_image_tag'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'folder_path': self.folder_path,
            'filename': self.filename,
            'tag_id': self.tag_id,
            'tag': self.tag.to_dict() if self.tag else None,
            'created_at': self.created_at.isoformat()
        }
