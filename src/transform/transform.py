"""Transform captured court case records into a consistent representation.

This layer prepares captured data for later pipeline stages by making text,
status, and date formats consistent.  It does not validate case records or
perform any database work.
"""

import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAPTURED_CASES_PATH = PROJECT_ROOT / "data" / "captured_cases.json"
TRANSFORMED_CASES_PATH = PROJECT_ROOT / "data" / "transformed_cases.json"


def normalize_text(value: str) -> str:
	"""Remove leading, trailing, and repeated whitespace from text."""
	return " ".join(value.split())


def transform_case(case: dict) -> dict:
	"""Return one case with consistent text, status, and date formats."""
	transformed_case = {}

	for field, value in case.items():
		if field in {"captured_at", "source_url"}:
			transformed_case[field] = value
		elif field == "case_number" and isinstance(value, str):
			transformed_case[field] = normalize_text(value).upper()
		elif field == "status" and isinstance(value, str):
			transformed_case[field] = normalize_text(value).lower()
		elif field in {"filing_date", "hearing_date"} and isinstance(value, str):
			transformed_case[field] = date.fromisoformat(value).isoformat()
		elif isinstance(value, str):
			transformed_case[field] = normalize_text(value)
		else:
			transformed_case[field] = value

	return transformed_case


def transform_cases(
	input_path: Path = CAPTURED_CASES_PATH,
	output_path: Path = TRANSFORMED_CASES_PATH,
) -> bool:
	"""Read captured cases, transform them, and write the transformed data.

	Returns:
		``True`` when the transformed records are written successfully,
		otherwise ``False`` when the input is missing or malformed.
	"""
	try:
		with input_path.open("r", encoding="utf-8") as source_file:
			captured_cases = json.load(source_file)
		transformed_cases = [transform_case(case) for case in captured_cases]
	except FileNotFoundError:
		print(f"Input file not found: {input_path}")
		return False
	except (json.JSONDecodeError, TypeError, ValueError) as error:
		print(f"Input file is malformed: {error}")
		return False

	with output_path.open("w", encoding="utf-8") as transformed_file:
		json.dump(transformed_cases, transformed_file, indent=2)
		transformed_file.write("\n")

	print(f"Transformed {len(transformed_cases)} cases to {output_path}")
	return True


def main() -> None:
	"""Run the transformation layer as a standalone module."""
	transform_cases()


if __name__ == "__main__":
	main()
