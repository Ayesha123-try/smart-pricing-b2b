"""Rebuild every result from the raw CSVs, in order."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for script in ("profile_data", "backtest", "reconcile_claim", "win_model", "build_report_data", "make_charts"):
    print(f"--- {script}", flush=True)
    subprocess.run([sys.executable, str(ROOT / "src" / f"{script}.py")], check=True, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"], check=True)
