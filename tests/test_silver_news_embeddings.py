import sys
import types

import numpy as np
import pytest

from railway_lakehouse.silver.schema import NewsFeature

pytestmark = pytest.mark.unit


class _FakeModel:
    def __init__(self, vector=None):
        self.vector = vector or [0.1] * 768
        self.calls = []

    def encode(self, text, **kwargs):
        self.calls.append((text, kwargs))
        return np.array(self.vector, dtype=np.float32)


def _feature(article_id, *, summary="Rail investment was announced.", embedding=None):
    return NewsFeature(
        article_id=article_id,
        source="rss",
        url=f"https://example.test/{article_id}",
        published_date="2026-06-25",
        language="en",
        is_rail_related=True,
        country="HU",
        event_type="investment",
        summary_en=summary,
        text_embedding=embedding,
    )


def test_load_embedding_model_caches_and_reuses(monkeypatch):
    from railway_lakehouse.silver.news import embeddings

    embeddings.load_embedding_model.cache_clear()
    created = []

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name
            created.append(model_name)

    fake_module = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    first = embeddings.load_embedding_model("fake/model")
    second = embeddings.load_embedding_model("fake/model")

    assert first is second
    assert created == ["fake/model"]
    embeddings.load_embedding_model.cache_clear()


def test_embed_text_returns_float_list_and_uses_passage_prefix():
    from railway_lakehouse.silver.news.embeddings import embed_text

    model = _FakeModel()

    result = embed_text("rail investment", model)

    assert isinstance(result, list)
    assert len(result) == 768
    assert all(isinstance(value, float) for value in result)
    encoded_text, kwargs = model.calls[0]
    assert encoded_text == "passage: rail investment"
    assert kwargs["normalize_embeddings"] is True


def test_embed_text_handles_none_and_empty():
    from railway_lakehouse.silver.news.embeddings import embed_text

    model = _FakeModel()

    assert embed_text(None, model) is None
    assert embed_text("", model) is None
    assert model.calls == []


def test_compute_embeddings_skips_already_embedded(monkeypatch):
    from railway_lakehouse.silver.news import embeddings

    row = _feature("a1", embedding=[0.2] * 768)
    monkeypatch.setattr(
        embeddings,
        "load_embedding_model",
        lambda model_name=embeddings.DEFAULT_EMBEDDING_MODEL: pytest.fail("model should not load"),
    )

    result = embeddings.compute_embeddings([row])

    assert result[0].text_embedding == [0.2] * 768


def test_compute_embeddings_use_model_false_skips_model(monkeypatch):
    from railway_lakehouse.silver.news import embeddings

    row = _feature("a1", embedding=None)
    monkeypatch.setattr(
        embeddings,
        "load_embedding_model",
        lambda model_name=embeddings.DEFAULT_EMBEDDING_MODEL: pytest.fail("model should not load"),
    )

    result = embeddings.compute_embeddings([row], use_model=False)

    assert result == [row]
    assert result[0].text_embedding is None


def test_compute_embeddings_populates_dataclass_and_dict(monkeypatch):
    from railway_lakehouse.silver.news import embeddings

    model = _FakeModel([0.3] * 768)
    monkeypatch.setattr(embeddings, "load_embedding_model", lambda model_name=embeddings.DEFAULT_EMBEDDING_MODEL: model)
    dataclass_row = _feature("a1")
    dict_row = {
        "article_id": "a2",
        "summary_en": "Rail services were disrupted.",
        "text_embedding": None,
    }

    result = embeddings.compute_embeddings([dataclass_row, dict_row])

    assert result[0].text_embedding == pytest.approx([0.3] * 768)
    assert result[0].text_embedding_model == embeddings.DEFAULT_EMBEDDING_MODEL
    assert result[1]["text_embedding"] == pytest.approx([0.3] * 768)
    assert result[1]["text_embedding_model"] == embeddings.DEFAULT_EMBEDDING_MODEL


def test_compute_embeddings_skips_one_failed_row(monkeypatch, caplog):
    from railway_lakehouse.silver.news import embeddings

    class FlakyModel:
        def encode(self, text, **kwargs):
            if "bad" in text:
                raise RuntimeError("encoder failed")
            return np.array([0.4] * 768, dtype=np.float32)

    monkeypatch.setattr(embeddings, "load_embedding_model", lambda model_name=embeddings.DEFAULT_EMBEDDING_MODEL: FlakyModel())
    bad = _feature("bad", summary="bad article")
    good = _feature("good", summary="good article")

    result = embeddings.compute_embeddings([bad, good])

    assert result[0].text_embedding is None
    assert result[1].text_embedding == pytest.approx([0.4] * 768)
    assert "news embedding skipped for bad" in caplog.text


def test_cluster_near_duplicates_groups_identical_embeddings():
    from railway_lakehouse.silver.news.embeddings import cluster_near_duplicates

    rows = [
        _feature("b", embedding=[1.0, 0.0, 0.0]),
        _feature("a", embedding=[1.0, 0.0, 0.0]),
        _feature("c", embedding=[0.0, 1.0, 0.0]),
    ]

    result = cluster_near_duplicates(rows, threshold=0.95)
    grouped = {row.article_id: row for row in result}

    assert grouped["a"].cross_lingual_dedup_id == grouped["b"].cross_lingual_dedup_id
    assert grouped["a"].is_duplicate is False
    assert grouped["b"].is_duplicate is True
    assert grouped["c"].cross_lingual_dedup_id is None
    assert grouped["c"].is_duplicate is False


def test_cluster_near_duplicates_deterministic_group_ids_for_shuffled_input():
    from railway_lakehouse.silver.news.embeddings import cluster_near_duplicates

    first = [
        _feature("a", embedding=[1.0, 0.0, 0.0]),
        _feature("b", embedding=[1.0, 0.0, 0.0]),
    ]
    second = [
        _feature("b", embedding=[1.0, 0.0, 0.0]),
        _feature("a", embedding=[1.0, 0.0, 0.0]),
    ]

    first_group = cluster_near_duplicates(first, threshold=0.95)[0].cross_lingual_dedup_id
    second_rows = cluster_near_duplicates(second, threshold=0.95)
    second_group = next(row for row in second_rows if row.article_id == "a").cross_lingual_dedup_id

    assert first_group == second_group


def test_cluster_near_duplicates_invalid_embeddings_degrade_gracefully(caplog):
    from railway_lakehouse.silver.news.embeddings import cluster_near_duplicates

    rows = [_feature("a", embedding=[]), _feature("b", embedding=[1.0])]

    result = cluster_near_duplicates(rows, threshold=0.95)

    assert result == rows
    assert rows[0].cross_lingual_dedup_id is None
    assert rows[0].is_duplicate is None
    assert "no usable embeddings" in caplog.text
