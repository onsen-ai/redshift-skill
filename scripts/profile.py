#!/usr/bin/env python3
"""Profile a Redshift table — per-column statistics via a single query."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output, format_duration


def build_profile_sql(schema, table, columns_info):
    """Build a profiling SQL query from column metadata."""
    parts = []
    for col_name, data_type in columns_info:
        is_numeric = any(t in data_type.upper() for t in
                        ["INT", "NUMERIC", "DECIMAL", "FLOAT", "DOUBLE", "REAL", "BIGINT", "SMALLINT"])
        is_date = any(t in data_type.upper() for t in ["DATE", "TIMESTAMP", "TIME"])

        col_q = f'"{col_name}"'
        parts.append(f"""
SELECT
    '{col_name}' AS column_name,
    '{data_type}' AS data_type,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN {col_q} IS NULL THEN 1 ELSE 0 END) AS null_count,
    ROUND(SUM(CASE WHEN {col_q} IS NULL THEN 1 ELSE 0 END)::DECIMAL / COUNT(*)::DECIMAL * 100, 1) AS null_pct,
    COUNT(DISTINCT {col_q}) AS distinct_count,
    {'MIN(' + col_q + ')::VARCHAR(100)' if is_numeric or is_date else 'MIN(' + col_q + '::VARCHAR(100))'} AS min_val,
    {'MAX(' + col_q + ')::VARCHAR(100)' if is_numeric or is_date else 'MAX(' + col_q + '::VARCHAR(100))'} AS max_val,
    {'ROUND(AVG(' + col_q + '::DECIMAL), 4)::VARCHAR(100)' if is_numeric else "''"} AS avg_val
FROM "{schema}"."{table}"
""")

    return "\nUNION ALL\n".join(parts)


# Simple column listing SQL (same approach as columns.py)
COLUMNS_SQL = """
SELECT column_name, UPPER(data_type) AS data_type
FROM svv_columns
WHERE table_schema = '{schema}' AND table_name = '{table}'
ORDER BY ordinal_position
"""


def main():
    parser = argparse.ArgumentParser(description="Profile a Redshift table — per-column statistics")
    add_connection_args(parser)
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table", required=True, help="Table name")
    args = parser.parse_args()

    config = resolve_config(args)

    # Step 1: Get column list
    print(f"Fetching columns for {args.schema}.{args.table}...", file=sys.stderr)
    col_sql = COLUMNS_SQL.format(schema=args.schema, table=args.table)
    _, col_rows, _ = execute_query(col_sql, config, timeout=args.timeout, max_rows=500)

    if not col_rows:
        print(f"ERROR: No columns found for {args.schema}.{args.table}", file=sys.stderr)
        sys.exit(1)

    columns_info = [(row[0], row[1]) for row in col_rows]
    print(f"  Found {len(columns_info)} columns. Running profile query...", file=sys.stderr)

    # Step 2: Run profile query
    profile_sql = build_profile_sql(args.schema, args.table, columns_info)
    columns, rows, meta = execute_query(profile_sql, config, timeout=300, max_rows=500)

    format_output(columns, rows, fmt=args.format, save_path=args.save, no_save=args.no_save)
    print(f"Duration: {format_duration(meta['duration_secs'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
