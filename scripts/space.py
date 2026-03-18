#!/usr/bin/env python3
"""Show disk usage per table."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output, format_duration

SQL_TEMPLATE = """
SELECT
    ti.schema AS schemaname,
    ti."table" AS tablename,
    ti.size AS size_mb,
    ti.tbl_rows AS row_count,
    ti.unsorted,
    ti.diststyle,
    ti.sortkey1,
    ti.pct_used
FROM svv_table_info ti
{schema_filter}
ORDER BY ti.size DESC NULLS LAST
LIMIT {top}
"""


def main():
    parser = argparse.ArgumentParser(description="Show disk usage per Redshift table")
    add_connection_args(parser)
    parser.add_argument("--schema", help="Filter by schema name")
    parser.add_argument("--top", type=int, default=20, help="Show top N tables (default: 20)")
    args = parser.parse_args()

    config = resolve_config(args)

    schema_filter = f"WHERE ti.schema = '{args.schema}'" if args.schema else ""
    sql = SQL_TEMPLATE.format(schema_filter=schema_filter, top=args.top)

    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.top)
    format_output(columns, rows, fmt=args.format, save_path=args.save, no_save=args.no_save)
    print(f"{len(rows)} tables. Duration: {format_duration(meta['duration_secs'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
