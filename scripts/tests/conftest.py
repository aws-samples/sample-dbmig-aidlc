"""Make the dbmig package importable when pytest runs from the repo root."""
import sys
from pathlib import Path

# scripts/ (parent of tests/) holds the dbmig package.
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
