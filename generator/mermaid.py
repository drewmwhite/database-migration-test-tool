"""
Mermaid erDiagram generator.

Accepts structured table and foreign key data from the query layer and
produces a fenced Mermaid code block ready to embed in a markdown file.
"""

from db.query import ColumnInfo, ForeignKeyInfo, TableInfo


def _column_line(col: ColumnInfo) -> str:
    """
    Build a single Mermaid attribute line for a column.

    Mermaid erDiagram attribute syntax: type name [PK|FK|UK] ["comment"]
    'nullable' is not a valid key token so it is emitted as a quoted comment.
    """
    parts = [col.data_type, col.name]
    if col.is_primary_key:
        parts.append("PK")
    if col.is_foreign_key:
        parts.append("FK")
    if col.is_nullable:
        parts.append('"nullable"')
    return "        " + " ".join(parts)


def _relationship_notation(fk: ForeignKeyInfo) -> str:
    """
    Return the Mermaid relationship notation string.

    is_unique=True  → one-to-one  (||--||)
    is_unique=False → one-to-many (||--o{)  [default]
    """
    if fk.is_unique:
        return "||--||"
    return "||--o{"


def _fk_label(fk: ForeignKeyInfo) -> str:
    """Return the relationship label — comma-joined source column names."""
    return ", ".join(fk.from_columns)


def build_diagram(
    tables: dict[str, TableInfo],
    foreign_keys: list[ForeignKeyInfo],
) -> str:
    """
    Build a Mermaid erDiagram as a fenced markdown code block.

    Args:
        tables:       Mapping of "schema.table" → TableInfo (from fetch_schema).
        foreign_keys: List of ForeignKeyInfo objects (from fetch_schema).

    Returns:
        A string containing the full fenced Mermaid block, e.g.:
            ```mermaid
            erDiagram
                ...
            ```
    """
    lines = ["```mermaid", "erDiagram"]

    # Entity blocks — sorted for deterministic output
    for key in sorted(tables.keys()):
        table = tables[key]
        lines.append(f"    {table.name} {{")
        for col in table.columns:
            lines.append(_column_line(col))
        lines.append("    }")

    # Blank line between entity blocks and relationship lines
    lines.append("")

    # Relationship lines: parent ||--o{ child : "label"
    for fk in foreign_keys:
        notation = _relationship_notation(fk)
        label = _fk_label(fk)
        lines.append(f"    {fk.to_table} {notation} {fk.from_table} : \"{label}\"")

    lines.append("```")
    return "\n".join(lines)
