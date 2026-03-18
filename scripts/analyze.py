#!/usr/bin/env python3
"""Local analytics on saved CSV/JSON files — no Redshift needed."""

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.formatter import format_output, _to_str


def load_data(filepath):
    """Load a CSV or JSON file into (columns, rows)."""
    path = Path(filepath)
    if path.suffix == ".json":
        with open(path) as f:
            data = json.load(f)
        if not data:
            return [], []
        columns = list(data[0].keys())
        rows = [[row.get(c) for c in columns] for row in data]
        return columns, rows
    else:
        # CSV or TXT (try CSV first)
        with open(path, newline="") as f:
            reader = csv.reader(f)
            columns = next(reader, [])
            rows = [row for row in reader]
        return columns, rows


def to_numeric(val):
    """Try to convert a value to float. Returns None if not numeric."""
    if val is None or val == "" or val == "NULL":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def filter_rows(columns, rows, expr):
    """Filter rows by a simple expression like 'column=value' or 'column>100'."""
    for op in [">=", "<=", "!=", "=", ">", "<"]:
        if op in expr:
            col_name, value = expr.split(op, 1)
            col_name = col_name.strip()
            value = value.strip()
            break
    else:
        print(f"ERROR: Invalid filter expression: {expr}", file=sys.stderr)
        print("  Use: column=value, column>100, column!=foo", file=sys.stderr)
        sys.exit(1)

    if col_name not in columns:
        print(f"ERROR: Column '{col_name}' not found. Available: {', '.join(columns)}", file=sys.stderr)
        sys.exit(1)

    col_idx = columns.index(col_name)
    num_value = to_numeric(value)

    def matches(row_val):
        num_row = to_numeric(row_val)
        if op == "=" or op == "==":
            return str(row_val) == value
        elif op == "!=":
            return str(row_val) != value
        elif num_row is not None and num_value is not None:
            if op == ">":
                return num_row > num_value
            elif op == "<":
                return num_row < num_value
            elif op == ">=":
                return num_row >= num_value
            elif op == "<=":
                return num_row <= num_value
        return False

    return [row for row in rows if col_idx < len(row) and matches(row[col_idx])]


def cmd_count(columns, rows):
    """Print row count."""
    print(f"{len(rows)} rows")


def cmd_describe(columns, rows):
    """Per-column descriptive statistics."""
    result_cols = ["column", "count", "nulls", "null%", "distinct", "type", "min", "max", "mean", "top_values"]
    result_rows = []

    for i, col in enumerate(columns):
        values = [row[i] if i < len(row) else None for row in rows]
        non_null = [v for v in values if v is not None and v != "" and v != "NULL"]
        numerics = [n for n in (to_numeric(v) for v in non_null) if n is not None]

        count = len(values)
        nulls = count - len(non_null)
        null_pct = f"{(nulls / count * 100):.1f}" if count > 0 else "0"
        distinct = len(set(str(v) for v in non_null))

        if len(numerics) == len(non_null) and numerics:
            col_type = "numeric"
            min_val = str(min(numerics))
            max_val = str(max(numerics))
            mean_val = f"{statistics.mean(numerics):.2f}"
            top = ""
        else:
            col_type = "string"
            min_val = str(min(non_null, key=str)) if non_null else ""
            max_val = str(max(non_null, key=str)) if non_null else ""
            mean_val = ""
            # Top 3 most common values
            counter = Counter(str(v) for v in non_null)
            top_items = counter.most_common(3)
            top = ", ".join(f"{v}({c})" for v, c in top_items)

        result_rows.append([col, str(count), str(nulls), null_pct, str(distinct),
                           col_type, min_val, max_val, mean_val, top])

    format_output(result_cols, result_rows, fmt="txt", no_save=True)


