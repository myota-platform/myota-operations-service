# MyOTA operations service

Domain-neutral operational visibility. Provides the authenticated admin UI with
real NATS/JetStream stream and consumer state and persistent sampled history.
It never processes business-domain queues or changes stream retention, messages,
consumer configuration, delivery cursors or acknowledgements.

- `GET /v1/operations/jetstream`: latest broker sample, timestamp and stale flag.
- `GET /v1/operations/jetstream/snapshots?page=1&pageSize=20`: paged history.
- `/healthz`, `/metrics`: internal health and OpenTelemetry-backed metrics.

Access requires an access token with GLOBAL_OPERATOR/GLOBAL_ADMIN,
`observability.view`, `operations.read` or wildcard permission. Broker credentials
and message payloads are never returned or stored. Sample failures are recorded
as unavailable, not a fictional zero backlog. History starts at deployment;
it is sampled status, not an exhaustive per-message delivery log.

`operations_jetstream_snapshot` is service-owned control-plane data in
`myota_core`. The service migration is synchronized to
`myota-deploy/db/migrations/core/002_operations.sql` and the platform mirror.
No direct database or NATS access is made by the browser. API instances are
stateless; a unique sample-slot constraint prevents duplicate history rows when
multiple samplers run. Connection concurrency is bounded to four per process.

Configuration: `CORE_DATABASE_URL`, `MYOTA_AUTH_SIGNING_KEY`, `NATS_URL`,
`OPERATIONS_POLL_SECONDS` (30 by default, minimum 10),
`OPERATIONS_HISTORY_DAYS` (7), `OPERATIONS_MAX_STREAMS` (20),
`MYOTA_JETSTREAM_METRICS_MAX_CONSUMERS` (100). Truncation is explicit in responses.
Configure the same interval on every replica. The broker account needs metadata
read permissions and stream-message inspection for age timestamps, not publish,
consumer-create, ACK, purge or delete permissions. Message content received during
an age lookup is discarded; it never enters snapshots.

Run the full local stack from `myota-deploy`. The admin page is `/jetstream`.
Production deployment and secrets are managed by the Helm/Fleet chart; the
internal service port is 8005 and public access is through the API gateway.

Quality: `./scripts/install-quality-hooks.sh` enables Ruff pre-commit/pre-push
checks; `python3 -m unittest discover -s tests` runs regressions. The image
workflow runs tests, formatting and lint before publishing
`ghcr.io/myota-platform/myota-operations-service:latest`.
