---
name: redshift
description: Query any AWS Redshift cluster via the Data API. Use whenever the user mentions Redshift, DWH, data warehouse, SQL queries, schema exploration, table metadata, DDL generation, column listing, disk usage, or wants to explore database objects. Covers running read-only queries, listing schemas/tables/columns, generating DDL for 7 object types (table, view, schema, database, UDF, external table, group), checking disk usage, sampling data, and searching for objects by name. Works on any Redshift cluster with no admin views required. Always use this skill for any Redshift-related task, even simple SELECT queries.
---

# Redshift Skill

Read-only Redshift exploration via the AWS Data API. Cross-platform (Mac + Windows).
All scripts are in `${CLAUDE_SKILL_DIR}/scripts/` and require only Python 3 + AWS CLI.

## Python Command

On macOS, use `python3`. On Windows, use `python`. To detect the right one, check
`~/.redshift-skill/config.json` for the `"python"` key (saved during setup), or run
`python3 --version` first, falling back to `python --version`.

Throughout this document, `PYTHON` means the detected Python command.

## First-Time Setup

Check if `~/.redshift-skill/config.json` exists. If not, run the setup wizard:

```bash
PYTHON ${CLAUDE_SKILL_DIR}/scripts/setup.py
```

This guides the user through profile selection, cluster discovery, and connectivity testing.
After setup, all scripts use saved defaults — no connection args needed.

## Quick Reference

All commands: `PYTHON ${CLAUDE_SKILL_DIR}/scripts/<script>.py [args]`

| Task | Script | Key Args |
|------|--------|----------|
| **Setup / reconfigure** | `setup.py` | |
| **Run SQL** | `query.py` | `"SELECT ..."` |
| **List schemas** | `schemas.py` | |
| **List tables** | `tables.py` | `--schema=NAME` |
| **List columns** | `columns.py` | `--schema=NAME --table=NAME` |
| **Table DDL** | `ddl.py` | `--schema=NAME --name=NAME` |
| **View DDL** | `ddl.py` | `--type=view --schema=NAME --name=NAME` |
| **Schema DDL** | `ddl.py` | `--type=schema [--name=NAME]` |
| **Database DDL** | `ddl.py` | `--type=database [--name=NAME]` |
| **UDF DDL** | `ddl.py` | `--type=udf [--schema=NAME] [--name=NAME]` |
| **External table DDL** | `ddl.py` | `--type=external [--schema=NAME] [--name=NAME]` |
| **Group DDL** | `ddl.py` | `--type=group [--name=NAME]` |
| **Table metadata** | `table_info.py` | `--schema=NAME --table=NAME` |
| **Search objects** | `search.py` | `--pattern=TEXT [--type=table\|column\|both]` |
| **Sample data** | `sample.py` | `--schema=NAME --table=NAME [--limit=N]` |
| **Disk usage** | `space.py` | `[--schema=NAME] [--top=N]` |

### Common options (all scripts)

| Option | Description |
|--------|-------------|
| `--format=txt\|csv\|json` | Output format (default: txt) |
| `--save=PATH` | Save output to file |
| `--profile=NAME` | Override AWS profile |
| `--cluster=NAME` | Override cluster |
| `--database=NAME` | Override database |
| `--db-user=NAME` | Override database user |
| `--timeout=N` | Max wait seconds (default: 120) |
| `--max-rows=N` | Max rows to fetch (default: 1000) |

## Read-Only Guardrails

**Two layers of protection:**

1. **You (Claude) must validate** — before passing any SQL to `query.py`, verify the first keyword is in the allowlist below. If the user asks to run a modifying query, refuse and explain why.

2. **`lib/client.py` enforces** — the script itself rejects non-allowlisted SQL before it reaches AWS. This is the hard guardrail.

**Allowed:** `SELECT`, `WITH`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `SET`

**Blocked:** `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `COPY`, `UNLOAD`, `GRANT`, `REVOKE`, `CALL`, `EXECUTE`, `VACUUM`, `ANALYZE`

Multi-statement queries (`;` followed by another statement) are also blocked.

## Output Formats

- **txt** (default): Aligned table — best for interactive exploration
- **csv**: Comma-separated — best for export and further processing
- **json**: Array of objects — best for programmatic use

For results exceeding 50 rows, output auto-saves to `~/redshift-exports/` and shows the first 20 rows inline.

## Bundled SQL

The skill ships with SQL extracted from [amazon-redshift-utils](https://github.com/awslabs/amazon-redshift-utils) admin views. These queries run directly against Redshift system catalogs — no admin schema or pre-installed views needed on the cluster. This provides rich DDL generation (with distkeys, sortkeys, encoding, constraints), extended table metadata, and detailed disk usage on any Redshift cluster.

## Advanced SQL Templates

For ad-hoc exploration via `query.py`:

**Data profiling:**
```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT column_name) AS distinct_values,
    SUM(CASE WHEN column_name IS NULL THEN 1 ELSE 0 END) AS null_count,
    MIN(column_name) AS min_value,
    MAX(column_name) AS max_value
FROM schema.table
```

**Query history (last 20):**
```sql
SELECT query, TRIM(querytxt) AS sql, starttime, endtime,
       DATEDIFF(ms, starttime, endtime) AS duration_ms
FROM stl_query
WHERE userid > 1
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
SELECT
    n1.nspname || '.' || c1.relname AS source_table,
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
