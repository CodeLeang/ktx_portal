-- Add optional avatar URL support for student profiles.
-- Run:
--   psql -h localhost -p 5433 -U postgres -d ktx_portal -f backend/migrations/add_avatar_url.sql

ALTER TABLE students
    ADD COLUMN IF NOT EXISTS avatar_url TEXT;
