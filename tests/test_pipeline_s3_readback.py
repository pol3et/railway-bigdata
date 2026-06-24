import gzip
import io
from pathlib import Path
from types import SimpleNamespace

import fsspec
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

import railway_lakehouse.pipeline as pipeline


pytestmark = pytest.mark.unit

FIXTURE_BRONZE = Path(__file__).parent / "fixtures" / "bronze"
FIXTURE_EUROSTAT = (
    FIXTURE_BRONZE
    / "stats"
    / "eurostat"
    / "rail_passengers_demo"
    / "ingest_date=2026-06-22"
    / "passengers.tsv"
)
FIXTURE_GDELT = (
    FIXTURE_BRONZE
    / "news"
    / "gdelt"
    / "HU"
    / "ingest_date=2026-06-22"
    / "gdelt_doc_HU_1w.json"
)
FIXTURE_RSS = (
    FIXTURE_BRONZE
    / "news"
    / "rss"
    / "hu_telex"
    / "ingest_date=2026-06-22"
    / "hu_telex.xml"
)


def _fresh_memory_fs():
    fs = fsspec.filesystem("memory")
    fs.store.clear()
    fs.pseudo_dirs[:] = [""]
    return fs


def _pipe(fs, path: str, payload: bytes | str) -> None:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    fs.pipe(path, payload)


def _gzip_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz:
        gz.write(text.encode("utf-8"))
    return buffer.getvalue()


def _seed_memory_bronze():
    fs = _fresh_memory_fs()
    _pipe(
        fs,
        "bronze/stats/eurostat/rail_passengers_demo/"
        "ingest_date=2026-06-22/passengers.tsv",
        FIXTURE_EUROSTAT.read_bytes(),
    )
    _pipe(
        fs,
        "bronze/stats/eurostat/rail_passengers_demo/"
        "ingest_date=2026-06-22/passengers.tsv.meta.json",
        b'{"source": "fixture"}\n',
    )
    _pipe(
        fs,
        "bronze/stats/eurostat/rail_passengers_demo_gzip/"
        "ingest_date=2026-06-22/passengers.tsv.gz",
        _gzip_bytes("category\t2020\t2021\nA,NR,HU\t300\t310\nA,NR,AT\t400\t410\n"),
    )
    _pipe(
        fs,
        "bronze/stats/eurostat/rail_passengers_demo_gzip/"
        "ingest_date=2026-06-22/passengers.tsv.gz.meta.json",
        b'{"source": "fixture"}\n',
    )
    _pipe(
        fs,
        "bronze/news/gdelt/HU/ingest_date=2026-06-22/gdelt_doc_HU_1w.json",
        FIXTURE_GDELT.read_bytes(),
    )
    _pipe(
        fs,
        "bronze/news/gdelt/HU/ingest_date=2026-06-22/gdelt_doc_HU_1w.json.meta.json",
        b'{"source": "fixture"}\n',
    )
    _pipe(
        fs,
        "bronze/news/rss/hu_telex/ingest_date=2026-06-22/hu_telex.xml",
        FIXTURE_RSS.read_bytes(),
    )
    _pipe(
        fs,
        "bronze/news/rss/hu_telex/ingest_date=2026-06-22/hu_telex.xml.meta.json",
        b'{"source": "fixture"}\n',
    )
    return fs


def _normalized(paths):
    return [str(path).replace("\\", "/").lstrip("/") for path in paths]


def test_list_bronze_files_uses_s3_glob_and_filters_sidecars():
    fs = _seed_memory_bronze()
    lander = SimpleNamespace(s3=fs)

    paths = pipeline._list_bronze_files(
        lander,
        domain="stats",
        source="eurostat",
        include=lambda name: name.endswith((".tsv", ".tsv.gz")),
    )

    assert _normalized(paths) == [
        "bronze/stats/eurostat/rail_passengers_demo/"
        "ingest_date=2026-06-22/passengers.tsv",
        "bronze/stats/eurostat/rail_passengers_demo_gzip/"
        "ingest_date=2026-06-22/passengers.tsv.gz",
    ]
    assert all(not str(path).endswith(".meta.json") for path in paths)
    assert all(not isinstance(path, Path) for path in paths)


