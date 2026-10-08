import unittest
from unittest.mock import patch

from storage_observability import parse_storage_metrics, storage_snapshot


EXPOSITION = """
SeaweedFS_build_info{version="4.48",commit="test"} 1
SeaweedFS_s3_bucket_object_count{bucket="imports"} 10
SeaweedFS_s3_bucket_size_bytes{bucket="imports"} 392680
SeaweedFS_s3_bucket_physical_size_bytes{bucket="imports"} 400000
SeaweedFS_s3_bucket_read_only{bucket="imports"} 0
SeaweedFS_volumeServer_resource{name="/data",type="all"} 1000000
SeaweedFS_volumeServer_resource{name="/data",type="avail"} 300000
SeaweedFS_volumeServer_resource{name="/data",type="used"} 700000
SeaweedFS_s3_request_total{bucket="imports",type="GET",code="200"} 16
SeaweedFS_s3_request_total{bucket="awards",type="GET",code="200"} 4
SeaweedFS_s3_request_total{bucket="",type="LIST",code="403"} 1
SeaweedFS_s3_in_flight_upload_count 2
SeaweedFS_s3_in_flight_upload_bytes 1024
"""


class StorageTests(unittest.TestCase):
    def test_native_metrics_keep_bucket_units_and_aggregate_request_labels(
        self,
    ):
        sample = parse_storage_metrics(EXPOSITION)
        self.assertEqual(sample["summary"]["objects"], 10)
        self.assertEqual(sample["summary"]["logicalBytes"], 392680)
        self.assertEqual(sample["volumes"][0]["availableBytes"], 300000)
        self.assertEqual(sample["buckets"][0]["readOnly"], False)
        self.assertEqual(
            sample["requests"][0],
            {"operation": "GET", "code": "200", "count": 20},
        )
        self.assertEqual(sample["summary"]["activeUploads"], 2)

    def test_missing_nonfinite_or_truncated_data_is_not_a_false_zero(self):
        sample = parse_storage_metrics(
            'SeaweedFS_s3_bucket_size_bytes{bucket="empty"} NaN'
        )
        self.assertIsNone(sample["summary"]["objects"])
        sample = parse_storage_metrics(
            EXPOSITION
            + '\nSeaweedFS_s3_bucket_size_bytes{bucket="awards"} 100',
            maximum=1,
        )
        self.assertTrue(sample["bucketsTruncated"])
        self.assertIsNone(sample["summary"]["objects"])

    def test_failed_provider_response_is_sanitized_and_unavailable(self):
        with patch(
            "storage_observability.urllib.request.urlopen",
            side_effect=OSError("credential-must-not-appear"),
        ):
            sample = storage_snapshot()
        self.assertEqual(sample["status"], "UNAVAILABLE")
        self.assertIsNone(sample["summary"]["logicalBytes"])
        self.assertNotIn("credential-must-not-appear", str(sample))
