# pandas 3.0 + pyarrow 24 + Python 3.14 upgrade gotchas (Parquet lakehouse)
> Skill: research-orchestrator | Routed MCP providers: Context7 (pandas docs), Tavily (search + extract). Ref attempted but out of credits.
> Date: 2026-06-23

## Queries
- Context7 resolve-library-id "pandas"; query-docs /websites/pandas_pydata for "default string dtype, read_parquet round trip, pivot_table, groupby observed, fillna downcasting, nullable Int64/Float64".
- Tavily search: "pandas 3.0 breaking changes Copy-on-Write default PyArrow strings migration guide"; "pandas 3.0 inplace fillna chained assignment ... SettingWithCopyWarning removed"; "pyarrow 24 release notes Python 3.14 support"; "pandas 3.0 read_parquet returns str dtype ..."; "pandas 3.0 Series.values returns ExtensionArray ...".
- Tavily extract: pandas v3.0.0 whatsnew; migration-3-strings guide; Apache Arrow 24.0.0 release blog.

## Sources
- https://pandas.pydata.org/docs/whatsnew/v3.0.0.html
- https://pandas.pydata.org/docs/user_guide/migration-3-strings.html
- https://pandas.pydata.org/docs/user_guide/copy_on_write.html
- https://pandas.pydata.org/docs/whatsnew/v2.2.0.html
- https://pandas.pydata.org/docs/whatsnew/v2.3.3.html
- https://github.com/pandas-dev/pandas/issues/63099
- https://arrow.apache.org/blog/2026/04/21/24.0.0-release
- https://pypi.org/project/pyarrow (cp314 wheels)

## Codebase exposure (railway-lakehouse, currently pandas>=2.2 / pyarrow>=15 / py>=3.12)
- `gold/build.py`: pivot_table x3, groupby+agg, to_parquet(engine="pyarrow"), fillna(0) on Float64-ish cols, `.dt.year.astype("Int64")`, `== True` mask, merge how=outer.
- `silver/persist.py`, `silver/stats/merge.py`, `silver/stats/load.py`: astype("string"/"Int64"/"Float64"/"boolean"), read_parquet/to_parquet.
- `pipeline.py`: read_parquet, heavy `.astype(str)` + `== "AT"`/`== "HU"` equality and `is_rail_related == True`.

## Top gotchas (see final answer for detail + URLs)
1. New default `str` dtype: read_parquet/constructors return `str` not `object`; `dtype == object` checks and `assert_frame_equal` exact dtype checks break.
2. `str` dtype rejects non-string values; missing = NaN (not pd.NA). astype("string") (pd.NA) vs default str (NaN) are different dtypes -> equality/test surprises.
3. Copy-on-Write default + SettingWithCopyWarning removed; chained inplace assignment silently no-ops.
4. inplace methods (fillna/replace/...) now return self instead of None.
5. read-only numpy arrays from .values/.to_numpy()/__array__ under CoW.
6. use_nullable_dtypes removed from read_parquet; pct_change limit removed; misc removals.
7. pivot_table/groupby on nullable Int64/Float64 -> result columns stay nullable; fillna(0) keeps Float64 not float64.
8. groupby observed=False behavior improved (categoricals) -> different row sets.
9. Frequency alias removals "M"/"Q"/"Y" -> "ME"/"QE"/"YE".
10. pyarrow becomes effectively required for the fast string path; pin pyarrow>=13 (pandas 3.0 floor) and use pyarrow 24 cp314 wheels; numpy>=1.26.
11. Python 3.14: need pandas>=2.3.3 baseline; free-threaded (3.14t) wheels exist for pyarrow but pandas free-threading is not guaranteed thread-safe -> use the GIL build.
