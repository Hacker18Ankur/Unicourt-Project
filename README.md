# Court Case Data Pipeline

## Automated Legal Data Collection, Validation & Search System

## Overview

Court Case Data Pipeline is a Python and PostgreSQL project for processing structured court-case records.

The system follows this workflow:

```text
Capture -> Transform -> Validate -> PostgreSQL -> Search -> Analysis
																												|
																			On-demand / Scheduled Updates
```

The current dataset contains **5 synthetic court-case records** for development and testing. The project does not scrape live court websites, and it does not bypass CAPTCHA.

The capture layer is source-agnostic. It currently reads local JSON data and can be connected to a legitimate public or authorized data source in the future.

## Problem Statement

Court-case data is difficult to search and analyze when records have inconsistent formatting, missing fields, invalid dates, unsupported statuses, or duplicate case numbers.

This project provides a controlled workflow that prepares records, checks their quality, stores valid data, and makes the stored cases searchable and measurable.

## Objectives

- Capture a reproducible snapshot of source records.
- Preserve raw, transformed, validated, and error data separately.
- Normalize text, status values, case numbers, and dates.
- Reject records that do not meet the validation rules.
- Store validated records in PostgreSQL.
- Prevent duplicate case numbers.
- Search cases by common fields.
- Produce useful aggregate analysis.
- Support both on-demand and scheduled updates.
- Test successful processing and important failure cases.

## System Workflow

```text
Capture
	-> captured_cases.json
Transform
	-> transformed_cases.json
Validate
	-> validated_cases.json and validation_errors.json
Store
	-> PostgreSQL court_cases table
Search and Analysis
	-> queries and summaries
Updates
	-> one-time or scheduled execution
```

The workflow is split into stages so that each stage has one clear responsibility. Raw data is retained for traceability, transformed data records normalized values, validation outputs explain which records are acceptable, and PostgreSQL provides durable storage for search and analysis.

## Project Architecture

```text
Capture Layer
		Reads source records and creates a captured snapshot

Transformation Layer
		Normalizes text, statuses, case numbers, and dates

Validation Layer
		Checks required fields, dates, statuses, and duplicates

Database Layer
		Creates the table and stores validated records in PostgreSQL

Search Layer
		Finds cases by case number, title, status, or court

Analysis Layer
		Calculates totals, grouped counts, and upcoming hearings

Update Layer
		Runs the stages in order on demand or on a schedule
```

## Project Structure

```text
Unicourt/
├── README.md
├── requirements.txt
├── .env
├── data/
│   ├── raw_cases.json
│   ├── captured_cases.json
│   ├── transformed_cases.json
│   ├── validated_cases.json
│   └── validation_errors.json
├── docs/
├── src/
│   ├── main.py
│   ├── analysis/
│   │   └── analysis.py
│   ├── capture/
│   │   └── capture.py
│   ├── database/
│   │   └── database.py
│   ├── search/
│   │   └── search.py
│   ├── transform/
│   │   └── transform.py
│   ├── updates/
│   │   └── updates.py
│   └── validate/
│       └── validate.py
└── tests/
		└── test_pipeline.py
```

## Technologies Used

- Python
- PostgreSQL
- `psycopg2-binary`
- `python-dotenv`
- Python standard library modules such as `json`, `pathlib`, and `time`
- `pytest`

## Data Flow

```text
data/raw_cases.json
				|
				v
data/captured_cases.json
				|
				v
data/transformed_cases.json
				|
				v
data/validated_cases.json -----> PostgreSQL: court_cases
				|
				v
data/validation_errors.json
```

The separate files make it possible to inspect each stage, understand how a record changed, and diagnose validation failures without losing the original captured data.

## Capture Layer

The capture layer is implemented in `src/capture/capture.py`.

It reads records from `data/raw_cases.json`, adds a UTC `captured_at` timestamp, and writes `data/captured_cases.json`. It does not validate, transform, search, analyze, or insert records into PostgreSQL.

The current input is synthetic local data. No live court website scraping is implemented.

## Transformation Layer

The transformation layer is implemented in `src/transform/transform.py`.

It creates a consistent representation by:

