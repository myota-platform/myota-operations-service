# MyOTA operations service

Domain-neutral operational visibility. Provides the authenticated admin UI with
real NATS/JetStream stream and consumer state and persistent sampled history.
It also samples SeaweedFS S3 health and native exporter bucket, filesystem,
request and upload gauges. `/object-storage` in the Admin UI displays these
samples and persistent history; unknown measurements remain null.
It never processes business-domain queues or changes stream retention, messages,
consumer configuration, delivery cursors or acknowledgements.

- `GET /v1/operations/jetstream`: latest broker sample, timestamp and stale flag.
- `GET /v1/operations/jetstream/snapshots?page=1&pageSize=20`: paged history.
- `GET /v1/operations/object-storage`: latest SeaweedFS sample and stale flag.
- `GET /v1/operations/object-storage/snapshots`: paged storage history.
- `GET /v1/operations/observability-session`: validates the live identity
  session and returns a per-account Grafana identity with trusted proxy headers.
  GLOBAL_OPERATOR/GLOBAL_ADMIN become Editor; other authorized readers remain
  Viewer. Wildcard permission alone does not grant Grafana editing.
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
`operations_storage_snapshot` is separately owned in `myota_core`; migration
`002_storage_snapshots.sql` is synchronized to platform/deploy core migration
`003_storage_snapshots.sql`. Numbered migrations are discovered automatically.

Configuration: `CORE_DATABASE_URL`, `MYOTA_AUTH_SIGNING_KEY`, `NATS_URL`,
`OPERATIONS_POLL_SECONDS` (30 by default, minimum 10),
`OPERATIONS_HISTORY_DAYS` (7), `OPERATIONS_MAX_STREAMS` (20),
`MYOTA_JETSTREAM_METRICS_MAX_CONSUMERS` (100). Truncation is explicit in responses.
Configure the same interval on every replica. The broker account needs metadata
read permissions and stream-message inspection for age timestamps, not publish,
consumer-create, ACK, purge or delete permissions. Message content received during
an age lookup is discarded; it never enters snapshots.

Storage configuration: `OPERATIONS_STORAGE_HEALTH_URL` (S3 `/status`),
`OPERATIONS_STORAGE_METRICS_URL` (private SeaweedFS `/metrics`),
`OPERATIONS_MAX_BUCKETS` (100), and `MYOTA_IDENTITY_URL`. Storage sampling
uses two read-only HTTP requests, each with a five-second timeout. Exporter
responses are capped at 2 MiB. Only reported bucket gauges are included;
empty/inactive buckets may be absent. Filesystem capacity may be shared host
capacity rather than PVC quota. No S3 credentials, object keys, contents or
raw exporter text are stored. Storage failures log a sanitized exception class.
The service exports sample-health/freshness metrics through its existing OTel
metrics path. See the [storage page guide](https://github.com/myota-platform/myota-docs/blob/main/docs/seaweedfs-admin-status.md).

Run the full local stack from `myota-deploy`. The admin page is `/jetstream`.
Production deployment and secrets are managed by the Helm/Fleet chart; the
internal service port is 8005 and public access is through the API gateway.

Quality: `./scripts/install-quality-hooks.sh` enables Ruff pre-commit/pre-push
checks; `python3 -m unittest discover -s tests` runs regressions. The image
workflow runs tests, formatting and lint before publishing
`ghcr.io/myota-platform/myota-operations-service:latest`.

The [status API/UI guide](https://github.com/myota-platform/myota-docs/blob/main/docs/jetstream-admin-status.md)
documents sample semantics, permissions, deployment and alerts. The
[geodata scaling delivery record](https://github.com/myota-platform/myota-docs/blob/main/docs/geodata-horizontal-scaling-roadmap.md#latest-delivery-and-evidence--7-october-2026)
links the integration evidence and remaining qualification gates. Preprocessing,
promotion and deletion consumers remain geodata-owned; operational visibility
does not make this service a shared business-queue executor.
