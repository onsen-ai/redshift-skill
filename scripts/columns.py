#!/usr/bin/env python3
"""List columns for a table."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query
from lib.formatter import format_output

# svv_columns covers tables, views, AND late-binding views
SQL_TEMPLATE = """
SELECT
    s.ordinal_position AS pos,
    s.column_name,
    UPPER(s.data_type) AS data_type,
    s.character_maximum_length AS max_len,
    s.numeric_precision AS num_prec,
    s.is_nullable,
    s.column_default,
    NVL(format_encoding(a.attencodingtype::integer), '') AS encoding,
    NVL(a.attisdistkey, false) AS distkey,
    NVL(a.attsortkeyord, 0) AS sortkey
FROM svv_columns s
LEFT JOIN pg_namespace n ON n.nspname = s.table_schema
LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = s.table_name
LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = s.column_name AND a.attnum > 0
WHERE s.table_schema = '{schema}'
  AND s.table_name = '{table}'
ORDER BY s.ordinal_position
"""


def main():
    parser = argparse.ArgumentParser(description="List columns for a Redshift table")
    add_connection_args(parser)
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table", required=True, help="Table name")
    args = parser.parse_args()

    config = resolve_config(args)
    sql = SQL_TEMPLATE.format(schema=args.schema, table=args.table)
    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=args.max_rows)
    format_output(columns, rows, fmt=args.format, save_path=args.save)
    print(f"{len(rows)} columns. Duration: {meta['duration_ms']}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