- Removing leading and trailing whitespace.
- Collapsing repeated whitespace.
- Converting case numbers to uppercase.
- Converting statuses to lowercase.
- Normalizing ISO date values.
- Preserving fields such as `source_url` and `captured_at`.

The result is written to `data/transformed_cases.json`.

## Validation Layer

The validation layer is implemented in `src/validate/validate.py`.

It checks the following rules:

- Required fields are present: `case_number`, `case_title`, `court`, `case_type`, `filing_date`, and `status`.
- `status` is one of `pending`, `disposed`, or `active`.
- `filing_date` is a valid ISO date.
- `hearing_date`, when present, is a valid ISO date.
- `hearing_date` is not earlier than `filing_date`.
- Duplicate `case_number` values are reported.

Valid records are written to `data/validated_cases.json`. Invalid records and their reasons are written to `data/validation_errors.json`.

Validation is separate from transformation so formatting changes and data-quality decisions remain independent and testable.

## PostgreSQL Storage

The database layer is implemented in `src/database/database.py` and uses `psycopg2` with the PostgreSQL database `court_data`.

The `court_cases` table stores fields including:

- `id`
- `case_number`
- `case_title`
- `court`
- `case_type`
- `filing_date`
- `status`
- `hearing_date`
- `judge`
- `source_url`
- `captured_at`
- `created_at`

The `case_number` column is `UNIQUE NOT NULL`. The database also uses `ON CONFLICT (case_number) DO NOTHING`, so duplicate inserts are skipped instead of creating duplicate records.

All values supplied to insert operations are passed through parameterized SQL. Database connections are closed after each operation, and database errors are handled with rollback where appropriate.

## Search Functionality

The search layer is implemented in `src/search/search.py`.

It supports:

- Exact search by `case_number`.
- Case-insensitive partial matching by `case_title`.
- Filtering by `status`.
- Filtering by `court`.

Search results are returned as Python dictionaries. User-provided values are passed through parameterized SQL queries.

## Analysis Functionality

The analysis layer is implemented in `src/analysis/analysis.py`.

It provides:

- Total case count.
- Case counts grouped by status.
- Case counts grouped by court.
- Case counts grouped by case type.
- Upcoming hearings from the current date onward.

The grouped reports use SQL aggregation, including `COUNT` and `GROUP BY`.

## Update Mechanism

The update orchestration layer is implemented in `src/updates/updates.py`.

The on-demand `run_update()` function runs the stages in this order:

```text
Capture -> Transform -> Validate -> PostgreSQL storage
```

The storage stage creates the table if necessary and loads records from `data/validated_cases.json`. The update stops when a required stage fails and prints the stage status to the console.

The update layer coordinates existing functions. It does not duplicate capture, transformation, validation, or database insertion logic.

## Scheduled Updates

The `run_scheduled_update(interval_minutes)` function repeatedly calls the existing `run_update()` function.

It:

- Requires an interval greater than zero.
- Uses Python's standard-library `time.sleep()` between runs.
- Prints when scheduling starts and when each update begins.
- Prints when the next update is expected.
- Stops gracefully when the user presses `Ctrl+C`.

Scheduled execution is separate from the one-time `run_update()` function.

## Testing

The automated test suite is in `tests/test_pipeline.py`.

It currently contains **23 tests, and all 23 pass**. The tests cover:

- Successful capture and missing capture input.
- Text, status, case-number, and date transformation.
- Malformed transformation input.
- Missing required fields.
- Invalid dates.
- Invalid status values.
- Duplicate case numbers.
- Validation output files.
- Database table creation and insert behavior.
- Parameterized SQL and duplicate protection.
- Connection cleanup and database errors.
- Search result mapping.
- Aggregate analysis and upcoming hearings.
- Update ordering and failure handling.
- Scheduler behavior and invalid intervals.

Temporary files and mocked database connections are used where external dependencies are required. The tests do not call live external APIs, bypass CAPTCHA, or require a live PostgreSQL connection for mocked database cases.

## Synthetic Data Disclaimer

The current dataset contains **5 synthetic records** created for development and testing. These records are not official court records, legal evidence, or a source of legal advice.

