# Qualification results

| Orders | Run | Condition | GET p99 ms | Visibility p99 ms | DB CPU ms/write | App CPU ms/write | Buffer hits/write | Reads/write |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 100,000 | 1 | conventional | 6.2 | 5.0 | 11.95 | 3.81 | 1427.2 | 0.00 |
| 100,000 | 1 | cohesive | 5.9 | 4.8 | 12.09 | 4.00 | 1432.2 | 0.00 |
| 100,000 | 2 | conventional | 5.9 | 4.9 | 11.94 | 3.71 | 1427.2 | 0.00 |
| 100,000 | 2 | cohesive | 6.1 | 4.8 | 11.70 | 4.07 | 1431.2 | 0.00 |
| 100,000 | 3 | conventional | 6.0 | 4.9 | 12.08 | 3.77 | 1427.5 | 0.00 |
| 100,000 | 3 | cohesive | 6.2 | 5.0 | 12.45 | 4.05 | 1431.1 | 0.00 |
| 1,000,000 | 1 | conventional | 5.5 | 4.8 | 11.84 | 3.30 | 1427.4 | 0.00 |
| 1,000,000 | 1 | cohesive | 5.8 | 4.8 | 11.89 | 3.68 | 1431.3 | 0.00 |
| 1,000,000 | 2 | conventional | 5.3 | 4.7 | 11.57 | 3.23 | 1427.4 | 0.00 |
| 1,000,000 | 2 | cohesive | 5.5 | 4.8 | 11.62 | 3.48 | 1432.4 | 0.00 |
| 1,000,000 | 3 | conventional | 5.3 | 4.7 | 11.50 | 3.28 | 1427.2 | 0.00 |
| 1,000,000 | 3 | cohesive | 5.3 | 4.7 | 11.51 | 3.39 | 1432.5 | 0.00 |

Conventional, 1M / 100k median work per write: DB CPU 0.97×, total buffer accesses 1.00×, app CPU 0.87×.

Cohesive, 1M / 100k median work per write: DB CPU 0.96×, total buffer accesses 1.00×, app CPU 0.86×.


All twelve runs passed the frozen acceptance thresholds. Each issued 6,000 source writes and 19,200 foreground reads. Visibility probes were additional traffic. Initial pages, adverse fixtures and replay of a hold committed during host downtime matched the oracle. The raw-evidence audit reproduced the p99s from the captured samples.

Conventional: 0 visibility samples over two seconds; maximum final convergence 54.5 ms. End-of-run anonymous app RSS ranged from 26 to 29 MiB.
Cohesive: 0 visibility samples over two seconds; maximum final convergence 63.3 ms. End-of-run anonymous app RSS ranged from 40 to 46 MiB.

See the per-run evidence directories for request and commit scheduling lag, setup and seed times, buffer and CPU measurements, deployment limits, PostgreSQL settings, EXPLAIN ANALYZE and compressed raw events. The 3,200 active orders and their reservation lines stay fixed in both snapshots. Added history has no reservation lines. The ratios describe this fixture and host only.
