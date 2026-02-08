import os
from pathlib import Path
from .models import FileMetadata, ImageMetadata
from . import db
import math

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.mp4', '.mov', '.avi', '.webm'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}

def is_supported_image(filename):
    """Check if file is a supported image or video format"""
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS

def is_video(filename):
    """Check if file is a video format"""
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS

def get_all_folders(dataset_path, parent_path=''):
    """Get all category folders from database (only shows scanned folders)"""
    from sqlalchemy import func, distinct
    
    folders = []
    
    try:
        # Get all unique folder paths from database
        if parent_path:
            # Get subfolders of parent_path
            # Match folders that start with parent_path/ but don't have further subfolders at this level
            like_pattern = f"{parent_path}/%"
            
            # Get all folder_paths that match this pattern
            all_paths = db.session.query(
                FileMetadata.folder_path
            ).filter(
                FileMetadata.folder_path.like(like_pattern)
            ).distinct().all()
            
            # Extract immediate children only
            seen = set()
            for (folder_path,) in all_paths:
                # Remove parent prefix to get relative part
                rel = folder_path[len(parent_path)+1:]  # +1 for the /
                # Get first part (immediate subfolder)
                parts = rel.split('/')
                # Skip .thumbnails folders
                if parts[0] and parts[0] not in seen and parts[0] != '.thumbnails':
                    seen.add(parts[0])
                    child_path = f"{parent_path}/{parts[0]}"
                    
                    # Count images in this folder (and subfolders)
                    count = FileMetadata.query.filter(
                        FileMetadata.folder_path.like(f"{child_path}%")
                    ).count()
                    
                    # Count subfolders
                    subfolder_paths = db.session.query(
                        FileMetadata.folder_path
                    ).filter(
                        FileMetadata.folder_path.like(f"{child_path}/%")
                    ).distinct().all()
                    
                    subfolder_names = set()
                    for (sf_path,) in subfolder_paths:
                        sf_rel = sf_path[len(child_path)+1:]
                        sf_parts = sf_rel.split('/')
                        if sf_parts[0]:
                            subfolder_names.add(sf_parts[0])
                    
                    # Get first image as thumbnail
                    first_file = FileMetadata.query.filter(
                        FileMetadata.folder_path.like(f"{child_path}%")
                    ).order_by(FileMetadata.filename).first()
                    
                    thumbnail = None
                    if first_file:
                        thumbnail = f"{first_file.folder_path}/{first_file.filename}"
                    
                    folders.append({
                        'name': parts[0],
                        'path': child_path,
                        'count': count,
                        'has_subfolders': len(subfolder_names) > 0,
                        'subfolder_count': len(subfolder_names),
                        'thumbnail': thumbnail
                    })
        else:
            # Get top-level folders
            all_paths = db.session.query(
                FileMetadata.folder_path
            ).distinct().all()
            
            # Extract top-level folder names
            seen = set()
            for (folder_path,) in all_paths:
                parts = folder_path.split('/')
                top_folder = parts[0]
                # Skip .thumbnails folders
                if top_folder and top_folder not in seen and top_folder != '.thumbnails':
                    seen.add(top_folder)
                    
                    # Count images in this top-level folder (and all subfolders)
                    count = FileMetadata.query.filter(
                        FileMetadata.folder_path.like(f"{top_folder}%")
                    ).count()
                    
                    # Count subfolders
                    subfolder_paths = db.session.query(
                        FileMetadata.folder_path
                    ).filter(
                        FileMetadata.folder_path.like(f"{top_folder}/%")
                    ).distinct().all()
                    
                    subfolder_names = set()
                    for (sf_path,) in subfolder_paths:
                        sf_rel = sf_path[len(top_folder)+1:]
                        sf_parts = sf_rel.split('/')
                        if sf_parts[0]:
                            subfolder_names.add(sf_parts[0])
                    
                    # Get first image as thumbnail
                    first_file = FileMetadata.query.filter(
                        FileMetadata.folder_path.like(f"{top_folder}%")
                    ).order_by(FileMetadata.filename).first()
                    
                    thumbnail = None
                    if first_file:
                        thumbnail = f"{first_file.folder_path}/{first_file.filename}"
                    
                    folders.append({
                        'name': top_folder,
                        'path': top_folder,
                        'count': count,
                        'has_subfolders': len(subfolder_names) > 0,
                        'subfolder_count': len(subfolder_names),
                        'thumbnail': thumbnail
                    })
    except Exception as e:
        print(f"Error getting folders from database: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"DEBUG: get_all_folders() returning {len(folders)} folders")
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

def get_folder_images(dataset_path, folder_name, page=1, per_page=30, use_layout=True, shuffle=False):
    """Get images from database for a specific folder with pagination"""
    images = []
    
    try:
        # Query database for images in this exact folder (not subfolders)
        if shuffle:
            from sqlalchemy import func
            query = FileMetadata.query.filter_by(folder_path=folder_name).order_by(func.random())
        else:
            query = FileMetadata.query.filter_by(folder_path=folder_name).order_by(FileMetadata.filename)
        
        total = query.count()
        
        # Get all for layout calculation
        all_files = query.all()
        
        for fm in all_files:
            # Use dimensions from database (default to 300x300 if missing)
            width = fm.width or 300
            height = fm.height or 300
            
            images.append({
                'filename': fm.filename,
                'width': width,
                'height': height,
                'aspect_ratio': width / height if height > 0 else 1,
                'file_size': fm.file_size or 0,
                'is_video': fm.file_type == 'video'
            })
    except Exception as e:
        print(f"Error getting images from database: {e}")
    
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

def get_subfolders(dataset_path, parent_path):
    """Get immediate subfolders of a given folder"""
    return get_all_folders(dataset_path, parent_path)

def get_breadcrumb_path(folder_path):
    """Convert folder path to breadcrumb list"""
    if not folder_path:
        return []
    
    # Normalize path separators to forward slashes for consistency
    # This ensures the function works the same on Windows, macOS, and Linux
    normalized_path = folder_path.replace('\\', '/')
    parts = normalized_path.split('/')
    breadcrumbs = []
    current_path = ''
    
    for part in parts:
        if not part:  # Skip empty parts from leading/trailing slashes
            continue
        current_path = f"{current_path}/{part}" if current_path else part
        breadcrumbs.append({
            'name': part,
            'path': current_path
        })
    
    return breadcrumbs

def get_folder_files_cached(dataset_path, folder_name, page=1, per_page=30, shuffle=False):
    """Get files with pagination - uses database for fast retrieval"""
    try:
        return get_folder_images(dataset_path, folder_name, page, per_page, use_layout=True, shuffle=shuffle)
    except Exception as e:
        print(f"Error in get_folder_files_cached: {e}")
        import traceback
        traceback.print_exc()
        # Return empty result on error
        return [], 0
