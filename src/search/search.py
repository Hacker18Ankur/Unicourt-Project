from typing import Any

from psycopg2 import Error

from src.database.database import get_database_connection


def _fetch_cases(query: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Execute a search query and return rows as dictionaries."""
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            column_names = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

        return [dict(zip(column_names, row)) for row in rows]

    except Error as error:
        print(f"Database search error: {error}")
        return []

    finally:
        if connection is not None:
            connection.close()


def search_by_case_number(case_number: str) -> list[dict[str, Any]]:
    """Search for a case by its exact case number."""
    return _fetch_cases(
        """
        SELECT *
        FROM court_cases
        WHERE case_number = %s
        ORDER BY created_at DESC;
        """,
        (case_number,),
    )


def search_by_case_title(title: str) -> list[dict[str, Any]]:
    """Search for cases using case-insensitive partial title matching."""
    return _fetch_cases(
        """
        SELECT *
        FROM court_cases
        WHERE case_title ILIKE %s
        ORDER BY created_at DESC;
        """,
        (f"%{title}%",),
    )


def filter_by_status(status: str) -> list[dict[str, Any]]:
    """Return cases matching the specified status."""
    return _fetch_cases(
        """
        SELECT *
        FROM court_cases
        WHERE status = %s
        ORDER BY created_at DESC;
        """,
        (status,),
    )


def filter_by_court(court: str) -> list[dict[str, Any]]:
    """Return cases matching the specified court."""
    return _fetch_cases(
        """
        SELECT *
        FROM court_cases
        WHERE court = %s
        ORDER BY created_at DESC;
        """,
        (court,),
    )


def main() -> None:
    """Demonstrate common court case searches."""
    print("Search by case number:")
    print(search_by_case_number("WP-1023-2025"))

    print("\nSearch by case title:")
    print(search_by_case_title("State of Karnataka"))

    print("\nFilter by status:")
    print(filter_by_status("pending"))

    print("\nFilter by court:")
    print(filter_by_court("High Court of Karnataka"))


if __name__ == "__main__":
    main()