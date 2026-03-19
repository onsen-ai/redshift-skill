---
name: redshift
description: Query any AWS Redshift cluster or serverless workgroup via the Data API. Use whenever the user mentions Redshift, DWH, data warehouse, SQL queries, schema exploration, table metadata, DDL generation, column listing, disk usage, data profiling, business analysis, or wants to explore database objects. Also use for local analytics on previously saved query results. Works on any Redshift cluster or serverless workgroup with no admin views required. Always use this skill for any Redshift-related task, even simple SELECT queries.
---

# Redshift Skill

Read-only Redshift exploration and business analysis via the AWS Data API. Works with both provisioned clusters and Redshift Serverless. Cross-platform (Mac + Windows). Works with any AI coding agent.

All scripts are in `${CLAUDE_SKILL_DIR}/scripts/` and require only Python 3 + AWS CLI.

## Python Command

Read `~/.redshift-skill/config.json` and use the `"python"` key as the Python command.
If config doesn't exist yet, try `python3 --version` first, falling back to `python --version`.
Throughout this document, `PYTHON` means the detected Python command.

## First-Time Setup

**You cannot run the setup wizard directly** — it requires interactive terminal input.

Check if `~/.redshift-skill/config.json` exists:
- **If it exists:** Read it to confirm the connection details.
- **If it doesn't exist:** Tell the user to run the setup wizard in their terminal:

> Run this in your terminal to configure the Redshift connection:
> ```
> python3 scripts/setup.py
> ```
> (On Windows, use `python` instead of `python3`)

Wait for the user to confirm setup is complete before running any queries.

## Quick Reference

| Task | Script | When to use | Key Args |
|------|--------|-------------|----------|
| **Run SQL** | `query.py` | Any free-form read-only query | `"SELECT ..."` or `--sql-file=PATH` |
| **List schemas** | `schemas.py` | Starting point — see what schemas exist | |
| **List tables** | `tables.py` | Browse tables, check row counts and sizes before querying | `--schema=NAME` |
| **List columns** | `columns.py` | Understand column types, encoding, dist/sort keys | `--schema=NAME --table=NAME` |
| **Table DDL** | `ddl.py` | Get full CREATE TABLE with encoding, distkey, sortkey | `--schema=NAME --name=NAME` |
| **View DDL** | `ddl.py` | Get CREATE VIEW definition | `--type=view --schema=NAME --name=NAME` |
| **Schema DDL** | `ddl.py` | Get CREATE SCHEMA with authorization | `--type=schema [--name=NAME]` |
| **Database DDL** | `ddl.py` | Get CREATE DATABASE | `--type=database` |
| **UDF DDL** | `ddl.py` | Get function definitions (SQL + Python) | `--type=udf [--schema=NAME]` |
| **External DDL** | `ddl.py` | Get Spectrum external table DDL | `--type=external [--schema=NAME]` |
| **Group DDL** | `ddl.py` | Get user group definitions | `--type=group` |
| **Table metadata** | `table_info.py` | Check size, rows, skew, encoding — before writing big queries | `--schema=NAME --table=NAME` |
| **Search objects** | `search.py` | Find tables or columns when you don't know the exact name | `--pattern=TEXT` |
| **Sample data** | `sample.py` | Quick peek at actual values — always do this before writing queries | `--schema=NAME --table=NAME` |
| **Disk usage** | `space.py` | Find the largest tables, identify storage issues | `[--schema=NAME] [--top=N]` |
| **Data profile** | `profile.py` | Per-column stats (nulls, cardinality, min/max/avg) | `--schema=NAME --table=NAME` |
| **Local analytics** | `analyze.py` | Analyze saved results locally without hitting Redshift | `FILE --describe` |

### Common options (all Redshift scripts)

| Option | Description |
|--------|-------------|
| `--format=txt\|csv\|json` | Output format (default: txt) |
| `--save=PATH` | Save to a specific file path |
| `--no-save` | Don't auto-save to ~/redshift-exports/ |
| `--sql-file=PATH` | Read SQL from a file (query.py only) |
| `--profile=NAME` | Override AWS profile |
| `--cluster=NAME` | Override cluster (provisioned) |
| `--workgroup=NAME` | Override workgroup (serverless) |
| `--database=NAME` | Override database |
| `--db-user=NAME` | Override database user (provisioned only) |
| `--timeout=N` | Max wait seconds (default: 120) |
| `--max-rows=N` | Max rows to fetch (default: 1000) |

