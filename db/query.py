"""
Database connection and schema introspection for the ERD generation tool.

Queries SQL Server system catalog views to retrieve table, column, and
foreign key information, then assembles the results into structured
dataclasses for consumption by the Mermaid generator.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import pyodbc
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

DRIVER = "ODBC Driver 18 for SQL Server"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool = False  # back-filled after FK query


@dataclass
class ForeignKeyInfo:
    constraint_name: str
    from_table: str
    from_schema: str
    from_columns: list[str]
    to_table: str
    to_schema: str
    to_columns: list[str]
    is_unique: bool  # True → one-to-one relationship


@dataclass
class TableInfo:
    name: str
    schema: str
    columns: list[ColumnInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def get_connection() -> pyodbc.Connection:
    server = os.getenv("DB_SERVER", "localhost,1433")
    database = os.getenv("DB_NAME", "dev_db")
    username = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD", "")
    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


# ---------------------------------------------------------------------------
# SQL queries
# ---------------------------------------------------------------------------

_TABLE_SQL = """
SELECT
    s.name  AS schema_name,
    t.name  AS table_name
FROM
    sys.tables  t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
WHERE
    t.is_ms_shipped = 0
    AND (? IS NULL OR s.name = ?)
ORDER BY
    s.name, t.name;
"""

_COLUMN_SQL = """
SELECT
    s.name                              AS schema_name,
    t.name                              AS table_name,
    c.name                              AS column_name,
    tp.name                             AS type_name,
    c.is_nullable                       AS is_nullable,
    CASE
        WHEN ic.column_id IS NOT NULL THEN 1
        ELSE 0
    END                                 AS is_primary_key
FROM
    sys.tables          t
    JOIN sys.schemas         s   ON s.schema_id  = t.schema_id
    JOIN sys.columns         c   ON c.object_id  = t.object_id
    JOIN sys.types           tp  ON tp.user_type_id = c.user_type_id
    LEFT JOIN sys.indexes    ix  ON ix.object_id = t.object_id
                                 AND ix.is_primary_key = 1
    LEFT JOIN sys.index_columns ic
                                 ON ic.object_id = ix.object_id
                                AND ic.index_id  = ix.index_id
                                AND ic.column_id = c.column_id
WHERE
    t.is_ms_shipped = 0
    AND (? IS NULL OR s.name = ?)
ORDER BY
    s.name, t.name, c.column_id;
"""

_FK_SQL = """
SELECT
    fk.name                         AS constraint_name,
    ps.name                         AS from_schema,
    pt.name                         AS from_table,
    fkc.constraint_column_id        AS key_ordinal,
    pc.name                         AS from_column,
    rs.name                         AS to_schema,
    rt.name                         AS to_table,
    rc.name                         AS to_column,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM   sys.indexes        ui
            JOIN   sys.index_columns  uic
                   ON  uic.object_id = ui.object_id
                   AND uic.index_id  = ui.index_id
            WHERE  ui.object_id  = fk.parent_object_id
              AND  ui.is_unique   = 1
              AND  uic.column_id  = fkc.parent_column_id
              AND  NOT EXISTS (
                      SELECT 1
                      FROM   sys.index_columns extra
                      WHERE  extra.object_id = ui.object_id
                        AND  extra.index_id  = ui.index_id
                        AND  extra.column_id NOT IN (
                               SELECT parent_column_id
                               FROM   sys.foreign_key_columns
                               WHERE  constraint_object_id = fk.object_id
                             )
                   )
        ) THEN 1
        ELSE 0
    END                             AS is_unique
