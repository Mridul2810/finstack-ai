"""pytest path setup: allow `import app.*` from backend/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