## Output and File Saving

All query results are **automatically saved** to `~/redshift-exports/query-{timestamp}.{ext}`.
The first 20 rows are shown inline for quick preview. The saved file path is printed to stderr.

This means you always have:
- **Inline preview** (20 rows) — enough to understand the data shape and answer quick questions
- **Full file on disk** — for deeper analysis with `analyze.py` or for the user to open in a spreadsheet

Use `--no-save` to skip auto-save for trivial queries. Use `--save=PATH` to save to a specific location.

---

## Defensive Guardrails

These rules protect the cluster from expensive queries. Follow them — but use judgement. If the user explicitly asks for something that bends a rule, explain the trade-off and proceed if they confirm.

- **Never `SELECT *` from tables with >10K rows** — this tool is for exploration and analysis, not data export. Use aggregations, filters, or `sample.py` instead. For smaller tables, `SELECT *` is fine.
- **Always add `LIMIT`** when exploring unfamiliar tables (default LIMIT 100).
- **Check row counts first** — run `tables.py --schema=X` before writing queries so you know what you're dealing with.
- **Prefer aggregations for large tables** — `COUNT`, `SUM`, `AVG` with `GROUP BY` over pulling raw rows. Raw data is perfectly fine for small tables and when exploring/understanding data.
- **Filter on sort key for very large fact tables** — especially tables sorted by date/timestamp when filtering on a specific time period. Redshift uses zone maps to skip blocks, making date-range filters very efficient. Not strictly required, but strongly recommended for tables >100M rows.
- **Joins are fine** — Redshift handles large table joins well as long as the join condition is correct and you aggregate/filter the result appropriately. The risk is not the join itself but returning unbounded raw data from a join.
- **Avoid accidental cross joins** — always include `ON`/`USING` unless you intentionally need a cartesian product (e.g. exploding data by design).
- **Prefer `LIMIT` + `ORDER BY`** over unbounded selects when exploring.

**Size awareness:**

| Table size | Approach |
|------------|----------|
| <10K rows | Explore freely, `SELECT *` is fine |
| 10K–1M rows | Add `WHERE` or `LIMIT`, aggregations preferred for full-table queries |
| >1M rows | Always aggregate or filter, never `SELECT *`, use sort key filters on large fact tables |

---

## SQL Standards

Every SQL query you write must follow these rules:

### Always comment your SQL

Explain the business intent, not just the mechanics. Use section headers for complex queries.

### Always show the SQL to the user

- **Short queries (<10 lines):** show the full SQL inline with comments
- **Long queries (>10 lines):** save to `~/redshift-exports/query-{timestamp}.sql`, show the key parts inline, and reference the saved file

### Use `--sql-file` for complex queries

For long SQL, write it to a file first and execute with `--sql-file`:
```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/query.py --sql-file=~/redshift-exports/my_query.sql
```

### Formatting conventions

```sql
------------------------------------------------------------------------------------------------------------------------
-- Monthly revenue by region
-- Purpose: Aggregate order line items by region for the last 12 months
-- Filters: Excludes cancelled orders and zero-quantity items
------------------------------------------------------------------------------------------------------------------------
WITH monthly_revenue AS (
    SELECT  r.region_name,                                                           -- region dimension
            DATE_TRUNC('month', o.order_date) :: DATE                                AS month_nk,
            SUM(o.quantity)                                                          AS total_quantity,
            SUM(o.line_total)                                                        AS total_revenue,
            SUM(o.margin)                                                            AS total_margin,
            COUNT(DISTINCT o.customer_id)                                            AS unique_customers
    FROM    sales.fact_order_lines o
    JOIN    sales.dim_regions r                     USING (region_id)
    WHERE   o.order_date >= DATEADD(month, -12, CURRENT_DATE)
            AND o.quantity > 0
            AND o.order_status <> 'cancelled'
    GROUP   BY 1, 2
)
SELECT  region_name,
        month_nk,
        total_quantity,
        total_revenue,
        total_margin,
        unique_customers,
        -- margin percentage
        ROUND(total_margin / NULLIF(total_revenue, 0) * 100, 2)                     AS margin_pct
FROM    monthly_revenue
ORDER   BY region_name, month_nk
```

