-- Add support for storing custom unit price per bill row.
ALTER TABLE bills
ADD COLUMN IF NOT EXISTS unit_rate INT;