The project does not currently scrape live court websites and does not bypass CAPTCHA. Any future source integration must use a legitimate public or authorized data source and comply with applicable access policies and laws.

## Setup and Installation

The following commands are for Windows PowerShell.

### Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Configure PostgreSQL

Ensure PostgreSQL is installed and running, then create the project database:

```powershell
psql -U postgres -c "CREATE DATABASE court_data;"
```

If `court_data` already exists, PostgreSQL will report that it exists; no second database is needed.

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
```

The database table is created automatically by the database module and update pipeline.

## How to Run

Run one complete on-demand update:

```powershell
python -m src.updates.updates
```

Run each major stage independently:

```powershell
python -m src.capture.capture
python -m src.transform.transform
python -m src.validate.validate
python -m src.database.database
python -m src.search.search
python -m src.analysis.analysis
```

Run the complete test suite:

```powershell
python -m pytest -q
```

Start scheduled updates every 60 minutes:

```powershell
python -c "from src.updates.updates import run_scheduled_update; run_scheduled_update(60)"
```

Stop the scheduler with `Ctrl+C`.

## Example Outputs

### Observed output

The following values describe the current synthetic dataset and observed project behavior:

```text
Validated 5 cases: 5 valid, 0 invalid
Inserted: 5, Skipped: 0
Total court cases: 5
Upcoming hearings: 3
```

The current observed analysis result is **3 upcoming hearings**, not 5. Counts can change if the input JSON or database contents change.

### Illustrative duplicate-insert output

The following is an illustrative example of what a second load of the same records may report after those records already exist in PostgreSQL:

```text
Inserted: 0, Skipped: 5
```

### Illustrative search output

The following is an illustrative shape of a search result, not a claim about a live source:

```text
Search by case number:
[{"case_number": "WP-1023-2025", "case_title": "A v. State of Karnataka", ...}]
```

## Design Decisions

### One responsibility per layer

Capture, transformation, validation, storage, search, analysis, and orchestration are kept separate. This makes the project easier to understand, test, and change.

### Separate intermediate artifacts

Raw data is preserved for traceability. Transformed data records normalized values. Validation outputs show accepted records and explain rejected records. PostgreSQL stores records that are ready for querying.

### Validate before storage

Only records produced by the validation stage are loaded into PostgreSQL. This reduces the chance that malformed data affects search and analysis.

### Database-level duplicate protection

Application logic skips duplicate insert results, while PostgreSQL's unique constraint on `case_number` provides a second line of protection at the storage layer.

### Parameterized SQL

Search and insert values are passed as query parameters rather than concatenated into SQL strings. This keeps user-provided values separate from SQL syntax.

### No live-source claims

The project documents its current local synthetic-data implementation accurately. It does not claim live court scraping or CAPTCHA bypass functionality.

## Limitations

- The current dataset contains only 5 synthetic records.
- No live court website integration is implemented.
- No CAPTCHA bypass or automated CAPTCHA handling is implemented.
- PostgreSQL credentials must be configured locally.
- JSON files are used for intermediate artifacts.
- Search and analysis require the PostgreSQL table and data to be available.
- The scheduler runs in the foreground and stops when its process ends.
- No web interface or REST API is implemented.
- The project does not provide legal advice or official legal records.

## Future Improvements

Possible future improvements include:

- Connecting the capture layer to an authorized public data source.
- Adding structured logging and execution history.
- Adding database indexes and migrations for larger datasets.
- Adding retry handling for temporary database failures.
- Adding pagination for search results.
- Adding a web interface or API.
- Adding deployment and monitoring configuration.

Any future change should preserve the existing separation between capture, transformation, validation, storage, search, analysis, and orchestration.

## Conclusion

Court Case Data Pipeline demonstrates a modular workflow for processing structured court-case data:

```text
Capture -> Transform -> Validate -> PostgreSQL -> Search -> Analysis
																											|
																			On-demand / Scheduled Updates
```

The project preserves intermediate artifacts, validates records before storage, protects PostgreSQL from duplicate case numbers, and supports automated testing. Its source-agnostic capture design provides a foundation for future integration with a legitimate public or authorized data source without overstating the capabilities of the current implementation.
