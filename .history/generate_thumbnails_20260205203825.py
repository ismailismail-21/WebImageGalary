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


def generate_thumbnail(source_path, thumb_path, size):
    """Generate a single thumbnail."""
    ext = Path(source_path).suffix.lower()
    
    try:
        if ext in VIDEO_EXTENSIONS:
            # Extract first frame from video
            cap = cv2.VideoCapture(source_path)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail((size, size), Image.LANCZOS)
                    img.save(thumb_path, 'JPEG', quality=JPEG_QUALITY)
                    cap.release()
                    return True
                cap.release()
            return False
        else:
            # Process image
            with Image.open(source_path) as img:
                # Handle animated GIFs - use first frame
                if hasattr(img, 'n_frames') and img.n_frames > 1:
                    img.seek(0)
                
                # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img.thumbnail((size, size), Image.LANCZOS)
                img.save(thumb_path, 'JPEG', quality=JPEG_QUALITY)
                return True
                
    except Exception as e:
        print(f"    ❌ Error: {os.path.basename(source_path)} - {e}")
        return False


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
        
        # Generate thumbnail filename (always .jpg)
        name = os.path.splitext(filename)[0]
        thumb_filename = f"{name}_thumb.jpg"
        thumb_path = os.path.join(thumb_dir, thumb_filename)
        
        # Check if thumbnail exists and is up-to-date
        if not force and os.path.exists(thumb_path):
            source_mtime = os.path.getmtime(source_path)
            thumb_mtime = os.path.getmtime(thumb_path)
            if thumb_mtime >= source_mtime:
                results['skipped'] += 1
                continue
        
        # Generate thumbnail
        if generate_thumbnail(source_path, thumb_path, size):
            results['created'] += 1
        else:
            results['failed'] += 1
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Generate thumbnails for all images in the dataset')
    parser.add_argument('--folder', '-f', type=str, help='Process only a specific folder (relative to dataset)')
    parser.add_argument('--size', '-s', type=int, default=DEFAULT_THUMB_SIZE, help=f'Thumbnail size in pixels (default: {DEFAULT_THUMB_SIZE})')
    parser.add_argument('--force', action='store_true', help='Regenerate all thumbnails even if they exist')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of parallel workers (default: 4)')
    args = parser.parse_args()
    
    print("🖼️  Thumbnail Generator")
    print("=" * 50)
    print(f"📁 Dataset: {DATASET_PATH}")
    print(f"📐 Size: {args.size}x{args.size}")
    print(f"🔄 Force regenerate: {args.force}")
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
    
    # Process folders
    total_created = 0
    total_skipped = 0
    total_failed = 0
    
    for folder in folders:
        rel_path = os.path.relpath(folder, DATASET_PATH)
        print(f"📁 Processing: {rel_path}")
        
        results = process_folder(folder, args.size, args.force)
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
