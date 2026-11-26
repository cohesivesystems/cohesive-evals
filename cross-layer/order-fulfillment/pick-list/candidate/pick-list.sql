SELECT o.id, o.priority
FROM pick_orders o
WHERE o.location = $1 AND o.warehouse_status = 'Packed' AND NOT o.held
  AND (SELECT bool_and(d.units <= coalesce(s.units, 0))
       FROM (SELECT r.sku, sum(r.quantity) AS units
             FROM pick_lines r WHERE r.order_id = o.id GROUP BY r.sku) d
       LEFT JOIN pick_stock s ON s.location = o.location AND s.sku = d.sku)
ORDER BY o.priority DESC, o.id COLLATE "C"
LIMIT 50
