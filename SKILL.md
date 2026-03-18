---
name: redshift
description: Query any AWS Redshift cluster via the Data API. Use whenever the user mentions Redshift, DWH, data warehouse, SQL queries, schema exploration, table metadata, DDL generation, column listing, disk usage, data profiling, or wants to explore database objects. Also use for local analytics on previously saved query results. Works on any Redshift cluster with no admin views required. Always use this skill for any Redshift-related task, even simple SELECT queries.
---

# Redshift Skill

Read-only Redshift exploration via the AWS Data API. Cross-platform (Mac + Windows).
All scripts are in `${CLAUDE_SKILL_DIR}/scripts/` and require only Python 3 + AWS CLI.

## Python Command

Read `~/.redshift-skill/config.json` and use the `"python"` key as the Python command.
If config doesn't exist yet, try `python3 --version` first, falling back to `python --version`.
Throughout this document, `PYTHON` means the detected Python command.

## First-Time Setup

**You cannot run the setup wizard directly** — it requires interactive terminal input.

Check if `~/.redshift-skill/config.json` exists:
- **If it exists:** You're good. Read it to confirm the connection details.
- **If it doesn't exist:** Tell the user to run the setup wizard in their terminal:

> Run this in your terminal to configure the Redshift connection:
> ```
> python3 scripts/setup.py
> ```
> (On Windows, use `python` instead of `python3`)

Then wait for the user to confirm setup is complete before running any queries.

## Quick Reference

| Task | Script | When to use | Key Args |
|------|--------|-------------|----------|
| **Run SQL** | `query.py` | Free-form read-only SQL queries | `"SELECT ..."` |
| **List schemas** | `schemas.py` | See all schemas and their owners | |
| **List tables** | `tables.py` | Browse tables in a schema with sizes and row counts | `--schema=NAME` |
| **List columns** | `columns.py` | See column names, types, encoding, dist/sort keys | `--schema=NAME --table=NAME` |
| **Table DDL** | `ddl.py` | Get CREATE TABLE with full encoding, distkey, sortkey | `--schema=NAME --name=NAME` |
| **View DDL** | `ddl.py` | Get CREATE VIEW definition | `--type=view --schema=NAME --name=NAME` |
| **Schema DDL** | `ddl.py` | Get CREATE SCHEMA with authorization | `--type=schema [--name=NAME]` |
| **Database DDL** | `ddl.py` | Get CREATE DATABASE | `--type=database` |
| **UDF DDL** | `ddl.py` | Get function definitions (SQL + Python) | `--type=udf [--schema=NAME]` |
| **External DDL** | `ddl.py` | Get Spectrum external table DDL | `--type=external [--schema=NAME]` |
| **Group DDL** | `ddl.py` | Get user group definitions | `--type=group` |
| **Table metadata** | `table_info.py` | Detailed table stats (size, rows, skew, sortkey, encoding) | `--schema=NAME --table=NAME` |
| **Search objects** | `search.py` | Find tables or columns by name pattern | `--pattern=TEXT` |
| **Sample data** | `sample.py` | Quick peek at actual data in a table | `--schema=NAME --table=NAME` |
| **Disk usage** | `space.py` | Find the largest tables by size | `[--schema=NAME] [--top=N]` |
| **Data profile** | `profile.py` | Per-column stats (nulls, distinct, min/max/avg) via Redshift | `--schema=NAME --table=NAME` |
| **Local analytics** | `analyze.py` | Analyze saved result files locally without hitting Redshift | `FILE --describe` |

### Common options (all Redshift scripts)

| Option | Description |
|--------|-------------|
| `--format=txt\|csv\|json` | Output format (default: txt) |
| `--save=PATH` | Save to a specific file path |
| `--no-save` | Don't auto-save to ~/redshift-exports/ |
| `--profile=NAME` | Override AWS profile |
| `--cluster=NAME` | Override cluster |
| `--database=NAME` | Override database |
| `--db-user=NAME` | Override database user |
| `--timeout=N` | Max wait seconds (default: 120) |
| `--max-rows=N` | Max rows to fetch (default: 1000) |

