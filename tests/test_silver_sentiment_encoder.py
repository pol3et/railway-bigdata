import pytest

from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news import sentiment_encoder

pytestmark = pytest.mark.unit


class _FakeSentimentPipeline:
    def __init__(self, label, score):
        self.label = label
        self.score = score
        self.seen_texts = []

    def __call__(self, text, **kwargs):
        self.seen_texts.append(text)
        return [{"label": self.label, "score": self.score}]


def _pipeline_factory(label, score, calls=None):
    def factory(*args, **kwargs):
        if calls is not None:
            calls.append({"args": args, "kwargs": kwargs})
        return _FakeSentimentPipeline(label, score)

    return factory


def test_sentiment_encoder_initialization_with_mocked_pipeline():
    calls = []
    encoder = sentiment_encoder.SentimentEncoder(
        pipeline_factory=_pipeline_factory("Positive", 0.91, calls),
    )

    assert encoder.health_check() is True
    assert calls[0]["args"][0] == "sentiment-analysis"
    assert calls[0]["kwargs"]["model"] == sentiment_encoder.MODEL_NAME
    assert calls[0]["kwargs"]["tokenizer"] == sentiment_encoder.MODEL_NAME
    assert calls[0]["kwargs"]["revision"] == sentiment_encoder.MODEL_REVISION
    assert calls[0]["kwargs"]["device"] == -1


@pytest.mark.parametrize(
    ("raw_label", "raw_score", "text", "expected_label"),
    [
        ("Positive", 0.87, "Great news!", "positive"),
        ("negative", 0.81, "Accident on the railway", "negative"),
        ("Neutral", 0.73, "Railway statistics for 2024", "neutral"),
    ],
)
def test_sentiment_encoder_encodes_labels(raw_label, raw_score, text, expected_label):
    encoder = sentiment_encoder.SentimentEncoder(
        pipeline_factory=_pipeline_factory(raw_label, raw_score),
    )

    result = encoder.encode(text)

    assert result == {"label": expected_label, "score": pytest.approx(raw_score)}
    assert isinstance(result["score"], float)
    assert 0.0 <= result["score"] <= 1.0


def test_sentiment_encoder_truncates_long_text_at_model_boundary():
    class LongTextPipeline:
        def __init__(self):
            self.calls = []

        def __call__(self, text, **kwargs):
            self.calls.append({"text": text, "kwargs": kwargs})
            if len(text.split()) > sentiment_encoder.MODEL_MAX_LENGTH and kwargs != {
                "truncation": True,
                "max_length": sentiment_encoder.MODEL_MAX_LENGTH,
            }:
                raise ValueError("sequence length exceeds model limit")
            return [{"label": "positive", "score": 0.88}]

    pipeline = LongTextPipeline()
    encoder = sentiment_encoder.SentimentEncoder(
        pipeline_factory=lambda *args, **kwargs: pipeline,
    )
    long_text = "railway " * 700

    result = encoder.encode(long_text)

    assert result == {"label": "positive", "score": pytest.approx(0.88)}
    assert pipeline.calls[0]["kwargs"] == {
        "truncation": True,
        "max_length": sentiment_encoder.MODEL_MAX_LENGTH,
    }


def test_sentiment_encoder_returns_none_on_model_unavailable():
    def failing_factory(*args, **kwargs):
        raise RuntimeError("model unavailable")

    encoder = sentiment_encoder.SentimentEncoder(pipeline_factory=failing_factory)

    assert encoder.encode("Great news!") is None
    assert encoder.health_check() is False


def test_extract_article_with_sentiment_encoder(monkeypatch):
    encoded_texts = []

    class FakeEncoder:
        def encode(self, text):
            encoded_texts.append(text)
            return {"label": "positive", "score": 0.74}

    def fake_generate_json(prompt, *, schema=None, system=None):
        properties = schema["properties"]
        assert "sentiment" not in properties
        assert "confidence" not in properties
        return {
            "is_rail_related": True,
            "country": "HU",
            "event_type": "investment",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "Railway investment was announced.",
        }

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)
    monkeypatch.setattr(
        news_extract.sentiment_encoder,
        "get_encoder",
        lambda: FakeEncoder(),
    )

    feature = news_extract.extract_article(
        article_id="sentiment-a1",
        source="rss",
        url="https://example.test/sentiment-a1",
        title="Great rail investment",
        body="Railway upgrades were approved.",
        published_date="2026-06-25",
    )

    assert feature.sentiment == "positive"
    assert feature.confidence == pytest.approx(0.74)
    assert feature.sentiment_label == "positive"
    assert feature.sentiment_confidence == pytest.approx(0.74)
    assert feature.sentiment_score == pytest.approx(0.74)
    assert encoded_texts == ["Great rail investment\n\nRailway upgrades were approved."]


def test_extract_article_ignores_legacy_llm_sentiment_when_encoder_unavailable(monkeypatch):
    def fake_generate_json(prompt, *, schema=None, system=None):
        return {
            "is_rail_related": True,
            "country": "AT",
            "event_type": "accident",
            "monetary_amount_eur": None,
            "monetary_raw": None,
            "summary_en": "Railway services were disrupted.",
            "sentiment": "negative",
            "confidence": 0.99,
        }

    class UnavailableEncoder:
        def encode(self, text):
            return None

    monkeypatch.setattr(news_extract, "generate_json", fake_generate_json)
    monkeypatch.setattr(
        news_extract.sentiment_encoder,
        "get_encoder",
        lambda: UnavailableEncoder(),
    )

    feature = news_extract.extract_article(
        article_id="legacy-sentiment",
        source="rss",
        url="https://example.test/legacy-sentiment",
        title="Rail disruption",
        body="Accident on the railway.",
        published_date="2026-06-25",
    )

    assert feature.sentiment is None
    assert feature.confidence is None
    assert feature.sentiment_label is None
    assert feature.sentiment_score is None
    assert feature.sentiment_confidence is None
