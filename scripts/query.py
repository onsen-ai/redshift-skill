#!/usr/bin/env python3
"""Run a read-only SQL query against Redshift."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output


def main():
    parser = argparse.ArgumentParser(description="Run a read-only SQL query against Redshift")
    add_connection_args(parser)
    parser.add_argument("sql", help="SQL query to execute")
    args = parser.parse_args()

    config = resolve_config(args)
    columns, rows, meta = execute_query(
        args.sql, config, timeout=args.timeout, max_rows=args.max_rows
    )

    if columns:
        format_output(columns, rows, fmt=args.format, save_path=args.save)

    print(
        f"{len(rows)} rows returned ({meta['total_rows']} total). "
        f"Duration: {meta['duration_ms']}ms",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
