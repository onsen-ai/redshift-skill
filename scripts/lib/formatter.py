"""Shared output formatting — txt, csv, json."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


def format_output(columns, rows, fmt="txt", save_path=None, stream=sys.stdout):
    """Format and output query results.

    Args:
        columns: list of column name strings
        rows: list of lists
        fmt: "txt", "csv", or "json"
        save_path: optional file path to save output
        stream: output stream (default: stdout)
    """
    if not columns and not rows:
        print("No results.", file=sys.stderr)
        return

    # Auto-save large results
    if len(rows) > 50 and not save_path:
        export_dir = Path.home() / "redshift-exports"
        export_dir.mkdir(exist_ok=True)
        ext = {"txt": "txt", "csv": "csv", "json": "json"}[fmt]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = str(export_dir / f"query-{timestamp}.{ext}")
        # Show first 20 rows inline, save full results
        _write_output(columns, rows[:20], fmt, stream)
        print(f"\n... showing 20 of {len(rows)} rows", file=sys.stderr)
        _write_to_file(columns, rows, fmt, save_path)
        print(f"Full results saved to: {save_path}", file=sys.stderr)
        return

    if save_path:
        _write_to_file(columns, rows, fmt, save_path)
        print(f"Saved {len(rows)} rows to: {save_path}", file=sys.stderr)
    else:
        _write_output(columns, rows, fmt, stream)


def _write_output(columns, rows, fmt, stream):
    """Write formatted output to a stream."""
    if fmt == "txt":
        _format_txt(columns, rows, stream)
    elif fmt == "csv":
        _format_csv(columns, rows, stream)
    elif fmt == "json":
        _format_json(columns, rows, stream)


def _write_to_file(columns, rows, fmt, path):
    """Write formatted output to a file."""
    with open(path, "w", newline="") as f:
        _write_output(columns, rows, fmt, f)


def _format_txt(columns, rows, stream):
    """Aligned table output."""
    # Calculate column widths
    str_rows = [[_to_str(v) for v in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in str_rows:
        for i, val in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(val))

    # Header
    header = "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    separator = "  ".join("-" * w for w in widths)
    stream.write(header + "\n")
    stream.write(separator + "\n")

    # Rows
    for row in str_rows:
        line = "  ".join(
            (row[i] if i < len(row) else "").ljust(widths[i])
            for i in range(len(columns))
        )
        stream.write(line + "\n")


def _format_csv(columns, rows, stream):
    """CSV output with header."""
    writer = csv.writer(stream)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_to_str(v) for v in row])


def _format_json(columns, rows, stream):
    """JSON array of objects."""
    result = []
    for row in rows:
        obj = {}
        for i, col in enumerate(columns):
            obj[col] = row[i] if i < len(row) else None
        result.append(obj)
    stream.write(json.dumps(result, indent=2, default=str) + "\n")


def _to_str(value):
    """Convert a value to string for display."""
    if value is None:
        return "NULL"
    return str(value)


def format_duration(secs):
    """Format seconds into a human-readable string like '1m 23s' or '5s'."""
    if secs < 1:
        return f"{round(secs * 1000)}ms"
    secs = round(secs)
    if secs >= 60:
        m, s = divmod(secs, 60)
        return f"{m}m {s}s"
    return f"{secs}s"
