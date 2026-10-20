"""objects shared by every request."""
from __future__ import annotations

from ..services.jobs import JobManager

manager = JobManager()
