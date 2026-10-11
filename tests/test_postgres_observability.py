from __future__ import annotations

from postgres_observability import DatabaseSample, sample_once
from metrics import METRICS


def test_postgres_sample_uses_bounded_metrics_and_sets_unavailable(
    monkeypatch,
):
    sample = DatabaseSample(3, 100, 4096, 11, 2, 17, 0, "3.4.2")

    def fake_sample(database, host_env, default_host, dbname):
        if database == "activity":
            raise OSError("redacted connection failure")
        return sample

    monkeypatch.setattr("postgres_observability._sample", fake_sample)
    sample_once()
    output = METRICS.render()

    assert 'myota_postgresql_up{database="core"} 1' in output
    assert 'myota_postgresql_up{database="activity"} 0' in output
    assert 'myota_postgresql_commits_total{database="geo"} 11' in output
    assert (
        'myota_postgis_extension_present{database="geo",version="3.4.2"} 1'
        in output
    )
    assert "redacted connection failure" not in output
    assert "query" not in output.lower()
