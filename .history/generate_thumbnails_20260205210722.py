#!/usr/bin/env python
"""
Generate thumbnails for all images in the dataset.
Run this once after adding new images for faster page loading.

Usage:
    python generate_thumbnails.py
    python generate_thumbnails.py --folder "corba"
    python generate_thumbnails.py --size 400
"""
import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration
DATASET_PATH = os.getenv('DATASET_PATH', os.path.join(os.path.dirname(__file__), 'dataset'))
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm'}
DEFAULT_THUMB_SIZE = 300
JPEG_QUALITY = 85


def get_all_folders(dataset_path):
    """Recursively get all folders containing images."""
    folders = []
    for root, dirs, files in os.walk(dataset_path):
        # Skip hidden folders and thumbnail folders
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Check if folder has images
        has_media = any(
            Path(f).suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
            for f in files
        )
        if has_media:
            folders.append(root)
    return folders


def clean_old_thumbnails(folder_path):
    """Remove all old thumbnails from a folder."""
    thumb_dir = os.path.join(folder_path, '.thumbnails')
    removed = 0
    if os.path.exists(thumb_dir):
        for f in os.listdir(thumb_dir):
            try:
                os.remove(os.path.join(thumb_dir, f))
                removed += 1
            except Exception as e:
                print(f"    ⚠️  Could not remove {f}: {e}")
    return removed


# Video preview settings
VIDEO_PREVIEW_DURATION = 3.0  # seconds of video to capture
VIDEO_PREVIEW_FPS = 8  # frames per second for preview


def generate_thumbnail(source_path, thumb_dir, filename, size):
    """Generate a single thumbnail. Returns (success, thumb_filename)."""
    ext = Path(source_path).suffix.lower()
    name = os.path.splitext(filename)[0]
    
    try:
        if ext in VIDEO_EXTENSIONS:
            # Create animated preview from video
            thumb_filename = f"{name}_thumb.webp"
            thumb_path = os.path.join(thumb_dir, thumb_filename)
            
            cap = cv2.VideoCapture(source_path)
            if not cap.isOpened():
                return False, None
            
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
                    img.thumbnail((size, size), Image.LANCZOS)
                    thumb_filename = f"{name}_thumb.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_filename)
                    img.save(thumb_path, 'JPEG', quality=JPEG_QUALITY)
                    cap.release()
                    return True, thumb_filename
                cap.release()
                return False, None
            
            # Calculate which frames to extract
            # Take frames from first VIDEO_PREVIEW_DURATION seconds (or whole video if shorter)
            preview_duration = min(VIDEO_PREVIEW_DURATION, duration)
            num_frames = int(preview_duration * VIDEO_PREVIEW_FPS)
            num_frames = max(4, min(num_frames, 30))  # Between 4-30 frames
            
            # Spread frames across the preview duration
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
                    img.thumbnail((size, size), Image.LANCZOS)
                    
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    frames.append(img)
            
            cap.release()
            
            if len(frames) >= 2:
                # Save as animated WebP
                frames[0].save(
                    thumb_path,
                    'WEBP',
                    save_all=True,
                    append_images=frames[1:],
                    duration=[frame_duration] * len(frames),
                    loop=0,
                    quality=75
                )
                return True, thumb_filename
            elif len(frames) == 1:
                # Only got one frame, save as static
                thumb_filename = f"{name}_thumb.jpg"
                thumb_path = os.path.join(thumb_dir, thumb_filename)
                frames[0].convert('RGB').save(thumb_path, 'JPEG', quality=JPEG_QUALITY)
                return True, thumb_filename
            
            return False, None
        else:
            # Process image
            with Image.open(source_path) as img:
                # Check if image is animated (GIF or animated WEBP)
                is_animated = hasattr(img, 'n_frames') and img.n_frames > 1
                
                if is_animated:
                    # Keep animation - save as animated WEBP (better compression than GIF)
                    thumb_filename = f"{name}_thumb.webp"
                    thumb_path = os.path.join(thumb_dir, thumb_filename)
                    
                    frames = []
                    durations = []
                    
                    # Get the base image size for consistent frame dimensions
                    base_width, base_height = img.size
                    
                    # Calculate thumbnail dimensions while maintaining aspect ratio
                    ratio = min(size / base_width, size / base_height)
                    thumb_width = int(base_width * ratio)
                    thumb_height = int(base_height * ratio)
                    
                    for frame_num in range(img.n_frames):
                        img.seek(frame_num)
                        # Get frame duration (default to 100ms if not available)
                        duration = img.info.get('duration', 100)
                        durations.append(duration)
                        
                        # Convert frame to RGBA first (handles palette mode, transparency, etc.)
                        frame = img.convert('RGBA')
                        
                        # Resize to exact same dimensions for all frames
                        frame = frame.resize((thumb_width, thumb_height), Image.LANCZOS)
                        
                        frames.append(frame)
                    
                    # Save animated WEBP
                    if frames:
                        frames[0].save(
                            thumb_path,
                            'WEBP',
                            save_all=True,
                            append_images=frames[1:] if len(frames) > 1 else [],
                            duration=durations,
                            loop=0,  # Loop forever
                            quality=80
                        )
                        return True, thumb_filename
                    return False, None
                else:
                    # Static image - save as JPEG
                    thumb_filename = f"{name}_thumb.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_filename)
                    
                    # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    img.thumbnail((size, size), Image.LANCZOS)
                    img.save(thumb_path, 'JPEG', quality=JPEG_QUALITY)
                    return True, thumb_filename
                
    except Exception as e:
        print(f"    ❌ Error: {os.path.basename(source_path)} - {e}")
        return False, None


