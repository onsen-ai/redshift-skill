#!/usr/bin/env python3
"""List tables in a schema with extended metadata."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output, format_duration

SQL_TEMPLATE = """
SELECT
    ti."table" AS table_name,
    ti.tbl_rows AS row_count,
    ti.size AS size_mb,
    ti.diststyle,
    ti.sortkey1,
    ti.unsorted,
    ti.pct_used
FROM svv_table_info ti
WHERE ti.schema = '{schema}'
ORDER BY ti."table"
"""


def main():
    parser = argparse.ArgumentParser(description="List tables in a Redshift schema")
    add_connection_args(parser)
    parser.add_argument("--schema", required=True, help="Schema name")
    args = parser.parse_args()

    config = resolve_config(args)
    sql = SQL_TEMPLATE.format(schema=args.schema)
    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.max_rows)
    format_output(columns, rows, fmt=args.format, save_path=args.save)
    print(f"{len(rows)} tables. Duration: {format_duration(meta['duration_secs'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
