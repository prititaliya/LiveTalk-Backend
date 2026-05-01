"""
User Management Utility

Script to check, list, and manage users in the database.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Try to load .env.local, but don't fail if it doesn't exist
try:
    load_dotenv(".env.local")
except:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    print("   Make sure you have DATABASE_URL set in your .env.local file")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def list_users():
    """List all users in the database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, email, username, created_at FROM users ORDER BY created_at DESC"))
            users = result.fetchall()
            
            if not users:
                print("✅ No users found in database")
                return 0
            else:
                print(f"\nFound {len(users)} user(s):\n")
                for i, user in enumerate(users, 1):
                    print(f"{i}. ID: {user[0]}")
                    print(f"   Email: {user[1]}")
                    print(f"   Username: {user[2]}")
                    print(f"   Created: {user[3]}")
                    print()
                return len(users)
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        engine.dispose()

def check_user(email: str = None, username: str = None):
    """Check if a specific email or username exists"""
    try:
        with engine.connect() as conn:
            if email:
                result = conn.execute(
                    text("SELECT id, email, username FROM users WHERE LOWER(email) = LOWER(:email)"),
                    {"email": email}
                )
                user = result.fetchone()
                if user:
                    print(f"✅ Found user with email '{email}':")
                    print(f"   ID: {user[0]}")
                    print(f"   Email: {user[1]}")
                    print(f"   Username: {user[2]}")
                    return True
                else:
                    print(f"❌ No user found with email '{email}'")
                    return False
            
            if username:
                result = conn.execute(
                    text("SELECT id, email, username FROM users WHERE username = :username"),
                    {"username": username}
                )
                user = result.fetchone()
                if user:
                    print(f"✅ Found user with username '{username}':")
                    print(f"   ID: {user[0]}")
                    print(f"   Email: {user[1]}")
                    print(f"   Username: {user[2]}")
                    return True
                else:
                    print(f"❌ No user found with username '{username}'")
                    return False
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        engine.dispose()

def clear_users():
    """Clear all users from the database (use with caution!)"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            
            if count == 0:
                print("✅ No users to delete")
                return 0
            
            confirm = input(f"\n⚠️  Are you sure you want to delete {count} user(s)? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Cancelled")
                return 1
            
            result = conn.execute(text("DELETE FROM users"))
            conn.commit()
            print(f"✅ Deleted {result.rowcount} user(s)")
            return 0
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        engine.dispose()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_users.py list          - List all users")
        print("  python manage_users.py check <email> - Check if email exists")
        print("  python manage_users.py check --username <username> - Check if username exists")
        print("  python manage_users.py clear         - Clear all users (with confirmation)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        sys.exit(list_users())
    elif command == "check":
        if len(sys.argv) < 3:
            print("❌ Please provide email or use --username <username>")
            sys.exit(1)
        
        if sys.argv[2] == "--username" and len(sys.argv) >= 4:
            username = sys.argv[3]
            sys.exit(0 if check_user(username=username) else 1)
        else:
            email = sys.argv[2]
            sys.exit(0 if check_user(email=email) else 1)
    elif command == "clear":
        sys.exit(clear_users())
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()

