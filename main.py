"""
ERD generation tool — entry point.

Connects to a SQL Server database, introspects the schema, and writes a
Mermaid erDiagram to a markdown file.

Usage:
    python main.py
    python main.py --schema dbo
    python main.py --tables Orders,Customers,Products
    python main.py --output ./docs/erd.md
    python main.py --schema dbo --tables items,tags --output ./docs/erd.md
"""

import argparse
import os
import sys

from db.query import fetch_schema
from generator.mermaid import build_diagram

DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "output", "erd.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Mermaid ERD diagram from a SQL Server database."
    )
    parser.add_argument(
        "--schema",
        metavar="SCHEMA",
        default=None,
        help="Filter to a single schema (e.g. dbo). Defaults to all schemas.",
    )
    parser.add_argument(
        "--tables",
        metavar="TABLE1,TABLE2,...",
        default=None,
        help="Comma-separated table names to include. Defaults to all tables.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=DEFAULT_OUTPUT,
        help=f"Output file path. Defaults to {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    table_filter = (
        [t.strip() for t in args.tables.split(",") if t.strip()]
        if args.tables
        else None
    )

    print("Connecting to database and introspecting schema...")
    try:
        tables, foreign_keys = fetch_schema(
            schema_filter=args.schema,
            table_filter=table_filter,
        )
    except Exception as exc:
        print(f"Error fetching schema: {exc}", file=sys.stderr)
        sys.exit(1)

    if not tables:
        print("No tables found matching the specified filters.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(tables)} table(s), {len(foreign_keys)} foreign key(s).")

    diagram = build_diagram(tables, foreign_keys)

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(diagram)
        fh.write("\n")

    print(f"ERD written to: {output_path}")


if __name__ == "__main__":
    main()
