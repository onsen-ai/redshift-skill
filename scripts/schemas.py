#!/usr/bin/env python3
"""List database schemas."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output, format_duration

SQL = """
SELECT nspname AS schema_name, usename AS owner
FROM pg_namespace n
JOIN pg_user u ON n.nspowner = u.usesysid
WHERE nspname NOT IN ('pg_catalog','information_schema','pg_toast','pg_internal','pg_automv')
  AND nspname NOT LIKE 'pg_temp_%'
ORDER BY schema_name
"""


def main():
    parser = argparse.ArgumentParser(description="List Redshift schemas")
    add_connection_args(parser)
    args = parser.parse_args()

    config = resolve_config(args)
    columns, rows, meta = execute_query(SQL, config, timeout=args.timeout, max_rows=args.max_rows)
    format_output(columns, rows, fmt=args.format, save_path=args.save)
    print(f"{len(rows)} schemas. Duration: {format_duration(meta['duration_secs'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
