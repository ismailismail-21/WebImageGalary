import os
from PIL import Image
from pathlib import Path
from .models import FileMetadata, ImageMetadata
from . import db
import math
import threading
import cv2
from datetime import datetime

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.mp4', '.mov', '.avi', '.webm'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.mp4', '.mov', '.avi', '.webm'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm'}

def get_image_dimensions(image_path):
    """Get image width and height for images, or default dimensions for videos"""
    file_ext = Path(image_path).suffix.lower()
    
    # For videos, return default dimensions (will be handled by video player)
    if file_ext in VIDEO_EXTENSIONS:
        return 1920, 1080  # Default 16:9 aspect ratio
    
    # For images, use PIL
    try:
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception as e:
        print(f"Error reading image {image_path}: {e}")
        return None, None

def is_supported_image(filename):
    """Check if file is a supported image or video format"""
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS

def is_video(filename):
    """Check if file is a video format"""
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS

def get_all_folders(dataset_path, parent_path=''):
    """Get all category folders from dataset (recursive for hierarchical structure)"""
    folders = []
    base_path = os.path.join(dataset_path, parent_path) if parent_path else dataset_path
    
    if not os.path.exists(base_path):
        return folders
    
    try:
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Get relative path from dataset root
                rel_path = os.path.join(parent_path, item) if parent_path else item
                
                # Count images in this directory (not recursive)
                images = [f for f in os.listdir(item_path) 
                         if is_supported_image(f) and os.path.isfile(os.path.join(item_path, f))]
                image_count = len(images)
                
                # Get first image as thumbnail
                first_image = None
                if images:
                    # Image is in the current folder
                    first_image = os.path.join(rel_path, images[0])
                else:
                    # If no images in current folder, try to find first image in subfolders
                    try:
                        for sub in sorted(os.listdir(item_path)):
                            sub_path = os.path.join(item_path, sub)
                            if os.path.isdir(sub_path) and not sub.startswith('.'):
                                sub_images = [f for f in os.listdir(sub_path)
                                            if is_supported_image(f) and os.path.isfile(os.path.join(sub_path, f))]
                                if sub_images:
                                    first_image = os.path.join(rel_path, sub, sub_images[0])
                                    break
                    except:
                        pass
                
                # Count subfolders
                subfolder_count = sum(1 for sub in os.listdir(item_path)
                                     if os.path.isdir(os.path.join(item_path, sub)) and not sub.startswith('.'))
                
                # Include folder if it has images or subfolders
                if image_count > 0 or subfolder_count > 0:
                    folders.append({
                        'name': item,
                        'path': rel_path,
                        'count': image_count,
                        'has_subfolders': subfolder_count > 0,
                        'subfolder_count': subfolder_count,
                        'thumbnail': first_image
                    })
    except Exception as e:
        print(f"Error reading dataset: {e}")
    
    return sorted(folders, key=lambda x: x['name'])

def calculate_justified_layout(images, container_width=1200, row_height=200, gap=8):
    """
    Calculate optimal image layout using justified layout algorithm.
    This minimizes gaps between images while respecting aspect ratios.
    
    Args:
        images: List of image dicts with width, height, filename
        container_width: Width of container in pixels
        row_height: Fixed height for each row
        gap: Gap between images in pixels
    
    Returns:
        List of image dicts with calculated width, height, and position
    """
    if not images:
        return []
    
    layout = []
    current_row = []
    current_row_width = 0
    
    for image in images:
        aspect_ratio = image['width'] / image['height'] if image['height'] > 0 else 1
        img_width = int(row_height * aspect_ratio)
        
        # Check if adding this image would exceed container width
        total_width = current_row_width + img_width + (len(current_row) * gap)
        
        if total_width > container_width and current_row:
            # Process current row
            layout.extend(_justify_row(current_row, container_width, row_height, gap))
            current_row = [image]
            current_row_width = img_width
        else:
            current_row.append(image)
            current_row_width += img_width
    
    # Process last row
    if current_row:
        layout.extend(_justify_row(current_row, container_width, row_height, gap, is_last=True))
    
    return layout

