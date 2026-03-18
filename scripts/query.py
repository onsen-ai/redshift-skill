#!/usr/bin/env python3
"""Run a read-only SQL query against Redshift."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output, format_duration


def main():
    parser = argparse.ArgumentParser(description="Run a read-only SQL query against Redshift")
    add_connection_args(parser)
    parser.add_argument("sql", nargs="?", help="SQL query to execute")
    parser.add_argument("--sql-file", dest="sql_file",
                        help="Read SQL from a file instead of command line")
    args = parser.parse_args()

    # Resolve SQL from either positional arg or --sql-file
    if args.sql_file:
        sql_path = Path(args.sql_file)
        if not sql_path.exists():
            print(f"ERROR: SQL file not found: {args.sql_file}", file=sys.stderr)
            sys.exit(1)
        sql = sql_path.read_text().strip()
    elif args.sql:
        sql = args.sql
    else:
        print("ERROR: Provide SQL as an argument or use --sql-file=PATH", file=sys.stderr)
        sys.exit(1)

    config = resolve_config(args)
    columns, rows, meta = execute_query(
        sql, config, timeout=args.timeout, max_rows=args.max_rows
    )

    if columns:
        format_output(columns, rows, fmt=args.format, save_path=args.save, no_save=args.no_save)

    print(
        f"{len(rows)} rows returned ({meta['total_rows']} total). "
        f"Duration: {format_duration(meta['duration_secs'])}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