def process_folder(folder_path, size, force=False):
    """Process all images in a folder and generate thumbnails."""
    results = {'created': 0, 'skipped': 0, 'failed': 0}
    
    # Create thumbnails directory
    thumb_dir = os.path.join(folder_path, '.thumbnails')
    os.makedirs(thumb_dir, exist_ok=True)
    
    # Get all media files
    files = [
        f for f in os.listdir(folder_path)
        if Path(f).suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
        and os.path.isfile(os.path.join(folder_path, f))
    ]
    
    for filename in files:
        source_path = os.path.join(folder_path, filename)
        
        # Check if any thumbnail exists for this file (could be .jpg or .webp)
        name = os.path.splitext(filename)[0]
        possible_thumbs = [
            os.path.join(thumb_dir, f"{name}_thumb.jpg"),
            os.path.join(thumb_dir, f"{name}_thumb.webp")
        ]
        
        # Check if thumbnail exists and is up-to-date
        existing_thumb = None
        for thumb_path in possible_thumbs:
            if os.path.exists(thumb_path):
                existing_thumb = thumb_path
                break
        
        if not force and existing_thumb:
            source_mtime = os.path.getmtime(source_path)
            thumb_mtime = os.path.getmtime(existing_thumb)
            if thumb_mtime >= source_mtime:
                results['skipped'] += 1
                continue
        
        # Generate thumbnail
        success, thumb_filename = generate_thumbnail(source_path, thumb_dir, filename, size)
        if success:
            results['created'] += 1
        else:
            results['failed'] += 1
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Generate thumbnails for all images in the dataset')
    parser.add_argument('--folder', '-f', type=str, help='Process only a specific folder (relative to dataset)')
    parser.add_argument('--size', '-s', type=int, default=DEFAULT_THUMB_SIZE, help=f'Thumbnail size in pixels (default: {DEFAULT_THUMB_SIZE})')
    parser.add_argument('--force', action='store_true', help='Regenerate all thumbnails even if they exist')
    parser.add_argument('--clean', '-c', action='store_true', help='Remove old thumbnails before generating new ones')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of parallel workers (default: 4)')
    args = parser.parse_args()
    
    print("🖼️  Thumbnail Generator")
    print("=" * 50)
    print(f"📁 Dataset: {DATASET_PATH}")
    print(f"📐 Size: {args.size}x{args.size}")
    print(f"🔄 Force regenerate: {args.force}")
    print(f"🧹 Clean old thumbnails: {args.clean}")
    print(f"👷 Workers: {args.workers}")
    print("=" * 50)
    
    start_time = time.time()
    
    # Get folders to process
    if args.folder:
        target_folder = os.path.join(DATASET_PATH, args.folder)
        if not os.path.exists(target_folder):
            print(f"❌ Folder not found: {args.folder}")
            sys.exit(1)
        folders = [target_folder]
        # Also get subfolders
        for root, dirs, files in os.walk(target_folder):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for d in dirs:
                subdir = os.path.join(root, d)
                if any(Path(f).suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS 
                       for f in os.listdir(subdir) if os.path.isfile(os.path.join(subdir, f))):
                    folders.append(subdir)
    else:
        folders = get_all_folders(DATASET_PATH)
    
    if not folders:
        print("⚠️  No folders with images found.")
        sys.exit(0)
    
    print(f"\n📂 Found {len(folders)} folder(s) to process\n")
    
    # Clean old thumbnails if requested
    if args.clean:
        print("🧹 Cleaning old thumbnails...")
        total_removed = 0
        for folder in folders:
            removed = clean_old_thumbnails(folder)
            total_removed += removed
        print(f"   Removed {total_removed} old thumbnail(s)\n")
    
    # Process folders
    total_created = 0
    total_skipped = 0
    total_failed = 0
    
    for folder in folders:
        rel_path = os.path.relpath(folder, DATASET_PATH)
        print(f"📁 Processing: {rel_path}")
        
        # If clean was used, force regenerate all
        force = args.force or args.clean
        results = process_folder(folder, args.size, force)
        total_created += results['created']
        total_skipped += results['skipped']
        total_failed += results['failed']
        
        if results['created'] > 0 or results['failed'] > 0:
            print(f"    ✅ Created: {results['created']} | ⏭️  Skipped: {results['skipped']} | ❌ Failed: {results['failed']}")
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print("📊 Summary")
    print("=" * 50)
    print(f"✅ Thumbnails created: {total_created}")
    print(f"⏭️  Already existed: {total_skipped}")
    print(f"❌ Failed: {total_failed}")
    print(f"⏱️  Time: {elapsed:.1f} seconds")
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
