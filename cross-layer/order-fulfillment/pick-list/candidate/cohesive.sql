CREATE INDEX IF NOT EXISTS pick_queue ON cohesive_orders(location, priority DESC, order_id COLLATE "C")
    WHERE partition_key = 'local' AND warehouse_status = 'Packed' AND NOT held;
CREATE INDEX IF NOT EXISTS pick_order_lines ON cohesive_reservations(order_id, sku) INCLUDE (quantity)
    WHERE partition_key = 'local';
CREATE OR REPLACE VIEW pick_orders AS SELECT order_id AS id, location, priority, warehouse_status, held
    FROM cohesive_orders WHERE partition_key = 'local';
CREATE OR REPLACE VIEW pick_lines AS SELECT order_id, sku, quantity FROM cohesive_reservations WHERE partition_key = 'local';