def cmd_aggregate(columns, rows, op, col_name):
    """Run an aggregate operation on a column."""
    if col_name not in columns:
        print(f"ERROR: Column '{col_name}' not found. Available: {', '.join(columns)}", file=sys.stderr)
        sys.exit(1)

    col_idx = columns.index(col_name)
    numerics = [n for n in (to_numeric(row[col_idx] if col_idx < len(row) else None) for row in rows) if n is not None]

    if not numerics:
        print(f"No numeric values in column '{col_name}'", file=sys.stderr)
        return

    if op == "sum":
        print(f"{col_name} SUM: {sum(numerics)}")
    elif op == "avg":
        print(f"{col_name} AVG: {statistics.mean(numerics):.4f}")
    elif op == "min":
        print(f"{col_name} MIN: {min(numerics)}")
    elif op == "max":
        print(f"{col_name} MAX: {max(numerics)}")
    elif op == "median":
        print(f"{col_name} MEDIAN: {statistics.median(numerics)}")

    print(f"  ({len(numerics)} numeric values, {len(rows) - len(numerics)} nulls/non-numeric)")


def cmd_group_by(columns, rows, group_col, agg_op=None, agg_col=None):
    """Group rows by a column with optional aggregation."""
    if group_col not in columns:
        print(f"ERROR: Column '{group_col}' not found.", file=sys.stderr)
        sys.exit(1)

    group_idx = columns.index(group_col)
    groups = {}
    for row in rows:
        key = str(row[group_idx]) if group_idx < len(row) else "NULL"
        groups.setdefault(key, []).append(row)

    if agg_op and agg_col:
        if agg_col not in columns:
            print(f"ERROR: Column '{agg_col}' not found.", file=sys.stderr)
            sys.exit(1)
        agg_idx = columns.index(agg_col)
        result_cols = [group_col, "count", f"{agg_op}({agg_col})"]
        result_rows = []
        for key in sorted(groups.keys()):
            grp_rows = groups[key]
            numerics = [n for n in (to_numeric(r[agg_idx] if agg_idx < len(r) else None) for r in grp_rows) if n is not None]
            if agg_op == "sum":
                agg_val = str(sum(numerics)) if numerics else "0"
            elif agg_op == "avg":
                agg_val = f"{statistics.mean(numerics):.4f}" if numerics else "N/A"
            elif agg_op == "min":
                agg_val = str(min(numerics)) if numerics else "N/A"
            elif agg_op == "max":
                agg_val = str(max(numerics)) if numerics else "N/A"
            else:
                agg_val = ""
            result_rows.append([key, str(len(grp_rows)), agg_val])
    else:
        result_cols = [group_col, "count"]
        result_rows = [[key, str(len(grp_rows))] for key, grp_rows in sorted(groups.items())]

    # Sort by count descending
    result_rows.sort(key=lambda r: int(r[1]), reverse=True)
    format_output(result_cols, result_rows, fmt="txt", no_save=True)


