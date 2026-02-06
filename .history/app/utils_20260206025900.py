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
                if parts[0] and parts[0] not in seen:
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
                
                if top_folder and top_folder not in seen:
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

def get_folder_images(dataset_path, folder_name, page=1, per_page=30, use_layout=True):
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

# Video preview settings
VIDEO_PREVIEW_DURATION = 3.0  # seconds of video to capture
VIDEO_PREVIEW_FPS = 8  # frames per second for preview


def generate_thumbnail(filepath, dataset_path, thumb_size=300):
    """Generate thumbnail and return relative path. Preserves animation for GIF/WEBP and creates animated previews for videos."""
    rel_path = os.path.relpath(filepath, dataset_path)
    file_dir = os.path.dirname(rel_path)
    filename = os.path.basename(rel_path)
    name, ext = os.path.splitext(filename)

    # Create thumbnails directory
    thumb_dir = os.path.join(dataset_path, file_dir, '.thumbnails')
    os.makedirs(thumb_dir, exist_ok=True)

    # Check for existing thumbnails (could be .jpg or .webp for animated)
    possible_thumbs = [
        (f"{name}_thumb.jpg", os.path.join(thumb_dir, f"{name}_thumb.jpg")),
        (f"{name}_thumb.webp", os.path.join(thumb_dir, f"{name}_thumb.webp"))
    ]
    
    file_mtime = os.path.getmtime(filepath)
    for thumb_filename, thumb_path in possible_thumbs:
        if os.path.exists(thumb_path):
            thumb_mtime = os.path.getmtime(thumb_path)
            if thumb_mtime >= file_mtime:
                # Thumbnail is up to date
                return os.path.relpath(thumb_path, dataset_path)

    try:
        file_ext = Path(filepath).suffix.lower()

        if file_ext in VIDEO_EXTENSIONS:
            # Create animated preview from video
            thumb_filename = f"{name}_thumb.webp"
            thumb_path = os.path.join(thumb_dir, thumb_filename)
            
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return None
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
            duration = total_frames / video_fps if video_fps > 0 else 0
            
            if total_frames < 2 or duration < 0.1:
                # Very short video - just get first frame as static
                ret, frame = cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail((thumb_size, thumb_size))
                    thumb_filename = f"{name}_thumb.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_filename)
                    img.save(thumb_path, 'JPEG', quality=85)
                    cap.release()
                    return os.path.relpath(thumb_path, dataset_path)
                cap.release()
                return None
            
            # Calculate which frames to extract
            preview_duration = min(VIDEO_PREVIEW_DURATION, duration)
            num_frames = int(preview_duration * VIDEO_PREVIEW_FPS)
            num_frames = max(4, min(num_frames, 30))  # Between 4-30 frames
            
            frame_interval = (preview_duration * video_fps) / num_frames
            
            frames = []
            frame_duration = int(1000 / VIDEO_PREVIEW_FPS)  # ms per frame
            
            for i in range(num_frames):
                frame_pos = int(i * frame_interval)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                ret, frame = cap.read()
                
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail((thumb_size, thumb_size))
                    
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    frames.append(img)
            
            cap.release()
            
            if len(frames) >= 2:
                frames[0].save(
                    thumb_path,
                    'WEBP',
                    save_all=True,
                    append_images=frames[1:],
                    duration=[frame_duration] * len(frames),
                    loop=0,
                    quality=75
                )
                return os.path.relpath(thumb_path, dataset_path)
            elif len(frames) == 1:
                thumb_filename = f"{name}_thumb.jpg"
                thumb_path = os.path.join(thumb_dir, thumb_filename)
                frames[0].convert('RGB').save(thumb_path, 'JPEG', quality=85)
                return os.path.relpath(thumb_path, dataset_path)
            
            return None
        else:
            # Process image
            with Image.open(filepath) as img:
                # Check if image is animated (GIF or animated WEBP)
                is_animated = hasattr(img, 'n_frames') and img.n_frames > 1
                
                if is_animated:
                    # Keep animation - save as animated WEBP
                    thumb_filename = f"{name}_thumb.webp"
                    thumb_path = os.path.join(thumb_dir, thumb_filename)
                    
                    frames = []
                    durations = []
                    
                    # Get the base image size for consistent frame dimensions
                    base_width, base_height = img.size
                    
                    # Calculate thumbnail dimensions while maintaining aspect ratio
                    ratio = min(thumb_size / base_width, thumb_size / base_height)
                    final_width = int(base_width * ratio)
                    final_height = int(base_height * ratio)
                    
                    for frame_num in range(img.n_frames):
                        img.seek(frame_num)
                        duration = img.info.get('duration', 100)
                        durations.append(duration)
                        
                        # Convert frame to RGBA first (handles palette mode, transparency, etc.)
                        frame = img.convert('RGBA')
                        
                        # Resize to exact same dimensions for all frames
                        frame = frame.resize((final_width, final_height), Image.LANCZOS)
                        
                        frames.append(frame)
                    
                    if frames:
                        frames[0].save(
                            thumb_path,
                            'WEBP',
                            save_all=True,
                            append_images=frames[1:] if len(frames) > 1 else [],
                            duration=durations,
                            loop=0,
                            quality=80
                        )
                        return os.path.relpath(thumb_path, dataset_path)
                else:
                    # Static image - save as JPEG
                    thumb_filename = f"{name}_thumb.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_filename)
                    
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                    img.thumbnail((thumb_size, thumb_size))
                    img.save(thumb_path, 'JPEG', quality=85)
                    return os.path.relpath(thumb_path, dataset_path)

    except Exception as e:
        print(f"Error generating thumbnail for {filepath}: {e}")
        return None

def get_folder_files_cached(dataset_path, folder_name, page=1, per_page=30):
    """Get files with pagination - uses file system to avoid database locks"""
    try:
        # Use file-based approach to avoid database locks
        return get_folder_images(dataset_path, folder_name, page, per_page, use_layout=True)
    except Exception as e:
        print(f"Error in get_folder_files_cached: {e}")
        import traceback
        traceback.print_exc()
        # Return empty result on error
        return [], 0
