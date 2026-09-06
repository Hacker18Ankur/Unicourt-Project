import time
from collections.abc import Callable
from typing import Any

from src.capture.capture import capture_cases
from src.database.database import (
    create_court_cases_table,
    load_validated_cases,
)
from src.transform.transform import transform_cases
from src.validate.validate import validate_cases


def _run_stage(stage_name: str, stage: Callable[[], Any]) -> bool:
    """Run one pipeline stage and report whether it succeeded."""
    print(f"Running {stage_name} stage...")

    try:
        result = stage()
    except Exception as error:
        print(f"{stage_name} stage failed: {error}")
        return False

    if result is False:
        print(f"{stage_name} stage failed.")
        return False

    print(f"{stage_name} stage succeeded.")
    return True


def _store_validated_cases() -> None:
    """Create the storage table and load validated records."""
    create_court_cases_table()
    load_validated_cases()


def run_update() -> bool:
    """Run one complete Capture -> Transform -> Validate -> Store update."""
    stages = (
        ("Capture", capture_cases),
        ("Transform", transform_cases),
        ("Validate", validate_cases),
        ("Store", _store_validated_cases),
    )

    for stage_name, stage in stages:
        if not _run_stage(stage_name, stage):
            print("Update stopped because a required stage failed.")
            return False

    print("Update completed successfully.")
    return True


def run_scheduled_update(interval_minutes: int) -> None:
    """Repeatedly run updates at the specified interval."""
    if not isinstance(interval_minutes, int) or isinstance(interval_minutes, bool):
        raise TypeError("interval_minutes must be an integer")

    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be greater than 0")

    interval_seconds = interval_minutes * 60

    print(
        f"Scheduler started. Updates will run every "
        f"{interval_minutes} minute(s)."
    )

    try:
        while True:
            print("Scheduled update is beginning.")
            run_update()

            print(
                f"Next update will run in {interval_minutes} minute(s). "
                "Press Ctrl+C to stop the scheduler."
            )
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nScheduler stopped by user.")


def main() -> None:
    """Run one on-demand pipeline update when executed directly."""
    run_update()


if __name__ == "__main__":
    main()