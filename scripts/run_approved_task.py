"""Project entry point; without explicit options this only prepares a plan."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from approval_gate.task_runner import main

if __name__ == "__main__":
    raise SystemExit(main())
