#!/usr/bin/env python
"""
Scan folders and save metadata to database.
Run this after adding new images to index them for faster loading.

Usage:
    python scan_folders.py
    python scan_folders.py --folder "corba"
    python scan_folders.py --with-thumbnails
"""
import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import FileMetadata
from app.utils import is_supported_image, extract_file_metadata, generate_thumbnail, VIDEO_EXTENSIONS

# Configuration
DATASET_PATH = os.getenv('DATASET_PATH', os.path.join(os.path.dirname(__file__), 'dataset'))


def get_all_folders(dataset_path):
    """Recursively get all folders containing images."""
    folders = []
    for root, dirs, files in os.walk(dataset_path):
        # Skip hidden folders and thumbnail folders
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Check if folder has media files
        has_media = any(is_supported_image(f) for f in files)
        if has_media:
            folders.append(root)
    return folders


def scan_folder(folder_path, dataset_path, with_thumbnails=False):
    """Scan a folder and save metadata to database."""
    results = {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0}
    
    files = [
        f for f in os.listdir(folder_path)
        if is_supported_image(f) and os.path.isfile(os.path.join(folder_path, f))
    ]
    
    rel_folder = os.path.relpath(folder_path, dataset_path)
    if rel_folder == '.':
        rel_folder = ''
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        try:
            # Get file stats
            stat = os.stat(filepath)
            file_size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            
            # Check if already in database and up-to-date
            existing = FileMetadata.query.filter_by(
                folder_path=rel_folder,
                filename=filename
            ).first()
            
            if existing and existing.modified_at and existing.modified_at >= modified_time:
                results['skipped'] += 1
                continue
            
            # Determine file type
            file_ext = Path(filename).suffix.lower()
            if file_ext in VIDEO_EXTENSIONS:
                file_type = 'video'
            elif file_ext == '.gif':
                file_type = 'gif'
            else:
                file_type = 'image'
            
            # Extract metadata (width, height, duration, fps)
            width, height, duration, fps = extract_file_metadata(filepath, file_type)
            
            # Generate thumbnail if requested
            thumbnail_path = None
            if with_thumbnails:
                thumbnail_path = generate_thumbnail(filepath, dataset_path)
            
            if existing:
                # Update existing record
                existing.file_type = file_type
                existing.file_size = file_size
                existing.width = width
                existing.height = height
                existing.duration = duration
                existing.fps = fps
                existing.modified_at = modified_time
                if thumbnail_path:
                    existing.thumbnail_path = thumbnail_path
                results['updated'] += 1
            else:
                # Create new record
                metadata = FileMetadata(
                    folder_path=rel_folder,
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
                results['created'] += 1
                
        except Exception as e:
            print(f"    ❌ Error: {filename} - {e}")
            results['failed'] += 1
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Scan folders and save metadata to database')
    parser.add_argument('--folder', '-f', type=str, help='Process only a specific folder (relative to dataset)')
    parser.add_argument('--with-thumbnails', '-t', action='store_true', help='Also generate thumbnails during scan')
    parser.add_argument('--force', action='store_true', help='Rescan all files even if already in database')
    args = parser.parse_args()
    
    print("📊 Folder Scanner")
    print("=" * 50)
    print(f"📁 Dataset: {DATASET_PATH}")
    print(f"🖼️  Generate thumbnails: {args.with_thumbnails}")
    print(f"🔄 Force rescan: {args.force}")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
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
                    if any(is_supported_image(f) for f in os.listdir(subdir) 
                           if os.path.isfile(os.path.join(subdir, f))):
                        folders.append(subdir)
        else:
            folders = get_all_folders(DATASET_PATH)
        
        if not folders:
            print("⚠️  No folders with images found.")
            sys.exit(0)
        
        print(f"\n📂 Found {len(folders)} folder(s) to process\n")
        
        # Process folders
        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_failed = 0
        
        for folder in folders:
            rel_path = os.path.relpath(folder, DATASET_PATH)
            print(f"📁 Scanning: {rel_path}")
            
            results = scan_folder(folder, DATASET_PATH, args.with_thumbnails)
            total_created += results['created']
            total_updated += results['updated']
            total_skipped += results['skipped']
            total_failed += results['failed']
            
            if results['created'] > 0 or results['updated'] > 0 or results['failed'] > 0:
                print(f"    ✅ New: {results['created']} | 🔄 Updated: {results['updated']} | ⏭️  Skipped: {results['skipped']} | ❌ Failed: {results['failed']}")
            
            # Commit after each folder
            db.session.commit()
        
        # Summary
        elapsed = time.time() - start_time
        total_processed = total_created + total_updated
        
        print("\n" + "=" * 50)
        print("📊 Summary")
        print("=" * 50)
        print(f"✅ New entries: {total_created}")
        print(f"🔄 Updated: {total_updated}")
        print(f"⏭️  Unchanged: {total_skipped}")
        print(f"❌ Failed: {total_failed}")
        print(f"⏱️  Time: {elapsed:.1f} seconds")
        
        # Show database stats
        total_in_db = FileMetadata.query.count()
        print(f"\n📈 Total files in database: {total_in_db}")
        print("\n✨ Done!")


if __name__ == '__main__':
    main()
