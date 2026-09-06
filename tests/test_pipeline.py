import json
from unittest.mock import MagicMock, call

import psycopg2
import pytest

from src.analysis import analysis
from src.capture import capture
from src.database import database
from src.search import search
from src.transform import transform
from src.updates import updates
from src.validate import validate


def write_json(path, value):
	path.write_text(json.dumps(value), encoding="utf-8")


def make_connection(cursor):
	connection = MagicMock()
	connection.cursor.return_value.__enter__.return_value = cursor
	return connection


def valid_case(**overrides):
	case = {
		"case_number": "WP-1-2026",
		"case_title": "A v. State",
		"court": "High Court",
		"case_type": "Writ Petition",
		"filing_date": "2026-01-10",
		"status": "pending",
		"hearing_date": "2026-10-10",
	}
	case.update(overrides)
	return case


def test_capture_cases_writes_timestamped_snapshot(tmp_path):
	input_path = tmp_path / "raw.json"
	output_path = tmp_path / "captured.json"
	write_json(input_path, [valid_case()])

	assert capture.capture_cases(input_path, output_path) is True

	captured = json.loads(output_path.read_text(encoding="utf-8"))
	assert captured[0]["case_number"] == "WP-1-2026"
	assert "captured_at" in captured[0]


def test_capture_cases_returns_false_for_missing_input(tmp_path):
	assert capture.capture_cases(tmp_path / "missing.json", tmp_path / "out.json") is False


def test_transform_case_normalizes_text_status_and_case_number():
	transformed = transform.transform_case(
		valid_case(
			case_number="  wp-1-2026  ",
			case_title="  A   v.   State ",
			status="  PENDING ",
		)
	)

	assert transformed["case_number"] == "WP-1-2026"
	assert transformed["case_title"] == "A v. State"
	assert transformed["status"] == "pending"


def test_transform_cases_returns_false_for_invalid_json(tmp_path):
	input_path = tmp_path / "captured.json"
	input_path.write_text("not json", encoding="utf-8")

	assert transform.transform_cases(input_path, tmp_path / "out.json") is False


@pytest.mark.parametrize(
	("case", "expected_error"),
	[
		(valid_case(case_title=""), "missing required field(s)"),
		(valid_case(filing_date="2026-99-01"), "filing_date must be a valid ISO date"),
		(valid_case(status="unknown"), "status must be one of"),
	],
)
def test_validate_case_rejects_invalid_records(case, expected_error):
	errors = validate.validate_case(case, set())

	assert any(expected_error in error for error in errors)


def test_validate_case_rejects_duplicate_case_number():
	errors = validate.validate_case(valid_case(), {"WP-1-2026"})

	assert "duplicate case_number" in errors


def test_validate_cases_writes_valid_and_error_outputs(tmp_path):
	input_path = tmp_path / "transformed.json"
	valid_output = tmp_path / "validated.json"
	errors_output = tmp_path / "errors.json"
	write_json(
    input_path,
    [
        valid_case(),
        valid_case(case_number="WP-2-2026", status="invalid"),
    ],
)

	assert validate.validate_cases(input_path, valid_output, errors_output) is True

	assert json.loads(valid_output.read_text(encoding="utf-8")) == [valid_case()]
	errors = json.loads(errors_output.read_text(encoding="utf-8"))
	assert errors[0]["case_number"] == "WP-2-2026"
	assert "status must be one of" in errors[0]["errors"][0]


def test_create_table_commits_and_closes_connection(monkeypatch):
	cursor = MagicMock()
	connection = make_connection(cursor)
	monkeypatch.setattr(database, "get_database_connection", lambda: connection)

	database.create_court_cases_table()

	sql = cursor.execute.call_args.args[0]
	assert "CREATE TABLE IF NOT EXISTS court_cases" in sql
	connection.commit.assert_called_once()
	connection.close.assert_called_once()


def test_insert_validated_case_uses_parameters_and_closes_connection(monkeypatch):
	cursor = MagicMock()
	cursor.rowcount = 1
	connection = make_connection(cursor)
	monkeypatch.setattr(database, "get_database_connection", lambda: connection)
	case = valid_case()

	assert database.insert_validated_case(case) is True

	query, parameters = cursor.execute.call_args.args
	assert "ON CONFLICT (case_number) DO NOTHING" in query
	assert parameters[0] == "WP-1-2026"
	assert "%s" in query
	connection.commit.assert_called_once()
	connection.close.assert_called_once()


def test_insert_validated_case_returns_false_for_duplicate(monkeypatch):
	cursor = MagicMock()
	cursor.rowcount = 0
	connection = make_connection(cursor)
	monkeypatch.setattr(database, "get_database_connection", lambda: connection)

	assert database.insert_validated_case(valid_case()) is False
	connection.close.assert_called_once()


