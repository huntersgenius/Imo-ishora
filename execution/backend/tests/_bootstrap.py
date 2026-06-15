"""Make the backend ``app`` package importable from test modules.

Tests are run from the execution/ root via ``python -m unittest discover -s
backend/tests``. This adds the backend directory to sys.path so ``import app``
works without installing the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
