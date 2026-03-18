#!/usr/bin/env python3
"""Generate DDL for various Redshift object types."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import add_connection_args, resolve_config, execute_query, load_sql
from lib.formatter import format_output

DDL_TYPES = {
    "table": {
        "sql_file": "generate_tbl_ddl",
        "filter_key": "schema_filter",
        "build_filter": lambda s, n: (
            f"WHERE schemaname = '{s}' AND tablename = '{n}'" if s and n
            else f"WHERE schemaname = '{s}'" if s
            else ""
        ),
        "ddl_col": "ddl",
    },
    "view": {
        "sql_file": "generate_view_ddl",
        "filter_key": "schema_filter",
        "build_filter": lambda s, n: (
            f"AND n.nspname = '{s}' AND c.relname = '{n}'" if s and n
            else f"AND n.nspname = '{s}'" if s
            else ""
        ),
        "ddl_col": "ddl",
    },
    "schema": {
        "sql_file": "generate_schema_ddl",
        "filter_key": "schema_filter",
        "build_filter": lambda s, n: (
            f"AND nspname = '{n}'" if n
            else ""
        ),
        "ddl_col": "ddl",
    },
    "database": {
        "sql_file": "generate_database_ddl",
        "filter_key": "database_filter",
        "build_filter": lambda s, n: (
            f"AND datname = '{n}'" if n
            else ""
        ),
        "ddl_col": "ddl",
    },
    "udf": {
        "sql_file": "generate_udf_ddl",
        "filter_key": "schema_filter",
        "build_filter": lambda s, n: (
            f"WHERE schemaname = '{s}' AND udfname = '{n}'" if s and n
            else f"WHERE schemaname = '{s}'" if s
            else ""
        ),
        "ddl_col": "ddl",
    },
    "external": {
        "sql_file": "generate_external_tbl_ddl",
        "filter_key": "schema_filter",
        "build_filter": lambda s, n: (
            f"AND schemaname = '{s}' AND tablename = '{n}'" if s and n
            else f"AND schemaname = '{s}'" if s
            else ""
        ),
        "ddl_col": "ddl",
    },
    "group": {
        "sql_file": "generate_group_ddl",
        "filter_key": "group_filter",
        "build_filter": lambda s, n: (
            f"WHERE groname = '{n}'" if n
            else ""
        ),
        "ddl_col": "ddl",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Generate DDL for Redshift objects")
    add_connection_args(parser)
    parser.add_argument("--type", choices=list(DDL_TYPES.keys()), default="table",
                        help="Object type (default: table)")
    parser.add_argument("--schema", help="Schema name (for table, view, udf, external)")
    parser.add_argument("--name", help="Object name")
    args = parser.parse_args()

    config = resolve_config(args)
    ddl_type = DDL_TYPES[args.type]

    filter_clause = ddl_type["build_filter"](args.schema, args.name)
    sql = load_sql(ddl_type["sql_file"], **{ddl_type["filter_key"]: filter_clause})

    columns, rows, meta = execute_query(sql, config, timeout=args.timeout, max_rows=10000)

    # DDL output: concatenate the ddl column values
    if rows:
        ddl_idx = columns.index(ddl_type["ddl_col"]) if ddl_type["ddl_col"] in columns else -1
        if ddl_idx >= 0:
            for row in rows:
                val = row[ddl_idx]
                if val is not None:
                    print(val)
        else:
            format_output(columns, rows, fmt=args.format, save_path=args.save)
    else:
        print("No DDL found for the specified object.", file=sys.stderr)

    print(f"\nDuration: {meta['duration_ms']}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
