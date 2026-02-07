#!/usr/bin/env python3
"""
Clean up database by removing .thumbnails entries
Run this if .thumbnails folders appear in your gallery
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import FileMetadata

def main():
    print("=" * 60)
    print("🧹 Database Cleanup")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # Find all records with .thumbnails in path
        thumbnail_records = FileMetadata.query.filter(
            FileMetadata.folder_path.like('%.thumbnails%')
        ).all()
        
        print(f"\nFound {len(thumbnail_records)} records with '.thumbnails' in path")
        
        if thumbnail_records:
            print("\nSample records:")
            for record in thumbnail_records[:5]:
                print(f"  - {record.folder_path}/{record.filename}")
            
            if len(thumbnail_records) > 5:
                print(f"  ... and {len(thumbnail_records) - 5} more")
            
            confirm = input(f"\nDelete these {len(thumbnail_records)} records? (yes/no): ")
            
            if confirm.lower() == 'yes':
                for record in thumbnail_records:
                    db.session.delete(record)
                db.session.commit()
                print(f"\n✅ Deleted {len(thumbnail_records)} records")
            else:
                print("\n❌ Cancelled - no changes made")
        else:
            print("\n✅ No .thumbnails records found - database is clean!")
        
        # Show statistics
        total_records = FileMetadata.query.count()
        print(f"\nTotal records remaining: {total_records}")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
