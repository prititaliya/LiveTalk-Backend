-- Migration script to add email_verified column
-- Run this SQL script directly on your PostgreSQL database

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

