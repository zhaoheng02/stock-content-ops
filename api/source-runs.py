import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_ops.vercel_handler import ContentOpsHandler as handler  # noqa: F401
