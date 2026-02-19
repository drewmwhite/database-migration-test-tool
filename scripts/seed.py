"""
Seed script for the dev SQL Server database.

Creates a small dev_db with three example tables and populates them
with sample rows. Safe to re-run — all operations are idempotent.

Usage:
    python scripts/seed.py

Prerequisites:
    pip install pyodbc python-dotenv
    Copy .env.example to .env and adjust values if needed.
"""

import os
import sys
import time

import pyodbc
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

SERVER = os.getenv("DB_SERVER", "localhost,1433")
DB_NAME = os.getenv("DB_NAME", "dev_db")
USER = os.getenv("DB_USER", "sa")
PASSWORD = os.getenv("DB_PASSWORD", "")

DRIVER = "ODBC Driver 18 for SQL Server"


def build_conn_str(database="master"):
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        f"UID={USER};"
        f"PWD={PASSWORD};"
        "TrustServerCertificate=yes;"
    )


def ensure_database(conn):
    conn.autocommit = True
    cursor = conn.cursor()
    for attempt in range(1, 6):
        try:
            cursor.execute(
                f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{DB_NAME}') "
                f"CREATE DATABASE [{DB_NAME}];"
            )
            break
        except pyodbc.Error as exc:
            # Error 1807: SQL Server couldn't lock the model database — it's
            # still initialising. Wait and retry.
            if "1807" in str(exc) and attempt < 5:
                print(f"  SQL Server still starting up, retrying in 3s (attempt {attempt}/5)...")
                time.sleep(3)
            else:
                raise
    cursor.close()
    print(f"Database '{DB_NAME}' ready.")


DDL = """
IF OBJECT_ID('dbo.tags', 'U') IS NULL
    CREATE TABLE dbo.tags (
        id       INT          NOT NULL IDENTITY(1,1) PRIMARY KEY,
        item_id  INT          NOT NULL,
        label    NVARCHAR(100) NOT NULL
    );

IF OBJECT_ID('dbo.items', 'U') IS NULL
    CREATE TABLE dbo.items (
        id           INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        category_id  INT           NOT NULL,
        name         NVARCHAR(200) NOT NULL,
        description  NVARCHAR(MAX) NULL,
        created_at   DATETIME2     NOT NULL DEFAULT GETDATE()
    );

IF OBJECT_ID('dbo.categories', 'U') IS NULL
    CREATE TABLE dbo.categories (
        id          INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        name        NVARCHAR(100) NOT NULL,
        created_at  DATETIME2     NOT NULL DEFAULT GETDATE()
    );

IF OBJECT_ID('dbo.tags', 'U') IS NOT NULL
AND OBJECT_ID('dbo.items', 'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_tags_items'
)
    ALTER TABLE dbo.tags
        ADD CONSTRAINT FK_tags_items FOREIGN KEY (item_id) REFERENCES dbo.items(id);

IF OBJECT_ID('dbo.items', 'U') IS NOT NULL
AND OBJECT_ID('dbo.categories', 'U') IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_items_categories'
)
    ALTER TABLE dbo.items
        ADD CONSTRAINT FK_items_categories FOREIGN KEY (category_id) REFERENCES dbo.categories(id);
"""

CATEGORIES = [
    ("Electronics",),
    ("Books",),
    ("Clothing",),
]

ITEMS = [
    # (category_name, item_name, description)
    ("Electronics", "Wireless Keyboard", "Compact Bluetooth keyboard"),
    ("Electronics", "USB-C Hub", "7-in-1 multiport adapter"),
    ("Books", "Clean Code", "Robert C. Martin — software craftsmanship"),
    ("Books", "The Pragmatic Programmer", "Hunt & Thomas — career guide for developers"),
    ("Clothing", "Merino Wool Socks", "Warm and breathable, pack of 3"),
]

TAGS = [
    # (item_name, label)
    ("Wireless Keyboard", "peripheral"),
    ("Wireless Keyboard", "bluetooth"),
    ("USB-C Hub", "peripheral"),
    ("USB-C Hub", "connectivity"),
    ("Clean Code", "programming"),
    ("Clean Code", "must-read"),
    ("The Pragmatic Programmer", "programming"),
    ("Merino Wool Socks", "outdoor"),
]


def seed(conn):
    conn.autocommit = False
    cursor = conn.cursor()

    # Create tables + FK constraints
    for statement in DDL.strip().split("\n\n"):
        cursor.execute(statement)
    print("Tables ready.")

    # Categories
    inserted_categories = 0
    for (name,) in CATEGORIES:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.categories WHERE name = ?) "
            "INSERT INTO dbo.categories (name) VALUES (?);",
            name, name,
        )
        inserted_categories += cursor.rowcount
    print(f"  categories: {inserted_categories} row(s) inserted.")

    # Items — look up category_id by name
    inserted_items = 0
    for cat_name, item_name, description in ITEMS:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.items WHERE name = ?) "
            "INSERT INTO dbo.items (category_id, name, description) "
            "SELECT id, ?, ? FROM dbo.categories WHERE name = ?;",
            item_name, item_name, description, cat_name,
        )
        inserted_items += cursor.rowcount
    print(f"  items: {inserted_items} row(s) inserted.")

    # Tags — look up item_id by name
    inserted_tags = 0
    for item_name, label in TAGS:
        cursor.execute(
            "IF NOT EXISTS (SELECT 1 FROM dbo.tags t "
            "JOIN dbo.items i ON i.id = t.item_id "
            "WHERE i.name = ? AND t.label = ?) "
            "INSERT INTO dbo.tags (item_id, label) "
            "SELECT id, ? FROM dbo.items WHERE name = ?;",
            item_name, label, label, item_name,
        )
        inserted_tags += cursor.rowcount
    print(f"  tags: {inserted_tags} row(s) inserted.")

    conn.commit()
    cursor.close()


def main():
    try:
        # Step 1: connect to master to create the database
        with pyodbc.connect(build_conn_str("master")) as conn:
            ensure_database(conn)

        # Step 2: connect to the target database and seed
        with pyodbc.connect(build_conn_str(DB_NAME)) as conn:
            seed(conn)

        print("Seeding complete.")
    except pyodbc.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
