#!/usr/bin/env python3
"""
Process images: Generate thumbnails and save to database with resume support.
Skips files that already have thumbnails in the database.
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import FileMetadata
from app.utils import generate_thumbnail

# Supported formats
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.wmv', '.flv'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def get_file_type(filepath):
    """Determine file type based on extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'unknown'


def get_file_hash(filepath, chunk_size=8192):
    """Calculate MD5 hash of file for change detection."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(chunk_size)
            while chunk:
                hasher.update(chunk)
                chunk = f.read(chunk_size)
        return hasher.hexdigest()
    except:
        return None


def get_relative_path(filepath, base_path):
    """Get path relative to dataset folder."""
    try:
        return os.path.relpath(filepath, base_path)
    except:
        return filepath


def process_single_file(filepath, base_path, thumb_size, force=False):
    """
    Process a single file: generate thumbnail and return metadata.
    Returns dict with file info or None if skipped/failed.
    """
    try:
        relative_path = get_relative_path(filepath, base_path)
        folder_path = os.path.dirname(relative_path)
        filename = os.path.basename(filepath)
        
        # Get file info
        stat = os.stat(filepath)
        file_size = stat.st_size
        file_type = get_file_type(filepath)
        
        # Generate thumbnail (requires filepath and dataset_path)
        thumb_path = generate_thumbnail(filepath, base_path, thumb_size=thumb_size)
        
        return {
            'filepath': filepath,
            'folder_path': folder_path,
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'thumbnail_path': thumb_path,
            'success': True
        }
    except Exception as e:
        return {
            'filepath': filepath,
            'success': False,
            'error': str(e)
        }


def get_processed_files(app):
    """Get set of files already processed (have thumbnail in database)."""
    with app.app_context():
        # Get all files that have thumbnails
        processed = set()
        results = db.session.query(
            FileMetadata.folder_path, 
            FileMetadata.filename,
            FileMetadata.thumbnail_path
        ).filter(
            FileMetadata.thumbnail_path.isnot(None),
            FileMetadata.thumbnail_path != ''
        ).all()
        
        for folder_path, filename, thumb_path in results:
            # Check if thumbnail file actually exists
            if thumb_path and os.path.exists(thumb_path):
                processed.add((folder_path, filename))
        
        return processed


def save_to_database(app, file_info, base_path):
    """Save file metadata to database."""
    with app.app_context():
        try:
            # Check if already exists
            existing = FileMetadata.query.filter_by(
                folder_path=file_info['folder_path'],
                filename=file_info['filename']
            ).first()
            
            if existing:
                # Update existing record
                existing.thumbnail_path = file_info['thumbnail_path']
                existing.file_type = file_info['file_type']
                existing.file_size = file_info['file_size']
            else:
                # Create new record
                metadata = FileMetadata(
                    folder_path=file_info['folder_path'],
                    filename=file_info['filename'],
                    file_type=file_info['file_type'],
                    file_size=file_info['file_size'],
                    thumbnail_path=file_info['thumbnail_path']
                )
                db.session.add(metadata)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"  Database error: {e}")
            return False


def find_all_files(folder_path, recursive=True):
    """Find all supported media files in folder."""
    files = []
    
    if recursive:
        for root, dirs, filenames in os.walk(folder_path):
            # Skip thumbnail directories
            dirs[:] = [d for d in dirs if d != 'thumbnails']
            
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, filename))
    else:
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(filepath)
    
    return files


def main():
    parser = argparse.ArgumentParser(
        description='Process images: generate thumbnails and save to database with resume support'
    )
    parser.add_argument(
        '--folder', '-f',
        help='Specific folder to process (full path or relative to dataset)'
    )
    parser.add_argument(
        '--size', '-s',
        type=int,
        default=300,
        help='Thumbnail size in pixels (default: 300)'
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regenerate all thumbnails (ignore resume)'
    )
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not process subfolders'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually doing it'
    )
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    
    # Determine base dataset path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_dataset = os.path.join(script_dir, 'dataset')
    
    # Determine folder to process
    if args.folder:
        if os.path.isabs(args.folder):
            target_folder = args.folder
            base_path = args.folder
        else:
            target_folder = os.path.join(default_dataset, args.folder)
            base_path = default_dataset
    else:
        target_folder = default_dataset
        base_path = default_dataset
    
    if not os.path.exists(target_folder):
        print(f"Error: Folder not found: {target_folder}")
        sys.exit(1)
    
    print(f"=" * 60)
    print(f"Processing: {target_folder}")
    print(f"Thumbnail size: {args.size}px")
    print(f"Workers: {args.workers}")
    print(f"Force regenerate: {args.force}")
    print(f"Recursive: {not args.no_recursive}")
    print(f"=" * 60)
    
    # Find all files
    print("\nScanning for files...")
    all_files = find_all_files(target_folder, recursive=not args.no_recursive)
    print(f"Found {len(all_files)} media files")
    
    if not all_files:
        print("No files to process.")
        return
    
    # Get already processed files (for resume)
    if not args.force:
        print("Checking for already processed files...")
        processed = get_processed_files(app)
        print(f"Already processed: {len(processed)} files")
        
        # Filter out already processed
        files_to_process = []
        for filepath in all_files:
            relative_path = get_relative_path(filepath, base_path)
            folder_path = os.path.dirname(relative_path)
            filename = os.path.basename(filepath)
            
            if (folder_path, filename) not in processed:
                files_to_process.append(filepath)
        
        skipped = len(all_files) - len(files_to_process)
        if skipped > 0:
            print(f"Skipping {skipped} already processed files")
    else:
        files_to_process = all_files
    
    print(f"\nFiles to process: {len(files_to_process)}")
    
    if not files_to_process:
        print("All files already processed!")
        return
    
    if args.dry_run:
        print("\n[DRY RUN] Would process:")
        for f in files_to_process[:20]:
            print(f"  - {os.path.basename(f)}")
        if len(files_to_process) > 20:
            print(f"  ... and {len(files_to_process) - 20} more")
        return
    
    # Process files
    print(f"\nProcessing {len(files_to_process)} files...")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    start_time = datetime.now()
    
    # Process with thread pool
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_file, 
                filepath, 
                base_path, 
                args.size,
                args.force
            ): filepath 
            for filepath in files_to_process
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(futures), 1):
            filepath = futures[future]
            filename = os.path.basename(filepath)
            
            try:
                result = future.result()
                
                if result['success']:
                    # Save to database immediately
                    if save_to_database(app, result, base_path):
                        success_count += 1
                        status = "✓"
                    else:
                        error_count += 1
                        status = "✗ DB"
                else:
                    error_count += 1
                    status = f"✗ {result.get('error', 'Unknown error')[:30]}"
                
                # Progress display
                progress = (i / len(files_to_process)) * 100
                print(f"[{i}/{len(files_to_process)}] {progress:5.1f}% {status} {filename[:50]}")
                
            except Exception as e:
                error_count += 1
                print(f"[{i}/{len(files_to_process)}] ✗ Error: {e}")
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print("-" * 60)
    print(f"\nCompleted in {elapsed:.1f} seconds")
    print(f"  Success: {success_count}")
    print(f"  Errors:  {error_count}")
    print(f"  Total:   {success_count + error_count}")
    
    if success_count > 0:
        print(f"\nThumbnails saved and database updated!")
        print(f"Average: {elapsed/max(success_count,1):.2f} seconds per file")


if __name__ == '__main__':
    main()
