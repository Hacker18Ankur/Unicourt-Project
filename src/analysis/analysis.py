from datetime import date
from typing import Any

import psycopg2

from src.database.database import get_database_connection


def count_total_cases() -> int:
    """Return the total number of court cases."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM court_cases;")
            return cursor.fetchone()[0]

    except psycopg2.Error as error:
        print(f"Database analysis error: {error}")
        return 0

    finally:
        if connection is not None:
            connection.close()


def count_cases_by_status() -> dict[str, int]:
    """Return case counts grouped by status."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status, COUNT(*)
                FROM court_cases
                GROUP BY status
                ORDER BY status;
                """
            )
            return {status: count for status, count in cursor.fetchall()}

    except psycopg2.Error as error:
        print(f"Database analysis error: {error}")
        return {}

    finally:
        if connection is not None:
            connection.close()


def count_cases_by_court() -> dict[str, int]:
    """Return case counts grouped by court."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT court, COUNT(*)
                FROM court_cases
                GROUP BY court
                ORDER BY court;
                """
            )
            return {court: count for court, count in cursor.fetchall()}

    except psycopg2.Error as error:
        print(f"Database analysis error: {error}")
        return {}

    finally:
        if connection is not None:
            connection.close()


def count_cases_by_type() -> dict[str, int]:
    """Return case counts grouped by case type."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT case_type, COUNT(*)
                FROM court_cases
                GROUP BY case_type
                ORDER BY case_type;
                """
            )
            return {case_type: count for case_type, count in cursor.fetchall()}

    except psycopg2.Error as error:
        print(f"Database analysis error: {error}")
        return {}

    finally:
        if connection is not None:
            connection.close()


def get_upcoming_hearings() -> list[dict[str, Any]]:
    """Return cases with hearings scheduled for today or a future date."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    case_number,
                    case_title,
                    court,
                    case_type,
                    hearing_date,
                    status,
                    judge
                FROM court_cases
                WHERE hearing_date IS NOT NULL
                  AND hearing_date::date >= CURRENT_DATE
                ORDER BY hearing_date ASC;
                """
            )

            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    except psycopg2.Error as error:
        print(f"Database analysis error: {error}")
        return []

    finally:
        if connection is not None:
            connection.close()


def main() -> None:
    """Print a summary of court case analysis."""
    print(f"Analysis date: {date.today()}")
    print(f"Total court cases: {count_total_cases()}")

    print("\nCases by status:")
    for status, count in count_cases_by_status().items():
        print(f"  {status}: {count}")

    print("\nCases by court:")
    for court, count in count_cases_by_court().items():
        print(f"  {court}: {count}")

    print("\nCases by type:")
    for case_type, count in count_cases_by_type().items():
        print(f"  {case_type}: {count}")

    upcoming_hearings = get_upcoming_hearings()
    print(f"\nUpcoming hearings: {len(upcoming_hearings)}")

    for hearing in upcoming_hearings:
        print(
            f"  {hearing['hearing_date']}: "
            f"{hearing['case_number']} - "
            f"{hearing['case_title']} "
            f"({hearing['court']})"
        )


if __name__ == "__main__":
    main()