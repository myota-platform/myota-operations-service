# MyOTA operations service

Operations exposes authenticated Grafana identity headers and samples bounded,
read-only PostgreSQL/PostGIS statistics for Prometheus. It does not read domain
tables or query text. SeaweedFS metrics are owned by the OpenTelemetry
Collector/Grafana path; Operations no longer polls SeaweedFS or stores its
sampled status history.

- `GET /v1/operations/observability-session` revalidates the live Identity
  session and returns the current per-account Grafana role. Global operators
  and administrators become Editors; other authorized readers remain Viewers.
- `/healthz` and `/metrics` expose internal service health and telemetry.
- PostgreSQL samples use catalog/statistics views and fixed database names;
  they never read application rows, query text, bind values, or geometry.

The sampled storage table is removed by the forward-only, idempotent migration
`migrations/003_retire_storage_snapshots.sql`. The original
`002_storage_snapshots.sql` remains unchanged for migration-history integrity.
Deploy and Platform mirror the drop as
`db/migrations/core/005_retire_storage_snapshots.sql`. Only
`operations_storage_snapshot` is dropped; PostgreSQL monitoring and unrelated
Operations data are unchanged.

PostgreSQL sampling is configured with `OPERATIONS_PG_POLL_SECONDS` and the
read-only monitor credentials for each database. Grafana identity resolution
uses `MYOTA_IDENTITY_URL` and the service's existing signing-key configuration.
SeaweedFS scrape configuration, dashboard, metric interpretation, and
application-storage boundaries are documented in the
[SeaweedFS monitoring guide](https://github.com/myota-platform/myota-docs/blob/main/docs/operations/storage/seaweedfs-admin-status.md).

Run the local stack from `myota-deploy`. The internal service port is 8005;
public access is through the API gateway. Quality checks use
`python3 -m unittest discover -s tests`; CI also runs Ruff formatting/lint and
publishes `ghcr.io/myota-platform/myota-operations-service:latest`.
