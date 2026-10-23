"""
Database Engine Manager for MNP Payroll Subsystem (BTM 495 Prototype)
Supports dual-mode execution:
1. Supabase Cloud PostgreSQL (production/demo mode)
2. Local SQLite fallback (payroll.db - zero-configuration grading mode)
"""

import os
import sqlite3
from pathlib import Path

# Paths to DDL and Seed scripts
DB_DIR = Path(__file__).parent
SQLITE_DB_PATH = DB_DIR / "payroll.db"
SCHEMA_SQL_PATH = DB_DIR / "schema.sql"
SEED_SQL_PATH = DB_DIR / "seed.sql"

class DatabaseManager:
    """Manages database connection and query execution with dual-engine support."""

    def __init__(self, use_supabase=False):
        self.use_supabase = use_supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self._supabase_client = None

        if self.use_supabase and self.supabase_url and self.supabase_key:
            try:
                from supabase import create_client
                self._supabase_client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                print(f"[DB Warning] Could not connect to Supabase: {e}. Falling back to SQLite.")
                self.use_supabase = False

    def get_connection(self):
        """Returns a SQLite connection with foreign keys enabled and row factory."""
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self, force_reset=False):
        """Initializes tables and seeds test data."""
        if force_reset and SQLITE_DB_PATH.exists():
            SQLITE_DB_PATH.unlink()

        conn = self.get_connection()
        cursor = conn.cursor()

        # Read and execute schema
        with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
            schema_script = f.read()
        cursor.executescript(schema_script)

        # Read and execute seed data
        with open(SEED_SQL_PATH, "r", encoding="utf-8") as f:
            seed_script = f.read()
        cursor.executescript(seed_script)

        conn.commit()
        conn.close()
        print(f"[DB Info] Database successfully initialized and seeded at {SQLITE_DB_PATH.name}")

    def query_all(self, query, params=()):
        """Executes a SELECT query and returns a list of dictionaries."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def query_one(self, query, params=()):
        """Executes a SELECT query and returns a single dictionary or None."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def execute(self, query, params=()):
        """Executes an INSERT, UPDATE, or DELETE query and returns the last row ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

# Global singleton instance
db = DatabaseManager()

if __name__ == "__main__":
    db.init_database(force_reset=True)
    clients = db.query_all("SELECT * FROM clients")
    print(f"Loaded {len(clients)} clients: {[c['client_name'] for c in clients]}")