## Output and File Saving

All query results are **automatically saved** to `~/redshift-exports/query-{timestamp}.{ext}`.
The first 20 rows are shown inline for quick preview. The saved file path is printed to stderr.

This means you always have:
- **Inline preview** (20 rows) for quick answers
- **Full file on disk** for follow-up analysis with `analyze.py`

Use `--no-save` to skip auto-save for trivial queries. Use `--save=PATH` to save to a specific location.

## Script Details

### query.py — Run SQL

Run any read-only SQL query against Redshift.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/query.py "SELECT count(1) FROM odl.fact_basket_items"
```
```
count
-----
997908827
1 rows returned (1 total). Duration: 25ms
Results saved to: ~/redshift-exports/query-20260318_150505.txt
```

### schemas.py — List schemas

List all user schemas with their owners.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/schemas.py
```
```
schema_name  owner
-----------  -------
adl          matillion
admin        admin
odl          matillion
...
313 schemas. Duration: 54ms
```

### tables.py — List tables

List tables in a schema with row counts, size, distribution style, and sort keys.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/tables.py --schema=odl
```
```
table_name       row_count  size_mb  diststyle  sortkey1     unsorted  pct_used
--------------   ---------  -------  ---------  ----------   --------  --------
dim_stores       17906      246      ALL        store_sk     100.00    0.0000
fact_basket...   997908827  1234567  KEY(...)   date_nk      28.40     1.2345
...
1000 tables. Duration: 11s
```

### columns.py — List columns

Show column names, data types, encoding, distribution key, and sort key position.
Works with tables, views, and late-binding views.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/columns.py --schema=odl --table=dim_stores
```
```
pos  column_name    data_type          max_len  encoding  distkey  sortkey
---  -------------  -----------------  -------  --------  -------  -------
1    store_nk       CHARACTER VARYING  200      lzo       False    0
2    store_sk       CHARACTER VARYING  200      none      False    1
...
38 columns. Duration: 2s
```

### ddl.py — Generate DDL

Generate DDL for 7 object types. Full CREATE TABLE includes encoding, distkey, sortkey, constraints, comments, and ownership.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --schema=odl --name=dim_stores
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=view --schema=odl --name=fact_basket_items
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=schema --name=odl
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=database
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=group
```
```
CREATE TABLE IF NOT EXISTS odl.dim_stores
(
    store_nk VARCHAR(200) ENCODE lzo
    ,store_sk VARCHAR(200) ENCODE RAW
    ...
)
DISTSTYLE ALL
 SORTKEY (store_sk)
;
ALTER TABLE odl.dim_stores owner to matillion;
```

### table_info.py — Table metadata

Detailed stats for a single table: size, rows, distribution skew, encoding, sort key performance.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/table_info.py --schema=odl --table=dim_stores
```
```
tablename       row_count  size_mb  pct_used  diststyle  sortkey1  unsorted  stats_off  encoded
--------------  ---------  -------  --------  ---------  --------  --------  ---------  -------
odl.dim_stores  17906      246      0.0000    ALL        store_sk  100.00    100.00     Y, AUTO
```

### search.py — Search objects

Find tables or columns by name pattern (case-insensitive).

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/search.py --pattern=basket
PYTHON ${CLAUDE_SKILL_DIR}/scripts/search.py --pattern=price --type=column
```
```
=== Tables ===
table_schema  table_name                  table_type
------------  -------------------------   ----------
odl           fact_basket_items           VIEW
odl           fact_basket_items_mv        BASE TABLE
...
616 tables found. Duration: 128ms
```

### sample.py — Sample data

Quick peek at actual row data. Useful for understanding column values.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/sample.py --schema=odl --table=dim_stores --limit=3
```

