import pytest

from railway_lakehouse.silver.schema import NewsFeature

pytestmark = pytest.mark.integration


def _feature(article_id, summary, language):
    return NewsFeature(
        article_id=article_id,
        source="fixture",
        url=f"https://example.test/{article_id}",
        published_date="2026-06-25",
        language=language,
        is_rail_related=True,
        country="HU",
        event_type="investment",
        summary_en=summary,
    )


def test_real_sentence_transformers_embeddings_cluster_translated_story():
    pytest.importorskip("sentence_transformers")
    from railway_lakehouse.silver.news.embeddings import compute_embeddings, cluster_near_duplicates

    rows = [
        _feature("hu", "MAV announced a railway station renovation in Budapest.", "hu"),
        _feature("de", "MAV kundigte eine Renovierung eines Bahnhofs in Budapest an.", "de"),
        _feature("en", "MAV announced a railway station renovation in Budapest.", "en"),
    ]

    embedded = compute_embeddings(rows)
    clustered = cluster_near_duplicates(embedded, threshold=0.95)
    group_ids = {row.cross_lingual_dedup_id for row in clustered}

    assert all(row.text_embedding for row in clustered)
    assert len(group_ids) == 1
    assert sum(row.is_duplicate is True for row in clustered) == 2
