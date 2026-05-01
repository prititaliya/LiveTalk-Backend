# Utility Scripts

This directory contains utility scripts for managing and maintaining the LiveTalk backend.

## Available Scripts

### manage_users.py

User management utility for the database.

**Usage:**
```bash
# List all users
python scripts/manage_users.py list

# Check if an email exists
python scripts/manage_users.py check user@example.com

# Check if a username exists
python scripts/manage_users.py check --username myusername

# Clear all users (with confirmation)
python scripts/manage_users.py clear
```

**Requirements:**
- PostgreSQL database must be running
- `DATABASE_URL` must be set in `Backend/.env.local`

