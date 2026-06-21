import pytest


pytestmark = pytest.mark.integration


@pytest.mark.xfail(
    strict=True,
    reason="GAP-004: pipeline Bronze storage reads are not wired",
)
def test_pipeline_storage_read_stubs_are_not_wired():
    import railway_lakehouse.pipeline as pipeline

    pipeline._read_bronze_eurostat(object())
