#!/usr/bin/env python3
"""List tables in a schema with extended metadata."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query, load_sql
from lib.formatter import format_output


def main():
    parser = argparse.ArgumentParser(description="List tables in a Redshift schema")
    add_connection_args(parser)
    parser.add_argument("--schema", required=True, help="Schema name")
    args = parser.parse_args()

    config = resolve_config(args)

    # Use bundled extended_table_info SQL
    sql = load_sql("extended_table_info", schema_filter=f"AND ti.schema = '{args.schema}'")
    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.max_rows)
    format_output(columns, rows, fmt=args.format, save_path=args.save)
    print(f"{len(rows)} tables. Duration: {meta['duration_ms']}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
