"""Shared Redshift Data API client — config, args, execute/poll/fetch, read-only guard."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CONFIG_DIR = Path.home() / ".redshift-skill"
CONFIG_FILE = CONFIG_DIR / "config.json"
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# --- Config ---

def load_config():
    """Load saved config from ~/.redshift-skill/config.json."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save config to ~/.redshift-skill/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def add_connection_args(parser):
    """Add standard connection args to an argparse parser."""
    parser.add_argument("--profile", help="AWS CLI profile")
    parser.add_argument("--cluster", help="Redshift cluster identifier")
    parser.add_argument("--database", help="Database name")
    parser.add_argument("--db-user", dest="db_user", help="Database user")
    parser.add_argument("--format", choices=["txt", "csv", "json"], default="txt",
                        help="Output format (default: txt)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Max query wait time in seconds (default: 120)")
    parser.add_argument("--max-rows", dest="max_rows", type=int, default=1000,
                        help="Max rows to fetch (default: 1000)")
    parser.add_argument("--save", help="Save output to file path")


def resolve_config(args):
    """Merge saved config with CLI args (CLI wins)."""
    config = load_config()
    if args.profile:
        config["profile"] = args.profile
    if args.cluster:
        config["cluster"] = args.cluster
    if args.database:
        config["database"] = args.database
    if args.db_user:
        config["db_user"] = args.db_user

    missing = []
    for key in ("cluster", "database", "db_user"):
        if not config.get(key):
            missing.append(key)

    if missing:
        print(f"ERROR: Missing connection parameters: {', '.join(missing)}", file=sys.stderr)
        print(f"Run setup first: python {Path(__file__).resolve().parent.parent / 'setup.py'}", file=sys.stderr)
        sys.exit(1)

    return config


# --- Read-only guard ---

ALLOWED_KEYWORDS = {"SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN", "SET"}

def validate_sql(sql):
    """Validate that SQL is read-only. Raises ValueError if not."""
    # Strip line comments
    clean = re.sub(r"--[^\n]*", "", sql)
    # Strip block comments
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
    # Collapse whitespace
    clean = clean.strip()

    if not clean:
        raise ValueError("Empty SQL statement")

    first_keyword = clean.split()[0].upper().rstrip("(")

    if first_keyword not in ALLOWED_KEYWORDS:
        raise ValueError(
            f"Blocked statement type: {first_keyword}. "
            f"Only read-only queries are allowed ({', '.join(sorted(ALLOWED_KEYWORDS))})"
        )

    # Reject multi-statement
    if re.search(r";\s*[A-Za-z]", clean):
        raise ValueError("Multi-statement queries are not allowed")


# --- SQL loading ---

def load_sql(name, **placeholders):
    """Load a bundled SQL file and substitute placeholders."""
    sql_file = SQL_DIR / f"{name}.sql"
    if not sql_file.exists():
        raise FileNotFoundError(f"Bundled SQL not found: {sql_file}")
    sql = sql_file.read_text()
    for key, value in placeholders.items():
        sql = sql.replace(f"{{{key}}}", value)
    return sql


# --- AWS CLI execution ---

def _run_aws(args, config):
    """Run an AWS CLI command and return parsed JSON."""
    cmd = ["aws"] + args + ["--output", "json"]
    if config.get("profile"):
        cmd += ["--profile", config["profile"]]
    if config.get("region"):
        cmd += ["--region", config["region"]]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error = result.stderr.strip()
        raise RuntimeError(f"AWS CLI error: {error}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def execute_query(sql, config, timeout=120, max_rows=1000):
    """Execute a read-only query via Redshift Data API.

    Returns (columns, rows, metadata) where:
      - columns: list of column name strings
      - rows: list of lists (each inner list is one row)
      - metadata: dict with 'duration_secs', 'total_rows'
    """
    validate_sql(sql)

    # Execute
    exec_result = _run_aws([
        "redshift-data", "execute-statement",
        "--cluster-identifier", config["cluster"],
        "--database", config["database"],
        "--db-user", config["db_user"],
        "--sql", sql,
    ], config)

    stmt_id = exec_result.get("Id")
    if not stmt_id:
        raise RuntimeError(f"Failed to submit query: {exec_result}")

    # Poll with adaptive backoff
    elapsed = 0
    interval = 1
    while True:
        status_json = _run_aws([
            "redshift-data", "describe-statement",
            "--id", stmt_id,
        ], config)

        status = status_json.get("Status")

        if status == "FINISHED":
            break
        elif status in ("FAILED", "ABORTED"):
            error = status_json.get("Error", "Unknown error")
            raise RuntimeError(f"Query {status}: {error}")
        elif status in ("SUBMITTED", "PICKED", "STARTED"):
            time.sleep(interval)
            elapsed += interval
            if elapsed >= 5:
                interval = 2
            if elapsed >= timeout:
                raise RuntimeError(f"Query timed out after {timeout}s (status: {status})")
        else:
            raise RuntimeError(f"Unexpected query status: {status}")

    duration_ns = status_json.get("Duration", 0)
    total_rows = status_json.get("ResultRows", 0)
    has_results = status_json.get("HasResultSet", False)

    if not has_results:
        return [], [], {"duration_secs": duration_ns / 1_000_000_000, "total_rows": 0}

    # Fetch results with pagination
    all_records = []
    columns = []
    next_token = None

    while True:
        fetch_args = ["redshift-data", "get-statement-result", "--id", stmt_id]
        if next_token:
            fetch_args += ["--next-token", next_token]

        result = _run_aws(fetch_args, config)

        if not columns:
            columns = [col["name"] for col in result.get("ColumnMetadata", [])]

        all_records.extend(result.get("Records", []))
        next_token = result.get("NextToken")

        if not next_token or len(all_records) >= max_rows:
            break

    # Trim to max_rows
    all_records = all_records[:max_rows]

    # Convert typed cells to Python values
    rows = []
    for record in all_records:
        row = []
        for cell in record:
            if cell.get("isNull"):
                row.append(None)
            elif "stringValue" in cell:
                row.append(cell["stringValue"])
            elif "longValue" in cell:
                row.append(cell["longValue"])
            elif "doubleValue" in cell:
                row.append(cell["doubleValue"])
            elif "booleanValue" in cell:
                row.append(cell["booleanValue"])
            elif "blobValue" in cell:
                row.append(cell["blobValue"])
            else:
                row.append(None)
        rows.append(row)

    metadata = {
        "duration_secs": duration_ns / 1_000_000_000,
        "total_rows": total_rows,
    }

    return columns, rows, metadata