### space.py — Disk usage

Find the largest tables, optionally filtered by schema.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/space.py --schema=odl --top=5
```
```
schemaname  tablename                     size_mb    row_count     pct_used
----------  ----------------------------  ---------  -----------   --------
odl         fact_traffic_bq_realtime_agg  18823412   106379898412  2.4509
odl         fact_historical_product_...   2545379    11824492089   0.3314
...
5 tables. Duration: 33s
```

### profile.py — Data profiling (via Redshift)

Runs a single Redshift query to compute per-column statistics: null count, distinct values, min, max, avg.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/profile.py --schema=odl --table=dim_stores
```
```
column_name     data_type          total_rows  null_count  null_pct  distinct_count  min_val  max_val  avg_val
--------------  -----------------  ----------  ----------  --------  --------------  -------  -------  -------
store_nk        CHARACTER VARYING  17906       0           0.0       17906           store-1  store-99
store_latitude  NUMERIC            17906       0           0.0       1234            -33.8    55.9     51.2345
...
```

### analyze.py — Local analytics (no Redshift)

Analyze previously saved CSV/JSON files locally. No network access needed.

```bash
# Describe all columns
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py ~/redshift-exports/query-*.csv --describe

# Sum a column
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --sum=revenue

# Group by with aggregation
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --group-by=region --sum=sales

# Filter + sort + top N
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --filter='year=2024' --sort=amount --desc --top=10

# Histogram
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --hist=price
```

Available operations: `--count`, `--describe`, `--sum=COL`, `--avg=COL`, `--min=COL`, `--max=COL`, `--median=COL`, `--group-by=COL`, `--filter=EXPR`, `--sort=COL`, `--desc`, `--top=N`, `--hist=COL`

## Read-Only Guardrails

**Two layers of protection:**

1. **You (Claude) must validate** — before passing any SQL to `query.py`, verify the first keyword is in the allowlist below. If the user asks to run a modifying query, refuse and explain why.

2. **`lib/client.py` enforces** — the script itself rejects non-allowlisted SQL before it reaches AWS. This is the hard guardrail.

**Allowed:** `SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `SET`

**Blocked:** `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `COPY`, `UNLOAD`, `GRANT`, `REVOKE`, `CALL`, `EXECUTE`, `VACUUM`, `ANALYZE`

Multi-statement queries (`;` followed by another statement) are also blocked.

## Bundled SQL

The skill ships with SQL extracted from [amazon-redshift-utils](https://github.com/awslabs/amazon-redshift-utils) admin views in `${CLAUDE_SKILL_DIR}/scripts/sql/`. These run directly against system catalogs — no admin schema needed. Used by `ddl.py` for full DDL generation with distkeys, sortkeys, encoding, constraints, and comments.

## Advanced SQL Templates

For ad-hoc exploration via `query.py`:

**Query history (last 20):**
```sql
SELECT query, TRIM(querytxt) AS sql, starttime, endtime,
       DATEDIFF(ms, starttime, endtime) AS duration_ms
FROM stl_query WHERE userid > 1
ORDER BY starttime DESC LIMIT 20
```

**Running queries:**
```sql
SELECT user_name, db_name, query, pid, starttime, duration, status
FROM stv_recents WHERE status = 'Running'
ORDER BY starttime DESC
```

**Table dependencies (FK relationships):**
```sql
SELECT n1.nspname || '.' || c1.relname AS source_table,
       n2.nspname || '.' || c2.relname AS referenced_table,
       con.conname AS constraint_name
FROM pg_constraint con
JOIN pg_class c1 ON con.conrelid = c1.oid
JOIN pg_namespace n1 ON c1.relnamespace = n1.oid
JOIN pg_class c2 ON con.confrelid = c2.oid
JOIN pg_namespace n2 ON c2.relnamespace = n2.oid
WHERE con.contype = 'f'
ORDER BY source_table
```
