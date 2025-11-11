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

class ImageMetadata(db.Model):
    """Store image metadata for fast loading"""
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
