#!/usr/bin/env python3
"""
Scan images and their thumbnails into the database.
Thumbnails are expected in 'thumbnails' subfolder of each image folder.
Supports scanning a specific folder or all folders.
"""

import os
import sys
import argparse
from datetime import datetime
from PIL import Image
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import FileMetadata

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.wmv', '.flv'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def get_file_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    return 'unknown'


def get_dimensions(filepath):
    """Get width and height of image or video."""
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if ext in VIDEO_EXTENSIONS:
            # Use OpenCV for videos
            cap = cv2.VideoCapture(filepath)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return width, height
        else:
            # Use PIL for images
            with Image.open(filepath) as img:
                return img.width, img.height
    except Exception as e:
        print(f"   Warning: Could not get dimensions for {os.path.basename(filepath)}: {e}")
        return None, None


# Removed find_thumbnail - thumbnails are now constructed dynamically in the app


def main():
    parser = argparse.ArgumentParser(
        description='Scan images and thumbnails into database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan entire dataset
  python scan_to_db.py --dataset /media/user/DiskX/dataset

  # Scan only folder1
  python scan_to_db.py --dataset /media/user/DiskX/dataset --folder folder1

  # Scan subfolder
  python scan_to_db.py --dataset /media/user/DiskX/dataset --folder "corba/mercimek"

  # Force update existing records
  python scan_to_db.py --dataset /media/user/DiskX/dataset --folder folder1 --force
        """
    )
    parser.add_argument(
        '--dataset', '-d', 
        required=True, 
        help='Base dataset directory'
    )
    parser.add_argument(
        '--folder', '-f',
        help='Specific folder to scan (relative to dataset). If not provided, scans all.'
    )
    parser.add_argument(
        '--force',
        action='store_true', 
        help='Update existing records'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true', 
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    # Determine paths
    dataset_dir = os.path.abspath(args.dataset)
    
    if args.folder:
        scan_dir = os.path.join(dataset_dir, args.folder)
    else:
        scan_dir = dataset_dir
    
    if not os.path.exists(dataset_dir):
        print(f"❌ Dataset directory not found: {dataset_dir}")
        sys.exit(1)
    
    if not os.path.exists(scan_dir):
        print(f"❌ Folder not found: {scan_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("📂 Scanning to Database")
    print("=" * 60)
    print(f"Dataset:  {dataset_dir}")
    print(f"Scanning: {scan_dir}")
    print(f"Folder:   {args.folder or '(all)'}")
    print(f"Force:    {args.force}")
    print("=" * 60)
    
    # Find all media files
    print("\n🔍 Scanning for files...")
    all_files = []
    
    for root, dirs, files in os.walk(scan_dir):
        # Skip thumbnail directories
        dirs[:] = [d for d in dirs if d != 'thumbnails']
        
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                filepath = os.path.join(root, filename)
                # folder_path is relative to dataset_dir
                folder_path = os.path.relpath(root, dataset_dir)
                all_files.append({
                    'filepath': filepath,
                    'folder_path': folder_path,
                    'filename': filename,
                    'dir': root
                })
    
    print(f"   Found {len(all_files)} media files")
    
    if not all_files:
        print("   No files to process.")
        return
    
    if args.dry_run:
        print("\n[DRY RUN] Would process:")
        for f in all_files[:20]:
            print(f"   {f['folder_path']}/{f['filename']}")
        if len(all_files) > 20:
            print(f"   ... and {len(all_files) - 20} more")
        return
    
    # Create Flask app context
    app = create_app()
    
    # Get existing records for the folder being scanned
    print("\n📊 Checking existing records...")
    with app.app_context():
        if args.folder:
            # Only get records for this folder (and subfolders)
            existing = {}
            for fm in FileMetadata.query.filter(
                FileMetadata.folder_path.like(f"{args.folder}%")
            ).all():
                existing[(fm.folder_path, fm.filename)] = fm
        else:
            existing = {}
            for fm in FileMetadata.query.all():
                existing[(fm.folder_path, fm.filename)] = fm
        print(f"   Found {len(existing)} existing records")
    
    # Process files
    print(f"\n⚙️  Processing {len(all_files)} files...")
    print("-" * 60)
    
    added = 0
    updated = 0
    skipped = 0
    thumb_count = 0
    errors = 0
    
    with app.app_context():
        for i, f in enumerate(all_files, 1):
            try:
                filepath = f['filepath']
                folder_path = f['folder_path']
                filename = f['filename']
                
                key = (folder_path, filename)
                
                if key in existing:
                    if args.force:
                        # Update existing
                        fm = existing[key]
                        fm.file_size = os.path.getsize(filepath)
                        fm.file_type = get_file_type(filepath)
                        # Update dimensions
                        width, height = get_dimensions(filepath)
                        if width and height:
                            fm.width = width
                            fm.height = height
                        fm.modified_at = datetime.utcnow()
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Get dimensions
                    width, height = get_dimensions(filepath)
                    
                    # Create new record
                    fm = FileMetadata(
                        folder_path=folder_path,
                        filename=filename,
                        file_type=get_file_type(filepath),
                        file_size=os.path.getsize(filepath),
                        width=width,
                        height=height
                    )
                    db.session.add(fm)
                    added += 1
                
                # Progress display
                if i % 100 == 0 or i == len(all_files):
                    pct = (i / len(all_files)) * 100
                    print(f"   [{i}/{len(all_files)}] {pct:.1f}% - Added: {added}, Updated: {updated}, Skipped: {skipped}")
                
                # Commit in batches
                if i % 1000 == 0:
                    db.session.commit()
            
            except Exception as e:
                errors += 1
                print(f"   ✗ Error: {filename} - {e}")
        
        # Final commit
        db.session.commit()
    
    print("-" * 60)
    print("\n✅ Done!")
    print(f"   Added:        {added}")
    print(f"   Updated:      {updated}")
    print(f"   Skipped:      {skipped}")
    print(f"   Errors:       {errors}")
    print("=" * 60)


if __name__ == '__main__':
    main()
