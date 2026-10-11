# MyOTA operations service

Domain-neutral operational visibility. The service samples SeaweedFS S3 health
and native exporter bucket, filesystem, request, and upload gauges.
`/object-storage` in the Admin UI displays the latest sample and its bounded
history; unavailable measurements remain unknown rather than becoming zero.

The service also validates the signed-in identity for authenticated Grafana
access and returns trusted proxy identity headers. It does not connect to NATS,
inspect broker state, or process business queues.

- `GET /v1/operations/object-storage`: latest SeaweedFS sample and stale flag.
- `GET /v1/operations/object-storage/snapshots`: paged storage history.
- `GET /v1/operations/observability-session`: validates the live identity
  session and returns a per-account Grafana identity. Global operators and
  administrators become Editors; other authorized readers remain Viewers.
- `/healthz`, `/metrics`: internal health and OpenTelemetry metrics.

Access requires an access token with GLOBAL_OPERATOR/GLOBAL_ADMIN,
`observability.view`, `operations.read`, or wildcard permission. Only
authorized readers can use the observation API. Sample failures are recorded
as unavailable. Storage history begins at deployment and is sampled status, not
an exhaustive object or request log.

`operations_storage_snapshot` is service-owned control-plane data in
`myota_core`. Migration `002_storage_snapshots.sql` is synchronized to
Deploy/Platform core migration `003_storage_snapshots.sql`; numbered
migrations are discovered automatically. Migration
`003_retire_jetstream_snapshots.sql` retires the former NATS history table and
is mirrored as core migration `005_retire_jetstream_snapshots.sql`. The verified
pre-cutover backup is retained outside source control. API instances are
stateless and the database pool is bounded.

Configuration: `CORE_DATABASE_URL`, `MYOTA_AUTH_SIGNING_KEY`,
`OPERATIONS_POLL_SECONDS` (30 seconds by default, minimum 10),
`OPERATIONS_HISTORY_DAYS` (7), `OPERATIONS_STORAGE_HEALTH_URL` (S3
`/status`), `OPERATIONS_STORAGE_METRICS_URL` (private SeaweedFS
`/metrics`), `OPERATIONS_MAX_BUCKETS` (100), and
`MYOTA_IDENTITY_URL`. Storage sampling uses two read-only HTTP requests with
five-second timeouts. Exporter responses are capped at 2 MiB. No S3 credentials,
object keys, contents, or raw exporter text are stored.

Run the full local stack from `myota-deploy`. Production deployment and
secrets are managed by the Helm/Fleet chart; the internal service port is 8005
and public access is through the API gateway.

Quality: `./scripts/install-quality-hooks.sh` enables Ruff pre-commit and
pre-push checks; `python3 -m unittest discover -s tests` runs regressions.
The image workflow runs tests, formatting, and lint before publishing
`ghcr.io/myota-platform/myota-operations-service:latest`.

The [SeaweedFS status guide](https://github.com/myota-platform/myota-docs/blob/main/docs/operations/storage/seaweedfs-admin-status.md)
documents storage sample semantics and deployment.