FROM
    sys.foreign_keys             fk
    JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
    JOIN sys.tables              pt  ON pt.object_id = fk.parent_object_id
    JOIN sys.schemas             ps  ON ps.schema_id = pt.schema_id
    JOIN sys.columns             pc  ON pc.object_id = fk.parent_object_id
                                    AND pc.column_id = fkc.parent_column_id
    JOIN sys.tables              rt  ON rt.object_id = fk.referenced_object_id
    JOIN sys.schemas             rs  ON rs.schema_id = rt.schema_id
    JOIN sys.columns             rc  ON rc.object_id = fk.referenced_object_id
                                    AND rc.column_id = fkc.referenced_column_id
WHERE
    (? IS NULL OR ps.name = ?)
ORDER BY
    fk.name, fkc.constraint_column_id;
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_schema(
    schema_filter: Optional[str] = None,
    table_filter: Optional[list[str]] = None,
) -> tuple[dict[str, TableInfo], list[ForeignKeyInfo]]:
    """
    Introspect the database and return structured table and FK data.

    Args:
        schema_filter: Only include tables in this schema (e.g. "dbo").
                       Pass None to include all schemas.
        table_filter:  Only include tables whose name matches one of these
                       values (case-insensitive). Pass None for all tables.

    Returns:
        A tuple of (tables, foreign_keys) where:
          - tables maps "schema.table" keys to TableInfo objects
          - foreign_keys is a list of ForeignKeyInfo objects
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Step 1 — fetch table names
        cursor.execute(_TABLE_SQL, schema_filter, schema_filter)
        table_rows = cursor.fetchall()

        if table_filter:
            filter_set = {n.lower() for n in table_filter}
            table_rows = [r for r in table_rows if r.table_name.lower() in filter_set]

        tables: dict[str, TableInfo] = {
            f"{r.schema_name}.{r.table_name}": TableInfo(
                name=r.table_name, schema=r.schema_name
            )
            for r in table_rows
        }
        allowed_keys = set(tables.keys())

        # Step 2 — fetch columns and populate tables
        cursor.execute(_COLUMN_SQL, schema_filter, schema_filter)
        for row in cursor.fetchall():
            key = f"{row.schema_name}.{row.table_name}"
            if key not in tables:
                continue
            tables[key].columns.append(
                ColumnInfo(
                    name=row.column_name,
                    data_type=row.type_name,
                    is_nullable=bool(row.is_nullable),
                    is_primary_key=bool(row.is_primary_key),
                )
            )

        # Step 3 — fetch foreign keys, aggregate composite keys, back-fill FK flag
        cursor.execute(_FK_SQL, schema_filter, schema_filter)
        fk_map: dict[str, ForeignKeyInfo] = {}
        for row in cursor.fetchall():
            from_key = f"{row.from_schema}.{row.from_table}"
            to_key = f"{row.to_schema}.{row.to_table}"
            # Skip FKs where either endpoint falls outside the filtered table set
            if table_filter and (from_key not in allowed_keys or to_key not in allowed_keys):
                continue
            cname = row.constraint_name
            if cname not in fk_map:
                fk_map[cname] = ForeignKeyInfo(
                    constraint_name=cname,
                    from_table=row.from_table,
                    from_schema=row.from_schema,
                    from_columns=[],
                    to_table=row.to_table,
                    to_schema=row.to_schema,
                    to_columns=[],
                    is_unique=bool(row.is_unique),
                )
            fk_map[cname].from_columns.append(row.from_column)
            fk_map[cname].to_columns.append(row.to_column)

            # Back-fill is_foreign_key on the source column
            if from_key in tables:
                for col in tables[from_key].columns:
                    if col.name == row.from_column:
                        col.is_foreign_key = True

        return tables, list(fk_map.values())
    finally:
        conn.close()


if __name__ == "__main__":
    tables, fks = fetch_schema()
    print(f"Tables: {len(tables)}, Foreign keys: {len(fks)}")
    for key, t in sorted(tables.items()):
        print(f"  {key}: {[c.name for c in t.columns]}")
    for fk in fks:
        print(f"  FK {fk.constraint_name}: {fk.from_table}.{fk.from_columns} -> {fk.to_table}.{fk.to_columns}")