def cmd_hist(columns, rows, col_name, bins=20):
    """Print a text histogram for a column."""
    if col_name not in columns:
        print(f"ERROR: Column '{col_name}' not found.", file=sys.stderr)
        sys.exit(1)

    col_idx = columns.index(col_name)
    values = [row[col_idx] if col_idx < len(row) else None for row in rows]
    numerics = [n for n in (to_numeric(v) for v in values) if n is not None]

    if numerics:
        # Numeric histogram
        lo, hi = min(numerics), max(numerics)
        if lo == hi:
            print(f"{col_name}: all values = {lo} ({len(numerics)} rows)")
            return
        step = (hi - lo) / bins
        buckets = [0] * bins
        for n in numerics:
            idx = min(int((n - lo) / step), bins - 1)
            buckets[idx] += 1
        max_count = max(buckets)
        bar_width = 40
        for i, count in enumerate(buckets):
            low_edge = lo + i * step
            high_edge = lo + (i + 1) * step
            bar = "#" * int(count / max_count * bar_width) if max_count > 0 else ""
            print(f"  {low_edge:>12.2f} - {high_edge:<12.2f} | {bar} ({count})")
    else:
        # Categorical histogram
        counter = Counter(str(v) for v in values if v is not None and v != "" and v != "NULL")
        top = counter.most_common(bins)
        max_count = top[0][1] if top else 1
        bar_width = 40
        for val, count in top:
            bar = "#" * int(count / max_count * bar_width) if max_count > 0 else ""
            label = val[:30] + "..." if len(val) > 30 else val
            print(f"  {label:<35} | {bar} ({count})")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze saved CSV/JSON files locally — no Redshift needed",
        epilog="Examples:\n"
               "  analyze.py data.csv --describe\n"
               "  analyze.py data.csv --sum=revenue --filter='year=2024'\n"
               "  analyze.py data.csv --group-by=region --sum=sales\n"
               "  analyze.py data.csv --hist=price\n"
               "  analyze.py data.csv --sort=amount --desc --top=10",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to CSV or JSON file")
    parser.add_argument("--count", action="store_true", help="Print row count")
    parser.add_argument("--describe", action="store_true", help="Per-column descriptive statistics")
    parser.add_argument("--sum", dest="sum_col", help="Sum a numeric column")
    parser.add_argument("--avg", dest="avg_col", help="Average a numeric column")
    parser.add_argument("--min", dest="min_col", help="Min of a column")
    parser.add_argument("--max", dest="max_col", help="Max of a column")
    parser.add_argument("--median", dest="median_col", help="Median of a numeric column")
    parser.add_argument("--group-by", dest="group_by", help="Group by column")
    parser.add_argument("--filter", dest="filter_expr", help="Filter rows (e.g. 'column=value', 'col>100')")
    parser.add_argument("--sort", help="Sort by column")
    parser.add_argument("--desc", action="store_true", help="Sort descending")
    parser.add_argument("--top", type=int, help="Show top N rows")
    parser.add_argument("--hist", dest="hist_col", help="Text histogram of a column")
    parser.add_argument("--format", choices=["txt", "csv", "json"], default="txt",
                        help="Output format (default: txt)")

    args = parser.parse_args()
    columns, rows = load_data(args.file)

    if not columns:
        print("ERROR: No data found in file", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(rows)} rows, {len(columns)} columns from {args.file}", file=sys.stderr)

    # Apply filter first
    if args.filter_expr:
        rows = filter_rows(columns, rows, args.filter_expr)
        print(f"  After filter: {len(rows)} rows", file=sys.stderr)

    # Sort
    if args.sort:
        if args.sort not in columns:
            print(f"ERROR: Column '{args.sort}' not found.", file=sys.stderr)
            sys.exit(1)
        sort_idx = columns.index(args.sort)
        rows.sort(
            key=lambda r: (to_numeric(r[sort_idx]) if to_numeric(r[sort_idx]) is not None else float('-inf'))
            if sort_idx < len(r) else float('-inf'),
            reverse=args.desc,
        )

    # Top N
    if args.top:
        rows = rows[:args.top]

    # Execute commands
    ran_something = False

    if args.count:
        cmd_count(columns, rows)
        ran_something = True

    if args.describe:
        cmd_describe(columns, rows)
        ran_something = True

    for op, col in [("sum", args.sum_col), ("avg", args.avg_col),
                     ("min", args.min_col), ("max", args.max_col),
                     ("median", args.median_col)]:
        if col:
            cmd_aggregate(columns, rows, op, col)
            ran_something = True

    if args.group_by:
        agg_op = None
        agg_col = None
        for op, col in [("sum", args.sum_col), ("avg", args.avg_col),
                         ("min", args.min_col), ("max", args.max_col)]:
            if col:
                agg_op, agg_col = op, col
                break
        cmd_group_by(columns, rows, args.group_by, agg_op, agg_col)
        ran_something = True

    if args.hist_col:
        cmd_hist(columns, rows, args.hist_col)
        ran_something = True

    # If only filter/sort/top were used without a specific command, show the data
    if not ran_something:
        format_output(columns, rows, fmt=args.format, no_save=True)


if __name__ == "__main__":
    main()