def _justify_row(row, container_width, target_height, gap, is_last=False):
    """Justify a single row of images"""
    if not row:
        return []
    
    # Calculate total aspect ratio
    total_aspect_ratio = sum(img['width'] / img['height'] for img in row if img['height'] > 0)
    
    # Calculate available width (minus gaps)
    available_width = container_width - (len(row) - 1) * gap
    
    # Calculate actual height to fit all images in container width
    actual_height = available_width / total_aspect_ratio if total_aspect_ratio > 0 else target_height
    
    # For last row with single image, limit width to max 400px
    if is_last and len(row) == 1:
        aspect_ratio = row[0]['width'] / row[0]['height'] if row[0]['height'] > 0 else 1
        max_width = min(400, int(target_height * aspect_ratio))
        return [{
            **row[0],
            'calc_width': max_width,
            'calc_height': int(max_width / aspect_ratio)
        }]
    
    # For last row, use target height or calculated height (whichever is smaller)
    if is_last:
        actual_height = min(actual_height, target_height)
    
    # Distribute width proportionally
    result = []
    for i, img in enumerate(row):
        aspect_ratio = img['width'] / img['height'] if img['height'] > 0 else 1
        img_width = int(actual_height * aspect_ratio)
        
        # Adjust last image width to fit exactly (but not for single image rows)
        if i == len(row) - 1 and len(row) > 1:
            used_width = sum(r['calc_width'] for r in result) + (len(result) * gap)
            img_width = container_width - used_width
        
        result.append({
            **img,
            'calc_width': img_width,
            'calc_height': int(actual_height)
        })
    
    return result

def get_folder_images(dataset_path, folder_name, page=1, per_page=100, use_layout=True):
    """Get images from a specific folder with pagination"""
    folder_path = os.path.join(dataset_path, folder_name)
    
    if not os.path.exists(folder_path):
        return [], 0
    
    images = []
    try:
        for filename in os.listdir(folder_path):
            if is_supported_image(filename):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path):
                    width, height = get_image_dimensions(full_path)
                    if width and height:
                        file_size = os.path.getsize(full_path)
                        images.append({
                            'filename': filename,
                            'width': width,
                            'height': height,
                            'aspect_ratio': width / height,
                            'file_size': file_size,
                            'is_video': is_video(filename)
                        })
    except Exception as e:
        print(f"Error reading folder {folder_path}: {e}")
    
    # Sort by filename
    images.sort(key=lambda x: x['filename'])
    
    total = len(images)
    
    # Apply justified layout if requested
    if use_layout and images:
        images = calculate_justified_layout(images)
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    
    return images[start:end], total

def delete_image(dataset_path, folder_name, filename):
    """Delete an image file"""
    try:
        image_path = os.path.join(dataset_path, folder_name, filename)
        
        # Security check
        real_path = os.path.realpath(image_path)
        real_base = os.path.realpath(os.path.join(dataset_path, folder_name))
        
        if not real_path.startswith(real_base):
            return False, "Security: Path traversal detected"
        
        if os.path.exists(image_path) and is_supported_image(filename):
            os.remove(image_path)
            
            # Remove from database if exists
            ImageMetadata.query.filter_by(
                folder_path=folder_name,
                filename=filename
            ).delete()
            
            # Also remove all tags associated with this image
            from .models import ImageTag
            ImageTag.query.filter_by(
                folder_path=folder_name,
                filename=filename
            ).delete()
            
            db.session.commit()
            
            return True, "Image deleted successfully"
        else:
            return False, "Image not found"
    except Exception as e:
        return False, f"Error deleting image: {str(e)}"

def get_thumbnail_path(filename):
    """Generate thumbnail filename"""
    return f".thumb_{filename}"

def get_subfolders(dataset_path, parent_path):
    """Get immediate subfolders of a given folder"""
    return get_all_folders(dataset_path, parent_path)

def get_breadcrumb_path(folder_path):
    """Convert folder path to breadcrumb list"""
    if not folder_path:
        return []
    
    parts = folder_path.split(os.sep)
    breadcrumbs = []
    current_path = ''
    
    for part in parts:
        current_path = os.path.join(current_path, part) if current_path else part
        breadcrumbs.append({
            'name': part,
            'path': current_path
        })
    
    return breadcrumbs
