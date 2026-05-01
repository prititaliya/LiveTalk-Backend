"""
Migration script to add email_verified column and grandfather existing users

Run this script once after adding the email_verified column to the database.
This will set email_verified=True for all existing users.

Usage:
    python -m scripts.migrate_add_email_verified
    OR
    cd Backend && python scripts/migrate_add_email_verified.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Change to backend directory to ensure imports work
os.chdir(backend_dir)

from sqlalchemy import text
from infrastructure.database.database import SessionLocal, engine

def migrate():
    """Add email_verified column and set existing users to verified"""
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='email_verified'
        """))
        
        if result.fetchone() is None:
            # Add column with default False
            print("Adding email_verified column to users table...")
            db.execute(text("""
                ALTER TABLE users 
                ADD COLUMN email_verified BOOLEAN DEFAULT FALSE NOT NULL
            """))
            db.commit()
            print("Column added successfully.")
        else:
            print("email_verified column already exists.")
        
        # Update all existing users to verified (grandfathering)
        print("Setting email_verified=True for all existing users...")
        result = db.execute(text("""
            UPDATE users 
            SET email_verified = TRUE 
            WHERE email_verified = FALSE
        """))
        db.commit()
        count = result.rowcount
        print(f"Updated {count} users to verified status.")
        
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Running migration to add email_verified column...")
    migrate()
    print("Migration completed successfully!")

