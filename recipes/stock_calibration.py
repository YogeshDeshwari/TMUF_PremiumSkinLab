from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.stock_diffuse.calibration import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
