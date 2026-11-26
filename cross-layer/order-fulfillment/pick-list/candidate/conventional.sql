ALTER TABLE orders ADD COLUMN IF NOT EXISTS location text NOT NULL DEFAULT '',
                   ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 0,
                   ADD COLUMN IF NOT EXISTS warehouse_status text NOT NULL DEFAULT 'Pending',
                   ADD COLUMN IF NOT EXISTS held boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS pick_queue ON orders(location, priority DESC, id COLLATE "C") WHERE warehouse_status = 'Packed' AND NOT held;
CREATE INDEX IF NOT EXISTS pick_order_lines ON reservations(order_id, sku) INCLUDE (quantity);
CREATE OR REPLACE VIEW pick_orders AS SELECT id, location, priority, warehouse_status, held FROM orders;
CREATE OR REPLACE VIEW pick_lines AS SELECT order_id, sku, quantity FROM reservations;
