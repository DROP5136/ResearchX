"""Pytest configuration."""

from __future__ import annotations

import sys
from pathlib import Path

# apps/ai-service — so `import app` works
AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))