Key formatting rules:
- Section headers with `--` dashes above the query
- `SELECT`, `FROM`, `JOIN`, `WHERE`, `GROUP BY`, `ORDER BY` left-aligned
- Column aliases aligned with `AS` at a consistent column position
- Inline comments explaining non-obvious business logic
- CTE names that describe the business concept, not the technical operation

---

## Schema Exploration Workflow

Use this graduated approach when exploring an unfamiliar schema. **Don't follow this rigidly** — if the user's intent is clear and specific, skip straight to the relevant step. Parallelise steps where possible.

1. **Understand the landscape** — `schemas.py` → see what schemas exist
2. **Browse tables** — `tables.py --schema=X` → check row counts and sizes
3. **Understand structure** — `columns.py --schema=X --table=Y` → column types, keys
4. **Check metadata** — `table_info.py` → distribution, sort key, unsorted %
5. **Sample first** — `sample.py --limit=5` → see actual data values
6. **Profile if needed** — `profile.py` → nulls, cardinality, min/max per column
7. **Write targeted queries** — now you know enough to write safe, efficient SQL
8. **Analyze locally** — `analyze.py` on saved results for follow-up

**Shortcut:** If the user says "how many orders last month?", don't run 6 discovery scripts. Check the table size, write the query, run it.

---

## Business Analysis Workflows

These are patterns for approaching common business questions. Think like a product analyst, commercial analyst, or BI developer.

### Understanding business performance

1. **Start with the headline metric** — total revenue, order count, customer count for the period
2. **Break down by dimensions** — time (daily/weekly/monthly), region, channel, product category
3. **Compare periods** — this month vs last month, this year vs last year, vs same period last year
4. **Identify outliers** — which segments are significantly above or below expectations?

### Root cause analysis

When something looks wrong ("revenue dropped 15% last week"):

1. **Confirm the anomaly** — is it real? Check the data source, compare with other metrics
2. **Decompose the metric** — is it volume (fewer orders) or value (lower average order)?
3. **Slice by dimensions** — which region/channel/category drove the change?
4. **Drill into the outlier** — what changed in that segment? New products? Pricing? Stock issues?
5. **Correlate with events** — promotions starting/ending, price changes, stock-outs, seasonality

### Common analyst patterns

| Pattern | Approach | SQL shape |
|---------|----------|-----------|
| **Trend analysis** | Track metrics over time | `GROUP BY date/month` + `SUM`/`COUNT`, compare YoY/MoM |
| **Cohort analysis** | Group by first purchase, track retention | `MIN(order_date)` per customer, then join back |
| **Distribution analysis** | Understand spread of values | `NTILE(100)`, percentiles, use `analyze.py --hist` locally |
| **Top/bottom N** | Best and worst performers | `ORDER BY metric DESC LIMIT N` |
| **YoY comparison** | Year-over-year growth | Self-join on date shifted by 1 year, or `LAG()` window function |
| **Funnel analysis** | Conversion at each step | `COUNT(DISTINCT user_id)` per step, compute drop-off rates |
| **Contribution / Pareto** | Which items drive 80% of revenue | Cumulative `SUM() OVER (ORDER BY ...)`, find the 80% cutoff |
| **Segmentation** | Group entities by behavior | `CASE WHEN` or `NTILE` to bucket, then profile each segment |

---

## Script Details

### query.py — Run SQL

Run any read-only SQL query. Accepts SQL as a command-line argument or from a file.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/query.py "SELECT count(1) FROM sales.fact_orders"
PYTHON ${CLAUDE_SKILL_DIR}/scripts/query.py --sql-file=~/redshift-exports/my_query.sql
```
```
count
-----
12500000
1 rows returned (1 total). Duration: 25ms
Results saved to: ~/redshift-exports/query-20260318_150505.txt
```

### schemas.py — List schemas

List all user schemas with their owners. Starting point for exploration.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/schemas.py
```
```
schema_name   owner
-----------   ---------
public        admin
sales         etl_user
marketing     etl_user
...
```

### tables.py — List tables

