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

def get_folder_images(dataset_path, folder_name, page=1, per_page=1, use_layout=True):
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

# Background scanning and optimization functions

def scan_folder_background(dataset_path, folder_name, app=None):
    """Scan folder in background and update database with metadata and thumbnails"""
    def scan():
        # Import current_app here to avoid circular imports
        from flask import current_app
        
        # Get the app instance - either passed in or use current_app
        app_instance = app or current_app._get_current_object()
        
        with app_instance.app_context():
            folder_path = os.path.join(dataset_path, folder_name)
            if not os.path.exists(folder_path):
                print(f"Folder not found: {folder_path}")
                return

            print(f"Starting background scan of {folder_name}")
            files_processed = 0

            try:
                # Walk through all files in the folder
                for root, dirs, filenames in os.walk(folder_path):
                    # Skip hidden directories and thumbnail directory
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.thumbnails']

                    for filename in filenames:
                        if is_supported_image(filename):
                            rel_path = os.path.relpath(root, dataset_path)
                            filepath = os.path.join(root, filename)

                            try:
                                # Get file metadata
                                stat = os.stat(filepath)
                                file_size = stat.st_size
                                modified_time = datetime.fromtimestamp(stat.st_mtime)

                                # Determine file type
                                file_ext = Path(filename).suffix.lower()
                                if file_ext in VIDEO_EXTENSIONS:
                                    file_type = 'video'
                                elif file_ext == '.gif':
                                    file_type = 'gif'
                                else:
                                    file_type = 'image'

                                # Extract dimensions and metadata
                                width, height, duration, fps = extract_file_metadata(filepath, file_type)

                                # Generate thumbnail
                                thumbnail_path = generate_thumbnail(filepath, dataset_path)

                                # Update or create database entry
                                metadata = FileMetadata.query.filter_by(
                                    folder_path=rel_path,
                                    filename=filename
                                ).first()

                                if metadata:
                                    # Update existing
                                    metadata.file_size = file_size
                                    metadata.file_type = file_type
                                    metadata.width = width
                                    metadata.height = height
                                    metadata.duration = duration
                                    metadata.fps = fps
                                    metadata.thumbnail_path = thumbnail_path
                                    metadata.modified_at = modified_time
                                else:
                                    # Create new
                                    metadata = FileMetadata(
                                        folder_path=rel_path,
                                        filename=filename,
                                        file_type=file_type,
                                        file_size=file_size,
                                        width=width,
                                        height=height,
                                        duration=duration,
                                        fps=fps,
                                        thumbnail_path=thumbnail_path,
                                        modified_at=modified_time
                                    )
                                    db.session.add(metadata)

                                files_processed += 1

                                # Commit in batches to avoid memory issues
                                if files_processed % 100 == 0:
                                    db.session.commit()
                                    print(f"Processed {files_processed} files in {folder_name}")

                            except Exception as e:
                                print(f"Error processing {filepath}: {e}")
                                continue

                # Final commit
                db.session.commit()
                print(f"Completed background scan of {folder_name}: {files_processed} files processed")

            except Exception as e:
                print(f"Error during background scan of {folder_name}: {e}")
                db.session.rollback()

    thread = threading.Thread(target=scan, daemon=True)
    thread.start()
    return thread

def extract_file_metadata(filepath, file_type):
    """Extract width, height, duration, and fps from file"""
    width = height = duration = fps = None

    try:
        if file_type == 'video':
            # Use OpenCV for video metadata
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps and fps > 0 else None
                cap.release()
        else:
            # Use PIL for images and GIFs
            with Image.open(filepath) as img:
                width, height = img.size
                # For animated GIFs, try to get duration
                if hasattr(img, 'is_animated') and img.is_animated:
                    duration = sum(img.info.get('duration', 100) for _ in range(img.n_frames)) / 1000.0  # Convert to seconds

    except Exception as e:
        print(f"Error extracting metadata from {filepath}: {e}")

    return width, height, duration, fps

def generate_thumbnail(filepath, dataset_path):
    """Generate thumbnail and return relative path"""
    rel_path = os.path.relpath(filepath, dataset_path)
    file_dir = os.path.dirname(rel_path)
    filename = os.path.basename(rel_path)

    # Create thumbnails directory
    thumb_dir = os.path.join(dataset_path, file_dir, '.thumbnails')
    os.makedirs(thumb_dir, exist_ok=True)

    # Generate thumbnail filename
    name, ext = os.path.splitext(filename)
    thumb_filename = f"{name}_thumb.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_filename)

    # Check if thumbnail already exists and is up to date
    if os.path.exists(thumb_path):
        thumb_mtime = os.path.getmtime(thumb_path)
        file_mtime = os.path.getmtime(filepath)
        if thumb_mtime >= file_mtime:
            # Thumbnail is up to date
            return os.path.relpath(thumb_path, dataset_path)

    try:
        file_ext = Path(filepath).suffix.lower()

        if file_ext in VIDEO_EXTENSIONS:
            # Extract first frame for video thumbnail
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail((300, 300))
                    img.save(thumb_path, 'JPEG', quality=85)
                cap.release()
        else:
            # Process image/GIF
            with Image.open(filepath) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                img.thumbnail((300, 300))
                img.save(thumb_path, 'JPEG', quality=85)

        return os.path.relpath(thumb_path, dataset_path)

    except Exception as e:
        print(f"Error generating thumbnail for {filepath}: {e}")
        return None

def get_folder_files_cached(dataset_path, folder_name, page=1, per_page=50):
    """Get files from database with caching, fallback to scanning if needed"""
    from flask import current_app
    
    # Check if we have recent metadata for this folder
    last_scan = FileMetadata.query.filter_by(folder_path=folder_name).order_by(FileMetadata.modified_at.desc()).first()

    # If no data or data is older than 1 hour, trigger background scan
    needs_scan = False
    if not last_scan:
        needs_scan = True
    else:
        time_diff = (datetime.utcnow() - last_scan.modified_at).total_seconds()
        if time_diff > 3600:  # 1 hour
            needs_scan = True

    if needs_scan:
        scan_folder_background(dataset_path, folder_name, current_app._get_current_object())

    # Get paginated results from database
    query = FileMetadata.query.filter_by(folder_path=folder_name).order_by(FileMetadata.filename)

    total = query.count()
    files = query.offset((page - 1) * per_page).limit(per_page).all()

    return [f.to_dict() for f in files], total
