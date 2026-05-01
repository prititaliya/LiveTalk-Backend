#!/bin/bash
# Script to run the email_verified column migration
# This script extracts database credentials and runs the SQL migration

cd "$(dirname "$0")/.."

# Load database URL from .env.local if it exists
if [ -f .env.local ]; then
    DATABASE_URL=$(grep "^DATABASE_URL=" .env.local | cut -d'=' -f2- | head -1)
else
    DATABASE_URL="postgresql://postgres:postgres@localhost:5432/livetalk"
fi

# Parse database URL
# Format: postgresql://user:password@host:port/database?params
# Remove query parameters for parsing
DB_URL_CLEAN=$(echo "$DATABASE_URL" | sed 's/?.*$//')
DB_URL_REGEX="postgresql://([^:]+):([^@]+)@([^:/]+)(:([^/]+))?/(.+)"
if [[ $DB_URL_CLEAN =~ $DB_URL_REGEX ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASS="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[5]:-5432}"  # Default to 5432 if not specified
    DB_NAME="${BASH_REMATCH[6]}"
    # Remove any query parameters from DB_NAME
    DB_NAME=$(echo "$DB_NAME" | sed 's/?.*$//')
else
    echo "Error: Could not parse DATABASE_URL: $DATABASE_URL"
    exit 1
fi

echo "Running migration to add email_verified column..."
echo "Database: $DB_NAME on $DB_HOST:$DB_PORT"

# Export password for psql
export PGPASSWORD="$DB_PASS"

# Run the SQL migration
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Add the email_verified column (if it doesn't exist)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL;

-- Grandfather existing users (set them all to verified)
UPDATE users 
SET email_verified = TRUE 
WHERE email_verified = FALSE;

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'email_verified';
EOF

MIGRATION_RESULT=$?

# Unset password
unset PGPASSWORD

if [ $MIGRATION_RESULT -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo "The email_verified column has been added and existing users have been marked as verified."
else
    echo ""
    echo "❌ Migration failed. Please check the error messages above."
    exit 1
fi

