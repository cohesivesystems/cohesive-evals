-- Existing Step 0 database, before starting the Step 1 host.
ALTER TABLE public.cohesive_orders
    ADD COLUMN IF NOT EXISTS released integer NOT NULL DEFAULT 0;
