# Automated ERD Tool — Project Specifications

## Overview

A Python-based tool that connects to a SQL Server database, introspects the schema, and automatically generates Mermaid ERD diagrams. The output can be rendered in VS Code, a markdown viewer, or a lightweight web UI.

---

## Goals

- Automate the generation of ER diagrams directly from a live SQL Server database
- Keep documentation in sync with the real schema without manual effort
- Output clean, readable Mermaid syntax that can be embedded in markdown or rendered in a browser

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| DB Driver | pyodbc |
| Diagram Format | Mermaid (erDiagram) |
| Optional Web UI | Flask + mermaid.js |
| Config Management | python-dotenv |

---

## Project Structure

```
erd-tool/
├── main.py               # Entry point
├── db/
│   └── query.py          # SQL queries and DB connection
├── generator/
│   └── mermaid.py        # Mermaid diagram builder
├── output/
│   └── erd.md            # Generated ERD output
├── web/                  # Optional Flask UI
│   ├── app.py
│   └── templates/
│       └── index.html
├── .env                  # DB connection config (not committed)
├── .env.example          # Example env file for reference
├── requirements.txt
└── README.md
```

---

## Configuration

Store connection settings in a `.env` file:

```
DB_SERVER=your_server_name
DB_NAME=your_database_name
DB_TRUSTED_CONNECTION=yes
# Optional for SQL auth:
# DB_USERNAME=your_username
# DB_PASSWORD=your_password
```

---

## Modules

### `db/query.py`
- Establish connection using `pyodbc` and settings from `.env`
- Execute the schema introspection query
- Return raw rows to the generator
- Support optional filtering by schema name or table name

**Key SQL sources:**
- `sys.tables` — table names
- `sys.columns` — column names, types, nullability
- `sys.types` — data type names
- `sys.foreign_keys` + `sys.foreign_key_columns` — FK relationships
- `sys.index_columns` + `sys.indexes` — primary key detection

---

### `generator/mermaid.py`
- Accept structured table/column/FK data
- Build `erDiagram` Mermaid syntax
- Handle edge cases:
  - Tables with no foreign keys
  - Composite foreign keys
  - Self-referencing tables
- Return diagram as a string
- Wrap output in a markdown fenced code block

**Mermaid relationship notation to use:**

| Relationship | Notation |
|---|---|
| One to many | `||--o{` |
| One to one | `||--||` |
| Zero or one to many | `|o--o{` |

---

### `main.py`
- Parse CLI arguments (optional filters, output path)
- Orchestrate DB query → diagram generation → file write
- Print success message with output file path

**CLI usage example:**
```bash
# Generate ERD for entire database
python main.py

# Filter to a specific schema
python main.py --schema dbo

# Filter to specific tables
python main.py --tables Orders,Customers,Products

# Custom output path
python main.py --output ./docs/erd.md
```

---

### `web/app.py` *(Optional)*
- Simple Flask app with a single route
- Renders the generated Mermaid diagram in the browser using mermaid.js CDN
- Includes a "Regenerate" button that re-runs the query and refreshes the diagram

---

## Output Format

The tool writes a `.md` file containing a fenced Mermaid code block:

~~~
```mermaid
erDiagram
    Customers {
        int CustomerID PK
        varchar Name
        varchar Email nullable
    }
    Orders {
        int OrderID PK
        int CustomerID FK
        datetime OrderDate nullable
    }
    Customers ||--o{ Orders : "CustomerID"
```
~~~

---

## Features

### MVP
- [x] Connect to SQL Server via pyodbc
- [x] Introspect all tables and columns
- [x] Detect foreign key relationships
- [x] Generate valid Mermaid erDiagram syntax
- [x] Write output to a `.md` file

### Phase 2
- [ ] Detect and label primary keys
- [ ] CLI argument support (filter by schema/table)
- [ ] Support SQL Server authentication (in addition to Windows auth)
- [ ] Handle composite foreign keys

### Phase 3
- [ ] Flask web UI with live rendering
- [ ] "Regenerate" button in UI
- [ ] Ability to filter/focus on a subset of tables in the UI
- [ ] Export to PNG via mermaid CLI (`mmdc`)

---

## Dependencies

```
pyodbc
python-dotenv
flask          # optional, for web UI
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Notes

- The tool is read-only — it never modifies the database
- Large databases with hundreds of tables may produce unwieldy diagrams; filtering by schema or table is recommended in those cases
- Mermaid diagrams can be previewed directly in VS Code using the **Markdown Preview Mermaid Support** extension
- For PNG export, install the Mermaid CLI: `npm install -g @mermaid-js/mermaid-cli`