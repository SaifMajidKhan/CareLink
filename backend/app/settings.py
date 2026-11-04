"""Load local Neon settings while keeping hosted environment variables first."""
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_local_environment(project_root: Path = PROJECT_ROOT):
    # Explicit process settings win, followed by backend overrides and Neon files.
    for folder in (project_root / 'backend', project_root):
        for name in ('.env.local', '.env'):
            load_dotenv(folder / name, override=False)
