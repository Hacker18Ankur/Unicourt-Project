import os
import json
from pathlib import Path
from typing import Any, Mapping

import psycopg2
from dotenv import load_dotenv
from psycopg2 import Error


load_dotenv()


DATABASE_NAME = "court_data"


def get_database_connection():
    """Establish and return a PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=DATABASE_NAME,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def create_court_cases_table() -> None:
    """Create the court_cases table if it does not already exist."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS court_cases (
                    id SERIAL PRIMARY KEY,
                    case_number VARCHAR(255) UNIQUE NOT NULL,
                    case_title TEXT,
                    court VARCHAR(255),
                    case_type VARCHAR(255),
                    filing_date DATE,
                    status VARCHAR(255),
                    hearing_date DATE,
                    judge VARCHAR(255),
                    source_url TEXT,
                    captured_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

        connection.commit()

    except Error:
        if connection is not None:
            connection.rollback()
        raise

    finally:
        if connection is not None:
            connection.close()


def insert_validated_case(case_record: Mapping[str, Any]) -> bool:
    """
    Insert one validated case record.

    Returns:
        True if the record was inserted, or False if its case number
        already exists.
    """
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO court_cases (
                    case_number,
                    case_title,
                    court,
                    case_type,
                    filing_date,
                    status,
                    hearing_date,
                    judge,
                    source_url,
                    captured_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (case_number) DO NOTHING;
                """,
                (
                    case_record["case_number"],
                    case_record.get("case_title"),
                    case_record.get("court"),
                    case_record.get("case_type"),
                    case_record.get("filing_date"),
                    case_record.get("status"),
                    case_record.get("hearing_date"),
                    case_record.get("judge"),
                    case_record.get("source_url"),
                    case_record.get("captured_at"),
                ),
            )

            inserted = cursor.rowcount == 1

        connection.commit()
        return inserted

    except Error:
        if connection is not None:
            connection.rollback()
        raise

    finally:
        if connection is not None:
            connection.close()


def load_validated_cases() -> None:
    """Load validated case records from JSON into the database."""
    validated_cases_path = (
        Path(__file__).resolve().parents[2] / "data" / "validated_cases.json"
    )

    try:
        with validated_cases_path.open("r", encoding="utf-8") as file:
            validated_cases = json.load(file)
    except FileNotFoundError:
        print(f"Validated cases file not found: {validated_cases_path}")
        return
    except (json.JSONDecodeError, OSError) as error:
        print(f"Could not read validated cases: {error}")
        return

    if not isinstance(validated_cases, list) or not all(
        isinstance(case_record, dict) for case_record in validated_cases
    ):
        print("Could not read validated cases: expected a JSON list of records.")
        return

    inserted_count = 0
    skipped_count = 0

    for case_record in validated_cases:
        if insert_validated_case(case_record):
            inserted_count += 1
        else:
            skipped_count += 1

    print(f"Inserted: {inserted_count}, Skipped: {skipped_count}")


def main() -> None:
    """Create the database table and load validated cases."""
    create_court_cases_table()
    load_validated_cases()


if __name__ == "__main__":
    main()