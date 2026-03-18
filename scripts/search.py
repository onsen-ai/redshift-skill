#!/usr/bin/env python3
"""Search for tables or columns by name pattern."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output, format_duration

TABLE_SQL = """
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_name ILIKE '%{pattern}%'
  AND table_schema NOT IN ('pg_catalog','information_schema','pg_internal')
ORDER BY table_schema, table_name
"""

COLUMN_SQL = """
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE column_name ILIKE '%{pattern}%'
  AND table_schema NOT IN ('pg_catalog','information_schema','pg_internal')
ORDER BY table_schema, table_name, column_name
"""


def main():
    parser = argparse.ArgumentParser(description="Search Redshift tables/columns by name")
    add_connection_args(parser)
    parser.add_argument("--pattern", required=True, help="Search pattern (case-insensitive)")
    parser.add_argument("--type", choices=["table", "column", "both"], default="both",
                        help="Search type (default: both)")
    args = parser.parse_args()

    config = resolve_config(args)

    if args.type in ("table", "both"):
        print("=== Tables ===")
        sql = TABLE_SQL.format(pattern=args.pattern)
        columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.max_rows)
        format_output(columns, rows, fmt=args.format, save_path=args.save)
        print(f"{len(rows)} tables found. Duration: {format_duration(meta['duration_secs'])}\n", file=sys.stderr)

    if args.type in ("column", "both"):
        print("=== Columns ===")
        sql = COLUMN_SQL.format(pattern=args.pattern)
        columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.max_rows)
        format_output(columns, rows, fmt=args.format, save_path=args.save)
        print(f"{len(rows)} columns found. Duration: {format_duration(meta['duration_secs'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
