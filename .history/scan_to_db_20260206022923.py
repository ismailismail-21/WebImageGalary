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


def find_thumbnail(file_dir, filename):
    """Find thumbnail in the same folder's 'thumbnails' subfolder."""
    name_no_ext = os.path.splitext(filename)[0]
    thumb_dir = os.path.join(file_dir, 'thumbnails')
    
    # Check for .jpg thumbnail
    jpg_thumb = os.path.join(thumb_dir, f"{name_no_ext}.jpg")
    if os.path.exists(jpg_thumb):
        return jpg_thumb
    
    # Check for .webp thumbnail (for GIFs)
    webp_thumb = os.path.join(thumb_dir, f"{name_no_ext}.webp")
    if os.path.exists(webp_thumb):
        return webp_thumb
    
    return None


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
    
    # Count files with thumbnails
    with_thumb = sum(1 for f in all_files if find_thumbnail(f['dir'], f['filename']))
    print(f"   With thumbnails: {with_thumb}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would process:")
        for f in all_files[:20]:
            thumb = "✓" if find_thumbnail(f['dir'], f['filename']) else "✗"
            print(f"   [{thumb}] {f['folder_path']}/{f['filename']}")
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
                
                # Find thumbnail
                thumb_path = find_thumbnail(f['dir'], filename)
                if thumb_path:
                    thumb_count += 1
                
                key = (folder_path, filename)
                
                if key in existing:
                    if args.force:
                        # Update existing
                        fm = existing[key]
                        fm.thumbnail_path = thumb_path
                        fm.file_size = os.path.getsize(filepath)
                        fm.file_type = get_file_type(filepath)
                        fm.modified_at = datetime.utcnow()
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Create new record
                    fm = FileMetadata(
                        folder_path=folder_path,
                        filename=filename,
                        file_type=get_file_type(filepath),
                        file_size=os.path.getsize(filepath),
                        thumbnail_path=thumb_path
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
    print(f"   With thumbs:  {thumb_count}")
    print(f"   Errors:       {errors}")
    print("=" * 60)


if __name__ == '__main__':
    main()
