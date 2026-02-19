# Seeding the Database

The seed script creates the development database and populates it with example data. It is intended as a starting point and will evolve alongside the schema.

## Prerequisites

- SQL Server running locally via Docker (see `run-sql-server-on-docker.md`)
- Python dependencies installed: `pip install pyodbc python-dotenv`
- A `.env` file at the project root (copy from `.env.example`)

## Running the Script

```bash
python scripts/seed.py
```

The script is idempotent — re-running it will not create duplicate rows or raise errors.

## What It Does

1. Connects to the server and creates the target database if it does not exist
2. Creates the example tables if they do not exist
3. Inserts sample rows, skipping any that are already present

## Configuration

Connection details are read from environment variables, with defaults pointing at the local Docker instance:

| Variable | Default |
|---|---|
| `DB_SERVER` | `localhost,1433` |
| `DB_NAME` | `dev_db` |
| `DB_USER` | `sa` |
| `DB_PASSWORD` | *(empty — set in `.env`)* |

## Modifying the Seed Data

Sample rows are defined as plain Python lists near the top of `scripts/seed.py`. To change what gets seeded, edit those lists — no SQL knowledge required.

Table definitions live in the `DDL` string in the same file. As the schema evolves, update or replace that block to match.
