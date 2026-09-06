"""Validate transformed court case records for downstream pipeline use.

This layer checks required fields and relationships between fields.  It keeps
valid records unchanged and reports invalid records separately so later
pipeline layers can decide how to handle them.
"""

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSFORMED_CASES_PATH = PROJECT_ROOT / "data" / "transformed_cases.json"
VALIDATED_CASES_PATH = PROJECT_ROOT / "data" / "validated_cases.json"
VALIDATION_ERRORS_PATH = PROJECT_ROOT / "data" / "validation_errors.json"

REQUIRED_FIELDS = (
	"case_number",
	"case_title",
	"court",
	"case_type",
	"filing_date",
	"status",
)
ALLOWED_STATUSES = {"pending", "disposed", "active"}


def parse_iso_date(value: object) -> date:
	"""Parse an ISO date value for comparison during validation."""
	if not isinstance(value, str):
		raise ValueError("must be an ISO date string")
	return date.fromisoformat(value)


def validate_case(case: object, duplicate_case_numbers: set[str]) -> list[str]:
	"""Return all validation errors found in one case record."""
	if not isinstance(case, dict):
		return ["record must be an object"]

	errors = []
	missing_fields = [
		field for field in REQUIRED_FIELDS
		if field not in case or case[field] in (None, "")
	]
	if missing_fields:
		errors.append(f"missing required field(s): {', '.join(missing_fields)}")

	case_number = case.get("case_number")
	if isinstance(case_number, str) and case_number in duplicate_case_numbers:
		errors.append("duplicate case_number")

	status = case.get("status")
	if not isinstance(status, str) or status not in ALLOWED_STATUSES:
		errors.append("status must be one of: pending, disposed, active")

	filing_date = None
	if case.get("filing_date") not in (None, ""):
		try:
			filing_date = parse_iso_date(case["filing_date"])
		except (TypeError, ValueError):
			errors.append("filing_date must be a valid ISO date")

	if case.get("hearing_date") not in (None, ""):
		try:
			hearing_date = parse_iso_date(case["hearing_date"])
			if filing_date is not None and hearing_date < filing_date:
				errors.append("hearing_date cannot be earlier than filing_date")
		except (TypeError, ValueError):
			errors.append("hearing_date must be a valid ISO date")

	return errors


def write_json(path: Path, value: object) -> None:
	"""Write JSON data using a readable, stable format."""
	with path.open("w", encoding="utf-8") as output_file:
		json.dump(value, output_file, indent=2)
		output_file.write("\n")


def validate_cases(
	input_path: Path = TRANSFORMED_CASES_PATH,
	valid_output_path: Path = VALIDATED_CASES_PATH,
	errors_output_path: Path = VALIDATION_ERRORS_PATH,
) -> bool:
	"""Validate all records and save valid records and validation errors.

	Returns:
		``True`` when validation completes, or ``False`` when the input file
		is missing or contains malformed JSON/data.
	"""
	try:
		with input_path.open("r", encoding="utf-8") as input_file:
			records = json.load(input_file)
	except FileNotFoundError:
		print(f"Input file not found: {input_path}")
		return False
	except json.JSONDecodeError as error:
		print(f"Input file contains invalid JSON: {error}")
		return False

	if not isinstance(records, list):
		print("Input JSON must contain a list of case records")
		return False

	case_number_counts: dict[str, int] = {}
	for record in records:
		if isinstance(record, dict) and isinstance(record.get("case_number"), str):
			case_number = record["case_number"]
			case_number_counts[case_number] = case_number_counts.get(case_number, 0) + 1
	duplicate_case_numbers = {
		case_number
		for case_number, count in case_number_counts.items()
		if count > 1
	}

	valid_records = []
	validation_errors = []
	for record in records:
		errors = validate_case(record, duplicate_case_numbers)
		if errors:
			case_number = record.get("case_number") if isinstance(record, dict) else None
			validation_errors.append({"case_number": case_number, "errors": errors})
		else:
			valid_records.append(record)

	write_json(valid_output_path, valid_records)
	write_json(errors_output_path, validation_errors)
	print(f"Validated {len(records)} cases: {len(valid_records)} valid, "
		  f"{len(validation_errors)} invalid")
	return True


def main() -> None:
	"""Run the validation layer as a standalone module."""
	validate_cases()


if __name__ == "__main__":
	main()