def test_load_validated_cases_counts_inserted_and_skipped(tmp_path, monkeypatch, capsys):
	data_dir = tmp_path / "data"
	database_dir = tmp_path / "src" / "database"
	database_dir.mkdir(parents=True)
	data_dir.mkdir()
	validated_path = data_dir / "validated_cases.json"
	write_json(validated_path, [valid_case(), valid_case(case_number="WP-2-2026")])
	monkeypatch.setattr(database, "__file__", str(database_dir / "database.py"))
	monkeypatch.setattr(database, "insert_validated_case", MagicMock(side_effect=[True, False]))

	database.load_validated_cases()

	assert capsys.readouterr().out.strip() == "Inserted: 1, Skipped: 1"


def test_search_by_title_returns_dictionaries_and_closes_connection(monkeypatch):
	cursor = MagicMock()
	cursor.description = [("case_number",), ("case_title",)]
	cursor.fetchall.return_value = [("WP-1-2026", "A v. State")]
	connection = make_connection(cursor)
	monkeypatch.setattr(search, "get_database_connection", lambda: connection)

	result = search.search_by_case_title("state")

	assert result == [{"case_number": "WP-1-2026", "case_title": "A v. State"}]
	query, parameters = cursor.execute.call_args.args
	assert "ILIKE %s" in query
	assert parameters == ("%state%",)
	connection.close.assert_called_once()


def test_search_returns_empty_list_on_database_error(monkeypatch):
	monkeypatch.setattr(
		search,
		"get_database_connection",
		MagicMock(side_effect=psycopg2.Error("connection failed")),
	)

	assert search.search_by_case_number("WP-1-2026") == []


def test_analysis_functions_use_aggregate_results(monkeypatch):
	cursor = MagicMock()
	cursor.fetchone.return_value = (3,)
	connection = make_connection(cursor)
	monkeypatch.setattr(analysis, "get_database_connection", lambda: connection)

	assert analysis.count_total_cases() == 3
	assert "COUNT(*)" in cursor.execute.call_args.args[0]
	connection.close.assert_called_once()


def test_analysis_grouped_count_returns_dictionary(monkeypatch):
	cursor = MagicMock()
	cursor.fetchall.return_value = [("pending", 2), ("disposed", 1)]
	connection = make_connection(cursor)
	monkeypatch.setattr(analysis, "get_database_connection", lambda: connection)

	assert analysis.count_cases_by_status() == {"pending": 2, "disposed": 1}
	assert "GROUP BY status" in cursor.execute.call_args.args[0]


def test_upcoming_hearings_returns_dictionaries(monkeypatch):
	cursor = MagicMock()
	cursor.description = [("case_number",), ("hearing_date",)]
	cursor.fetchall.return_value = [("WP-1-2026", "2026-10-10")]
	connection = make_connection(cursor)
	monkeypatch.setattr(analysis, "get_database_connection", lambda: connection)

	assert analysis.get_upcoming_hearings() == [
		{"case_number": "WP-1-2026", "hearing_date": "2026-10-10"}
	]
	assert "CURRENT_DATE" in cursor.execute.call_args.args[0]


def test_run_update_executes_stages_in_order(monkeypatch):
	stages = [MagicMock(return_value=True) for _ in range(4)]
	monkeypatch.setattr(updates, "capture_cases", stages[0])
	monkeypatch.setattr(updates, "transform_cases", stages[1])
	monkeypatch.setattr(updates, "validate_cases", stages[2])
	monkeypatch.setattr(updates, "create_court_cases_table", stages[3])
	load_cases = MagicMock()
	monkeypatch.setattr(updates, "load_validated_cases", load_cases)

	assert updates.run_update() is True
	assert all(stage.call_count == 1 for stage in stages)
	load_cases.assert_called_once()


def test_run_update_stops_when_stage_fails(monkeypatch):
	capture_stage = MagicMock(return_value=True)
	transform_stage = MagicMock(return_value=False)
	monkeypatch.setattr(updates, "capture_cases", capture_stage)
	monkeypatch.setattr(updates, "transform_cases", transform_stage)
	validate_stage = MagicMock()
	monkeypatch.setattr(updates, "validate_cases", validate_stage)

	assert updates.run_update() is False
	capture_stage.assert_called_once()
	transform_stage.assert_called_once()
	validate_stage.assert_not_called()


def test_scheduled_update_runs_again_after_interval(monkeypatch):
	run_update = MagicMock(side_effect=[True, KeyboardInterrupt])
	sleep = MagicMock()
	monkeypatch.setattr(updates, "run_update", run_update)
	monkeypatch.setattr(updates.time, "sleep", sleep)

	updates.run_scheduled_update(5)

	assert run_update.call_count == 2
	sleep.assert_called_once_with(300)


@pytest.mark.parametrize("interval", [0, -1])
def test_scheduled_update_rejects_non_positive_interval(interval):
	with pytest.raises(ValueError, match="greater than 0"):
		updates.run_scheduled_update(interval)
