# Retired Operations service

This service has been removed from the MyOTA runtime. Deploy and its
synchronized Platform mirror no longer define an Operations Deployment,
Service, Compose workload, Gateway route, Grafana caller, or database sampler.
The repository's image publishing job is disabled; any existing registry image
is historical and must not be deployed.

Replacement ownership:

- The OpenTelemetry Collector receives bounded PostgreSQL metrics for the
  Core, Activity, and Geo databases using the existing least-privilege monitor
  roles. Query sampling and raw SQL collection remain disabled.
- The API Gateway resolves Grafana access through Identity's live
  `/v1/identity/me` role assignments. It maps global operators/admins to
  Editor and `observability.view` readers to Viewer.
- NATS broker monitoring belongs to NATS Surveyor and Grafana.

The old implementation and migration history remain as reference until the
repository archive operation is completed. Do not deploy or extend it. The
cross-repository evidence and archive status are tracked in
[myota-docs](https://github.com/myota-platform/myota-docs/blob/main/docs/observability/evidence/operations-service-retirement-2026-10-12.md).
