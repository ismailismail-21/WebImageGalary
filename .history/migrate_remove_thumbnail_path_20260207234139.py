#!/usr/bin/env python3
"""
Database migration: Remove thumbnail_path column from file_metadata table
Run this ONCE to clean up the schema
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def main():
    print("=" * 60)
    print("🔄 Database Migration: Remove thumbnail_path column")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column exists
            result = db.engine.execute(
                "PRAGMA table_info(file_metadata);"
            ).fetchall()
            
            columns = [row[1] for row in result]
            
            if 'thumbnail_path' not in columns:
                print("\n✅ Column 'thumbnail_path' does not exist - already migrated!")
                return
            
            print(f"\n📋 Current columns: {', '.join(columns)}")
            print("\n⚠️  This will remove the 'thumbnail_path' column permanently.")
            confirm = input("Continue? (yes/no): ")
            
            if confirm.lower() != 'yes':
                print("\n❌ Migration cancelled")
                return
            
            print("\n🔧 Migrating...")
            
            # SQLite doesn't support DROP COLUMN, so we need to recreate the table
            db.engine.execute("""
                CREATE TABLE file_metadata_new (
                    id INTEGER PRIMARY KEY,
                    folder_path VARCHAR(500) NOT NULL,
                    filename VARCHAR(500) NOT NULL,
                    file_type VARCHAR(10) NOT NULL,
                    file_size INTEGER NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    duration FLOAT,
                    fps FLOAT,
                    created_at TIMESTAMP,
                    modified_at TIMESTAMP
                );
            """)
            
            # Copy data
            db.engine.execute("""
                INSERT INTO file_metadata_new 
                    (id, folder_path, filename, file_type, file_size, width, height, 
                     duration, fps, created_at, modified_at)
                SELECT 
                    id, folder_path, filename, file_type, file_size, width, height,
                    duration, fps, created_at, modified_at
                FROM file_metadata;
            """)
            
            # Drop old table
            db.engine.execute("DROP TABLE file_metadata;")
            
            # Rename new table
            db.engine.execute("ALTER TABLE file_metadata_new RENAME TO file_metadata;")
            
            # Recreate indexes
            db.engine.execute("""
                CREATE INDEX idx_folder_filename ON file_metadata(folder_path, filename);
            """)
            db.engine.execute("""
                CREATE INDEX idx_folder_modified ON file_metadata(folder_path, modified_at);
            """)
            db.engine.execute("""
                CREATE INDEX idx_file_type ON file_metadata(file_type);
            """)
            db.engine.execute("""
                CREATE INDEX idx_modified_at ON file_metadata(modified_at);
            """)
            db.engine.execute("""
                CREATE INDEX ix_file_metadata_folder_path ON file_metadata(folder_path);
            """)
            db.engine.execute("""
                CREATE INDEX ix_file_metadata_filename ON file_metadata(filename);
            """)
            
            print("\n✅ Migration complete!")
            print("   - Removed 'thumbnail_path' column")
            print("   - Preserved all data")
            print("   - Recreated indexes")
            
            # Verify
            result = db.engine.execute(
                "PRAGMA table_info(file_metadata);"
            ).fetchall()
            new_columns = [row[1] for row in result]
            print(f"\n📋 New columns: {', '.join(new_columns)}")
            
            total_records = db.engine.execute(
                "SELECT COUNT(*) FROM file_metadata"
            ).fetchone()[0]
            print(f"📊 Total records: {total_records}")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)

if __name__ == '__main__':
    main()
