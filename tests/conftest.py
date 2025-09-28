from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path when tests are executed via pytest from
# an arbitrary working directory (which mirrors the behaviour of python -m).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
