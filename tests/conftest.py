import pytest


class _NoOpSentimentEncoder:
    def encode(self, text):
        return None


@pytest.fixture(autouse=True)
def _disable_live_sentiment_encoder(monkeypatch):
    """Keep tests from downloading Hugging Face model weights by default."""
    try:
        from railway_lakehouse.silver.news import sentiment_encoder
    except ImportError:
        return
    monkeypatch.setattr(
        sentiment_encoder,
        "get_encoder",
        lambda: _NoOpSentimentEncoder(),
    )
