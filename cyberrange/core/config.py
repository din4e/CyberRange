from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "cyberrange" / "data"
STATS_FILE = DATA_DIR / "stats.json"
INSTANCES_FILE = DATA_DIR / "instances.json"
PORT_ALLOC_FILE = DATA_DIR / "port_allocations.json"

PORT_POOL_START = 9000
PORT_POOL_END = 9999
PORTS_PER_INSTANCE = 20

DEFAULT_COMPOSE_TIMEOUT = 300

SKIP_DIRS = frozenset({
    ".git", ".claude", ".omc", "node_modules", "__pycache__",
    "cyberrange", "tests", ".venv", "venv", ".idea", ".vscode",
    "data",
})

DATA_DIR.mkdir(parents=True, exist_ok=True)
