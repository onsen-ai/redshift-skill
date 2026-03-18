#!/usr/bin/env python3
"""Show extended table metadata."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query, load_sql
from lib.formatter import format_output, format_duration


def main():
    parser = argparse.ArgumentParser(description="Show extended metadata for a Redshift table")
    add_connection_args(parser)
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table", required=True, help="Table name")
    args = parser.parse_args()

    config = resolve_config(args)
    sql = load_sql(
        "extended_table_info",
        schema_filter=f"AND ti.schema = '{args.schema}' AND ti.\"table\" = '{args.table}'"
    )
    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.max_rows)
    format_output(columns, rows, fmt=args.format, save_path=args.save)
    print(f"Duration: {format_duration(meta['duration_secs'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
