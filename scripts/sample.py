#!/usr/bin/env python3
"""Sample rows from a table."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output


def main():
    parser = argparse.ArgumentParser(description="Sample rows from a Redshift table")
    add_connection_args(parser)
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table", required=True, help="Table name")
    parser.add_argument("--limit", type=int, default=10, help="Number of rows (default: 10)")
    args = parser.parse_args()

    config = resolve_config(args)
    sql = f'SELECT * FROM "{args.schema}"."{args.table}" LIMIT {args.limit}'
    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.limit)
    format_output(columns, rows, fmt=args.format, save_path=args.save)
    print(f"{len(rows)} rows. Duration: {meta['duration_ms']}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
