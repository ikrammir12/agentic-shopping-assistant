
import json
import sqlite3
from pathlib import Path

from app.database.connection import get_connection


# Save the report in the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FILE = PROJECT_ROOT / "database_report.json"

# Columns containing sensitive information will not be exported.
SENSITIVE_WORDS = (
    "password",
    "token",
    "secret",
    "api_key",
    "credential",
    "email",
    "phone",
)


def make_safe_value(column_name, value):
    """Hide sensitive values before exporting database records."""
    column = column_name.lower()

    if any(word in column for word in SENSITIVE_WORDS):
        return "[REDACTED]"

    if isinstance(value, bytes):
        return f"[BINARY DATA: {len(value)} bytes]"

    return value


def inspect_database():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Find all application tables.
        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)

        table_names = [row[0] for row in cursor.fetchall()]

        report = {
            "database_report": "Blink AI SQLite inspection",
            "tables": {},
        }

        for table_name in table_names:

            # Get table structure.
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns_info = cursor.fetchall()

            columns = [
                {
                    "name": column[1],
                    "type": column[2],
                    "not_null": bool(column[3]),
                    "primary_key": bool(column[5]),
                }
                for column in columns_info
            ]

            # Read every record from this table.
            cursor.execute(f'SELECT * FROM "{table_name}"')
            records = cursor.fetchall()

            column_names = [column[1] for column in columns_info]

            rows = []
            for record in records:
                row = {
                    column: make_safe_value(column, value)
                    for column, value in zip(column_names, record)
                }
                rows.append(row)

            report["tables"][table_name] = {
                "columns": columns,
                "total_records": len(rows),
                "records": rows,
            }

        OUTPUT_FILE.write_text(
            json.dumps(report, indent=4, default=str),
            encoding="utf-8",
        )

        print("\nDATABASE INSPECTION COMPLETED")
        print("--------------------------------")

        for table_name, table_data in report["tables"].items():
            print(
                f"{table_name}: "
                f"{table_data['total_records']} records"
            )

        print("--------------------------------")
        print(f"Report saved at: {OUTPUT_FILE}")

    finally:
        connection.close()


if __name__ == "__main__":
    inspect_database()