def test_list_bronze_files_requires_local_root_or_s3_backend():
    with pytest.raises(ValueError, match="bronze_root or s3"):
        pipeline._list_bronze_files(
            object(),
            domain="stats",
            source="eurostat",
            include=lambda name: name.endswith(".tsv"),
        )


def test_read_tsv_reads_gzip_object_from_s3():
    fs = _seed_memory_bronze()
    lander = SimpleNamespace(s3=fs)
    [gzip_path] = pipeline._list_bronze_files(
        lander,
        domain="stats",
        source="eurostat",
        include=lambda name: name.endswith(".tsv.gz"),
    )

    df = pipeline._read_tsv(lander, gzip_path)

    expected = pd.DataFrame(
        {
            "category": ["A,NR,HU", "A,NR,AT"],
            "2020": [300, 400],
            "2021": [310, 410],
        }
    )
    assert_frame_equal(df, expected)


def test_read_tsv_local_and_s3_paths_return_equal_frames():
    fs = _seed_memory_bronze()
    local_lander = SimpleNamespace(bronze_root=FIXTURE_BRONZE)
    s3_lander = SimpleNamespace(s3=fs)
    [s3_path] = [
        path
        for path in pipeline._list_bronze_files(
            s3_lander,
            domain="stats",
            source="eurostat",
            include=lambda name: name.endswith(".tsv"),
        )
        if "rail_passengers_demo/" in str(path).replace("\\", "/")
    ]

    local_df = pipeline._read_tsv(local_lander, FIXTURE_EUROSTAT)
    s3_df = pipeline._read_tsv(s3_lander, s3_path)

    assert_frame_equal(s3_df, local_df)


def test_read_bronze_news_local_and_s3_paths_return_equal_articles():
    fs = _seed_memory_bronze()
    local_lander = SimpleNamespace(bronze_root=FIXTURE_BRONZE)
    s3_lander = SimpleNamespace(s3=fs)
    [s3_xml_path] = pipeline._list_bronze_files(
        s3_lander,
        domain="news",
        source="rss",
        include=lambda name: name.endswith(".xml"),
    )

    assert pipeline._read_text(s3_lander, s3_xml_path) == FIXTURE_RSS.read_bytes().decode(
        "utf-8"
    )
    assert pipeline._read_bronze_news(s3_lander, limit=10) == pipeline._read_bronze_news(
        local_lander, limit=10
    )


class _LocaleSensitiveTextMemoryFS:
    def __init__(self, fs, *, text_encoding: str):
        self._fs = fs
        self._text_encoding = text_encoding

    def __getattr__(self, name):
        return getattr(self._fs, name)

    def open(self, path, mode="rb", *args, **kwargs):
        if "b" in mode:
            return self._fs.open(path, mode, *args, **kwargs)
        return io.TextIOWrapper(
            self._fs.open(path, "rb", *args, **kwargs),
            encoding=self._text_encoding,
        )


def test_read_text_s3_utf8_payload_does_not_use_locale_text_decoding():
    fs = _fresh_memory_fs()
    utf8_xml = """<rss>
  <channel>
    <item>
      <title>Arvizturo 'vasut' cafe</title>
      <link>https://example.test/utf8-rail</link>
      <pubDate>2026-06-24</pubDate>
      <description>Arvizturo 'vasut' cafe</description>
    </item>
  </channel>
</rss>
""".replace("Arvizturo 'vasut' cafe", "Árvíztűrő ‘vasút’ café")
    _pipe(
        fs,
        "bronze/news/rss/utf8/ingest_date=2026-06-24/utf8.xml",
        utf8_xml,
    )
    lander = SimpleNamespace(
        s3=_LocaleSensitiveTextMemoryFS(fs, text_encoding="cp1251")
    )
    [s3_xml_path] = pipeline._list_bronze_files(
        lander,
        domain="news",
        source="rss",
        include=lambda name: name.endswith(".xml"),
    )

    assert pipeline._read_text(lander, s3_xml_path) == utf8_xml
    assert pipeline._read_bronze_news(lander, limit=1)[0] == {
        "article_id": "https://example.test/utf8-rail",
        "source": "rss",
        "url": "https://example.test/utf8-rail",
        "title": "Árvíztűrő ‘vasút’ café",
        "body": "Árvíztűrő ‘vasút’ café",
        "published_date": "2026-06-24",
    }
