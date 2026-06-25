import builtins
import importlib
import sys

import pytest

pytestmark = pytest.mark.unit


def test_sentiment_encoder_import_defers_missing_transformers(monkeypatch):
    sys.modules.pop("railway_lakehouse.silver.news.sentiment_encoder", None)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "transformers" or name.startswith("transformers."):
            raise ModuleNotFoundError("No module named 'transformers'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    module = importlib.import_module("railway_lakehouse.silver.news.sentiment_encoder")

    assert module.MODEL_NAME == "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    assert module.SentimentEncoder().health_check() is False
