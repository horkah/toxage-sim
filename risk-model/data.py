"""Read data of the engine in the format of the central schema."""
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from schema import toxage_schema  # noqa: E402


def load(folder):
    """Return (baseline records, outcome records by patient_id)."""
    folder = Path(folder)
    baseline = toxage_schema.read_csv(folder / "baseline.csv", "baseline")
    outcomes = toxage_schema.read_csv(folder / "outcome.csv", "outcome")
    return baseline, {o["patient_id"]: o for o in outcomes}
