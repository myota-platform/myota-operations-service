import asyncio
import http.client
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from common import sign_token
from operations import (
    OperationsHandler,
    authorize,
    broker_snapshot,
    grafana_identity,
    current_identity,
)


class ProxyHeaderTests(unittest.TestCase):
    def test_trusted_headers_follow_account_role_and_denial_has_no_identity(
        self,
    ):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OperationsHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            account = {
                "id": "person-1",
                "displayName": "Operator",
                "email": "operator@example.test",
            }
            cases = (
                ({**account, "roles": ["GLOBAL_OPERATOR"]}, 200, "Editor"),
                ({**account, "scopes": ["operations.read"]}, 200, "Viewer"),
                ({**account, "roles": ["PARTICIPANT"]}, 403, None),
            )
            for identity, status, role in cases:
                with patch(
                    "operations.current_identity", return_value=identity
                ):
                    client = http.client.HTTPConnection(
                        "127.0.0.1", server.server_port, timeout=2
                    )
                    client.request(
                        "GET",
                        "/v1/operations/observability-session",
                        headers={"X-WEBAUTH-ROLE": "Admin"},
                    )
                    response = client.getresponse()
                    self.assertEqual(response.status, status)
                    self.assertEqual(
                        response.getheader("X-MyOTA-Grafana-Role"), role
                    )
                    self.assertEqual(
                        response.getheader("Cache-Control"), "no-store"
                    )
                    response.read()
                    client.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            "os.environ", {"MYOTA_AUTH_SIGNING_KEY": "test-only-key"}
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def params(self, claims, token_type="access"):
        return {
            "Authorization": "Bearer "
            + sign_token(
                {"sub": "test-admin", "exp": int(time.time()) + 60, **claims},
                token_type,
            )
        }

    def test_global_admin_and_explicit_observability_scope(self):
        authorize(self.params({"roles": [{"role": "GLOBAL_ADMIN"}]}))
        authorize(self.params({"scp": ["observability.view"]}))

    def test_anonymous_ordinary_member_and_refresh_token_denied(self):
        for params in (
            {},
            self.params({"roles": [{"role": "PARTICIPANT"}]}),
            self.params({"scp": ["*"]}, "refresh"),
        ):
            with self.assertRaises(PermissionError):
                authorize(params)

    def test_grafana_editing_uses_current_operator_role_not_wildcard_scope(
        self,
    ):
        account = {
            "id": "person-1",
            "displayName": "Operator",
            "email": "operator@example.test",
        }
        self.assertEqual(
            grafana_identity(
                {**account, "roles": [{"role": "GLOBAL_OPERATOR"}]}
            )["role"],
            "Editor",
        )
        self.assertEqual(
            grafana_identity({**account, "roles": ["GLOBAL_ADMIN"]})["role"],
            "Editor",
        )
        viewer = grafana_identity({**account, "scopes": ["*"]})
        self.assertEqual(viewer["role"], "Viewer")
        self.assertEqual(viewer["username"], "myota:person-1")
        with self.assertRaises(PermissionError):
            grafana_identity({**account, "roles": ["PARTICIPANT"]})

    def test_observability_session_rechecks_revoked_identity(self):
        import urllib.error

        params = self.params({"roles": ["GLOBAL_OPERATOR"]})
        error = urllib.error.HTTPError(
            "http://identity/me", 403, "revoked", {}, None
        )
        with patch("operations.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(PermissionError):
                current_identity(params)


class BrokerTests(unittest.TestCase):
    def test_real_broker_fields_and_unknown_oldest_age(self):
        class JS:
            async def streams_info(self):
                return [
                    {
                        "config": {"name": "EVENTS", "subjects": ["myota.>"]},
                        "state": {
                            "messages": 12,
                            "bytes": 512,
                            "consumer_count": 1,
                        },
                    }
                ]

            async def consumers_info(self, stream):
                return [
                    {
                        "name": "preprocess",
                        "num_pending": 4,
                        "num_ack_pending": 1,
                        "num_redelivered": 2,
                        "config": {
                            "filter_subject": "myota.import.>",
                            "durable_name": "preprocess",
                        },
                    }
                ]

        class NC:
            def jetstream(self):
                return JS()

            async def request(self, *_args, **_kwargs):
                raise RuntimeError("message is no longer retained")

        result = asyncio.run(broker_snapshot(NC()))
        consumer = result["streams"][0]["consumers"][0]
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(consumer["pending"], 4)
        self.assertEqual(consumer["ackPending"], 1)
        self.assertEqual(consumer["redelivered"], 2)
        self.assertIsNone(consumer["oldestMessageAgeSeconds"])
        self.assertNotIn("credentials", result)
        self.assertNotIn("payload", consumer)

    def test_partial_inspection_is_not_reported_healthy(self):
        class JS:
            async def streams_info(self):
                return [{"config": {"name": "EVENTS"}}]

            async def consumers_info(self, stream):
                raise RuntimeError("broker unavailable")

        class NC:
            def jetstream(self):
                return JS()

        result = asyncio.run(broker_snapshot(NC()))
        self.assertEqual(result["status"], "PARTIAL")
        self.assertTrue(result["errors"])
