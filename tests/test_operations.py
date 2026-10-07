import asyncio
import time
import unittest
from unittest.mock import patch

from common import sign_token
from operations import authorize, broker_snapshot


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