List tables in a schema with row counts, size, distribution style, and sort keys. **Run this before writing queries** so you know what you're dealing with.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/tables.py --schema=sales
```
```
table_name       row_count   size_mb  diststyle  sortkey1     unsorted  pct_used
--------------   ----------  -------  ---------  ----------   --------  --------
dim_customers    250000      120      ALL        customer_id  0.00      0.0100
dim_products     15000       48       ALL        product_id   0.00      0.0000
fact_orders      85000000    45000    KEY(...)   order_date   12.50     5.8600
...
```

### columns.py — List columns

Show column names, data types, encoding, distribution key, and sort key position. Works with tables, views, and late-binding views.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/columns.py --schema=sales --table=fact_orders
```
```
pos  column_name    data_type          max_len  encoding  distkey  sortkey
---  -------------  -----------------  -------  --------  -------  -------
1    order_id       CHARACTER VARYING  200      lzo       False    0
2    order_date     DATE                        az64      False    1
3    customer_id    CHARACTER VARYING  200      lzo       True     0
...
```

### ddl.py — Generate DDL

Generate DDL for 7 object types. Full CREATE TABLE includes encoding, distkey, sortkey, constraints, comments, and ownership.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --schema=sales --name=fact_orders
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=view --schema=sales --name=v_daily_revenue
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=schema --name=sales
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=database
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=udf --schema=public
PYTHON ${CLAUDE_SKILL_DIR}/scripts/ddl.py --type=group
```

### table_info.py — Table metadata

Detailed stats for a single table: size, rows, distribution skew, encoding, sort key performance.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/table_info.py --schema=sales --table=fact_orders
```
```
tablename          row_count   size_mb  pct_used  diststyle     sortkey1    unsorted  stats_off
-----------------  ----------  -------  --------  -----------   ----------  --------  ---------
sales.fact_orders  85000000    45000    5.8600    KEY(cust_id)  order_date  12.50     0.00
```

### search.py — Search objects

Find tables or columns by name pattern (case-insensitive). Useful when you don't know the exact name.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/search.py --pattern=order
PYTHON ${CLAUDE_SKILL_DIR}/scripts/search.py --pattern=revenue --type=column
```

### sample.py — Sample data

Quick peek at actual row data. **Always do this before writing complex queries** — it helps you understand column values, formats, and nullability.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/sample.py --schema=sales --table=dim_customers --limit=5
```

### space.py — Disk usage

Find the largest tables, optionally filtered by schema.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/space.py --schema=sales --top=5
```
```
schemaname  tablename         size_mb  row_count   pct_used
----------  ----------------  -------  ----------  --------
sales       fact_orders       45000    85000000    5.8600
sales       fact_line_items   32000    420000000   4.1700
...
```

### profile.py — Data profiling (via Redshift)

Runs a single Redshift query to compute per-column statistics. Useful for understanding data quality before analysis.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/profile.py --schema=sales --table=dim_customers
```
```
column_name     data_type          total_rows  null_count  null_pct  distinct_count  min_val    max_val    avg_val
--------------  -----------------  ----------  ----------  --------  --------------  ---------  ---------  -------
customer_id     CHARACTER VARYING  250000      0           0.0       250000          C0001      C250000
customer_name   CHARACTER VARYING  250000      12          0.0       249500          Aaron      Zoe
signup_date     DATE               250000      0           0.0       3650            2015-01-01 2025-12-31
lifetime_value  NUMERIC            250000      1500        0.6       48000           0.00       125000.00  2340.50
```

### analyze.py — Local analytics (no Redshift)

Analyze previously saved CSV/JSON files locally. No network access needed — great for follow-up analysis without hitting the cluster again.

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py ~/redshift-exports/query-*.csv --describe
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --sum=revenue
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --group-by=region --sum=sales
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --filter='year=2024' --sort=amount --desc --top=10
PYTHON ${CLAUDE_SKILL_DIR}/scripts/analyze.py data.csv --hist=price
```

Available operations: `--count`, `--describe`, `--sum=COL`, `--avg=COL`, `--min=COL`, `--max=COL`, `--median=COL`, `--group-by=COL`, `--filter=EXPR`, `--sort=COL`, `--desc`, `--top=N`, `--hist=COL`

---

## Read-Only Guardrails

**Two layers of protection:**

1. **You must validate** — before passing any SQL to `query.py`, verify the first keyword is in the allowlist. If the user asks to run a modifying query, refuse and explain why.

2. **`lib/client.py` enforces** — the script itself rejects non-allowlisted SQL before it reaches AWS. This is a hard guardrail that cannot be bypassed.

**Allowed:** `SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `SET`

**Blocked:** `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `COPY`, `UNLOAD`, `GRANT`, `REVOKE`, `CALL`, `EXECUTE`, `VACUUM`, `ANALYZE`

Multi-statement queries (`;` followed by another statement) are also blocked.

---

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
