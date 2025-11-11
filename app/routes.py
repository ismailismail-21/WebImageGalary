from flask import Blueprint, render_template, request, jsonify, send_file, current_app
import os
from pathlib import Path
from .utils import get_all_folders, get_folder_images, delete_image, is_supported_image
from .models import Favorite, ImageMetadata, Tag, ImageTag
from . import db

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Get dataset path from environment or use default
DATASET_PATH = os.getenv('DATASET_PATH', os.path.join(os.path.dirname(__file__), '..', 'dataset'))

@main_bp.route('/')
def index():
    """Main gallery page with favorite images"""
    folders = get_all_folders(DATASET_PATH)
    try:
        # Get all favorite images with their metadata
        favorites = Favorite.query.all()
        favorite_images = []
        for fav in favorites:
            # Get image dimensions
            try:
                from PIL import Image as PILImage
                img_path = os.path.join(DATASET_PATH, fav.folder_path, fav.filename)
                if os.path.exists(img_path):
                    pil_img = PILImage.open(img_path)
                    width, height = pil_img.size
                else:
                    width, height = 300, 300
            except:
                width, height = 300, 300
                
            favorite_images.append({
                'folder': fav.folder_path,
                'filename': fav.filename,
                'full_path': f"{fav.folder_path}/{fav.filename}",
                'width': width,
                'height': height
            })
    except:
        favorite_images = []
    
    return render_template('index.html', folders=folders, favorite_images=favorite_images)

@main_bp.route('/folder/<folder_name>')
def folder(folder_name):
    """Display images from a specific folder"""
    folders = get_all_folders(DATASET_PATH)
    folder_exists = any(f['path'] == folder_name for f in folders)
    
    if not folder_exists:
        return "Folder not found", 404
    
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    images, total = get_folder_images(DATASET_PATH, folder_name, page, per_page)
    
    # Get all tags as dictionaries for JSON serialization
    try:
        tag_objects = Tag.query.all()
        tags = [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in tag_objects]
    except:
        tags = []
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return render_template(
        'folder.html',
        folder_name=folder_name,
        images=images,
        current_page=page,
        total_pages=total_pages,
        total_images=total,
        folders=folders,
        tags=tags
    )

@main_bp.route('/tags')
def tags_page():
    """Display all tags and images by tag"""
    folders = get_all_folders(DATASET_PATH)
    try:
        tags = Tag.query.all()
    except:
        tags = []
    
    return render_template('tags.html', folders=folders, tags=tags)

@main_bp.route('/tag/<int:tag_id>')
def tag_detail(tag_id):
    """Display all images with a specific tag"""
    folders = get_all_folders(DATASET_PATH)
    
    try:
        tag = Tag.query.get(tag_id)
        if not tag:
            return "Tag not found", 404
        
        # Get all images with this tag
        image_tags = ImageTag.query.filter_by(tag_id=tag_id).all()
        images = []
        for img_tag in image_tags:
            # Calculate dimensions using justified layout
            try:
                from PIL import Image as PILImage
                img_path = os.path.join(DATASET_PATH, img_tag.folder_path, img_tag.filename)
                if os.path.exists(img_path):
                    pil_img = PILImage.open(img_path)
                    width, height = pil_img.size
                else:
                    width, height = 400, 300
            except:
                width, height = 400, 300
            
            images.append({
                'folder': img_tag.folder_path,
                'filename': img_tag.filename,
                'full_path': f"{img_tag.folder_path}/{img_tag.filename}",
                'width': width,
                'height': height,
                'calc_width': 300,  # Placeholder, will be calculated on frontend
                'calc_height': 300   # Placeholder, will be calculated on frontend
            })
        
        # Convert tag to dictionary
        tag_dict = {'id': tag.id, 'name': tag.name, 'color': tag.color}
    except:
        tag_dict = None
        images = []
    
    return render_template('tag_detail.html', tag=tag_dict, images=images, folders=folders)

# ==================== API ENDPOINTS ====================

@api_bp.route('/folders')
def get_folders():
    """API endpoint to get all folders"""
    folders = get_all_folders(DATASET_PATH)
    return jsonify(folders)

