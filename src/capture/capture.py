"""Capture raw court case records for the rest of the data pipeline.

The capture layer creates a timestamped snapshot of the source data.  It
does not interpret, validate, or transform case fields; later pipeline layers
are responsible for those concerns.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_CASES_PATH = PROJECT_ROOT / "data" / "raw_cases.json"
CAPTURED_CASES_PATH = PROJECT_ROOT / "data" / "captured_cases.json"


def capture_cases(
	input_path: Path = RAW_CASES_PATH,
	output_path: Path = CAPTURED_CASES_PATH,
) -> bool:
	"""Read raw cases, add capture timestamps, and write a captured snapshot.

	The original fields are copied unchanged so this layer records what was
	received without taking on validation or business logic.

	Returns:
		``True`` when the snapshot is written successfully, otherwise
		``False`` for a missing input file or invalid JSON.
	"""
	try:
		with input_path.open("r", encoding="utf-8") as source_file:
			raw_cases = json.load(source_file)
	except FileNotFoundError:
		print(f"Input file not found: {input_path}")
		return False
	except json.JSONDecodeError as error:
		print(f"Input file contains invalid JSON: {error}")
		return False

	captured_at = datetime.now(timezone.utc).isoformat()
	captured_cases = [
		{**case, "captured_at": captured_at}
		for case in raw_cases
	]

	with output_path.open("w", encoding="utf-8") as captured_file:
		json.dump(captured_cases, captured_file, indent=2)
		captured_file.write("\n")

	print(f"Captured {len(captured_cases)} cases to {output_path}")
	return True


def main() -> None:
	"""Run the capture layer as a standalone module."""
	capture_cases()


if __name__ == "__main__":
	main()
