## Provisioning and persistence

Use `seed.schema.json` for the active application. Its versioned `$id` identifies
the setup format; no version field is added to the existing seed payload. The
`orders`, `inventory` and `reservations` arrays remain required. IDs must be unique
within each resource; reservation order/SKU references must exist. Reservations
have positive quantities. Setup rejects invalid data; failed setup requires a
fresh dedicated database. There is no public setup/reset endpoint.

{seed_defaults}

Setup may create multiple reservations per order for read-only projection and
boundary fixtures, including arbitrary nonblank reservation IDs. This does not
relax the one-workflow-created-reservation rule. Such seed data is distinct from
reachable invariant histories. No requirement ties a seeded lifecycle state to a
reservation; use public commands when checking reachable histories.

Optional persistence verification: finish all operations, record public business
views, stop the host cleanly, and start the same application on the same database
without reseeding. Order status, inventory settings and reservation facts{review_persistence} must
survive. Check new commands with fresh request IDs afterward. Admission
and result history remain host-lifetime only; recovery of pending work, durable
request replay and live schema migration are not required.