@api_bp.route('/folder/<folder_name>/images')
def get_folder_data(folder_name):
    """API endpoint to get folder images with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    
    images, total = get_folder_images(DATASET_PATH, folder_name, page, per_page)
    
    # Add favorite status for each image
    for img in images:
        try:
            fav = Favorite.query.filter_by(folder_path=folder_name, filename=img['filename']).first()
            img['is_favorite'] = fav is not None
        except:
            img['is_favorite'] = False
        
        # Add tags for each image
        try:
            img_tags = ImageTag.query.filter_by(folder_path=folder_name, filename=img['filename']).all()
            img['tags'] = [t.tag.to_dict() for t in img_tags]
        except:
            img['tags'] = []
    
    total_pages = (total + per_page - 1) // per_page
    
    return jsonify({
        'images': images,
        'current_page': page,
        'total_pages': total_pages,
        'total_images': total,
        'per_page': per_page
    })

@api_bp.route('/image/<path:folder_name>/<filename>')
def get_image(folder_name, filename):
    """Serve an image file"""
    try:
        image_path = os.path.join(DATASET_PATH, folder_name, filename)
        
        # Security check - prevent path traversal
        real_path = os.path.realpath(image_path)
        real_base = os.path.realpath(os.path.join(DATASET_PATH, folder_name))
        
        if not real_path.startswith(real_base):
            return "Access denied", 403
        
        if os.path.exists(image_path) and is_supported_image(filename):
            return send_file(image_path, mimetype='image/jpeg')
        else:
            return "Image not found", 404
    except Exception as e:
        return f"Error serving image: {str(e)}", 500

@api_bp.route('/image/<path:folder_name>/<filename>', methods=['DELETE'])
def delete_image_api(folder_name, filename):
    """Delete an image"""
    success, message = delete_image(DATASET_PATH, folder_name, filename)
    return jsonify({'success': success, 'message': message}), 200 if success else 400

# ==================== FAVORITES ENDPOINTS ====================

@api_bp.route('/favorite/<path:folder_name>/<filename>', methods=['POST'])
def add_favorite(folder_name, filename):
    """Add image to favorites"""
    try:
        existing = Favorite.query.filter_by(folder_path=folder_name, filename=filename).first()
        if existing:
            return jsonify({'success': False, 'message': 'Already in favorites'}), 400
        
        favorite = Favorite(folder_path=folder_name, filename=filename)
        db.session.add(favorite)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Added to favorites'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/favorite/<path:folder_name>/<filename>', methods=['DELETE'])
def remove_favorite(folder_name, filename):
    """Remove image from favorites"""
    try:
        favorite = Favorite.query.filter_by(folder_path=folder_name, filename=filename).first()
        if not favorite:
            return jsonify({'success': False, 'message': 'Not in favorites'}), 404
        
        db.session.delete(favorite)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Removed from favorites'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/favorites')
def get_favorites():
    """Get all favorite images"""
    try:
        favorites = Favorite.query.order_by(Favorite.created_at.desc()).all()
        return jsonify([f.to_dict() for f in favorites])
    except:
        return jsonify([])

# ==================== TAGS ENDPOINTS ====================

@api_bp.route('/tags', methods=['GET'])
def get_tags():
    """Get all tags with image counts"""
    try:
        tags = Tag.query.order_by(Tag.name).all()
        tag_list = []
        for tag in tags:
            tag_dict = tag.to_dict()
            # Add image count
            image_count = ImageTag.query.filter_by(tag_id=tag.id).count()
            tag_dict['image_count'] = image_count
            tag_list.append(tag_dict)
        return jsonify(tag_list)
    except:
        return jsonify([])

@api_bp.route('/tags', methods=['POST'])
def create_tag():
    """Create a new tag"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        color = data.get('color', '#667eea')
        
        if not name:
            return jsonify({'success': False, 'message': 'Tag name required'}), 400
        
        existing = Tag.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'message': 'Tag already exists'}), 400
        
        tag = Tag(name=name, color=color)
        db.session.add(tag)
        db.session.commit()
        
        return jsonify({'success': True, 'tag': tag.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete a tag"""
    try:
        tag = Tag.query.get(tag_id)
        if not tag:
            return jsonify({'success': False, 'message': 'Tag not found'}), 404
        
        # Delete all associated image tags
        ImageTag.query.filter_by(tag_id=tag_id).delete()
        db.session.delete(tag)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tag deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/image-tags/<path:folder_name>/<filename>')
def get_image_tags(folder_name, filename):
    """Get all tags for an image"""
    try:
        image_tags = ImageTag.query.filter_by(folder_path=folder_name, filename=filename).all()
        return jsonify([it.to_dict() for it in image_tags])
    except:
        return jsonify([])

@api_bp.route('/image-tag/<path:folder_name>/<filename>/<int:tag_id>', methods=['POST'])
def add_image_tag(folder_name, filename, tag_id):
    """Add a tag to an image"""
    try:
        existing = ImageTag.query.filter_by(folder_path=folder_name, filename=filename, tag_id=tag_id).first()
        if existing:
            # Tag already exists, return success (idempotent operation)
            return jsonify({'success': True, 'message': 'Tag already added'})
        
        tag = Tag.query.get(tag_id)
        if not tag:
            return jsonify({'success': False, 'message': 'Tag not found'}), 404
        
        image_tag = ImageTag(folder_path=folder_name, filename=filename, tag_id=tag_id)
        db.session.add(image_tag)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tag added to image'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/image-tag/<path:folder_name>/<filename>/<int:tag_id>', methods=['DELETE'])
def remove_image_tag(folder_name, filename, tag_id):
    """Remove a tag from an image"""
    try:
        image_tag = ImageTag.query.filter_by(folder_path=folder_name, filename=filename, tag_id=tag_id).first()
        if not image_tag:
            return jsonify({'success': False, 'message': 'Tag not assigned'}), 404
        
        db.session.delete(image_tag)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Tag removed from image'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
