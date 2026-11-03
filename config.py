"""Central configuration for the Sunny the Panther app."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "sunny.db"
SUNNY_ART_DIR = BASE_DIR / "assets" / "sunny"
PROPS_DIR = BASE_DIR / "assets" / "props"

PET_NAME = "Sunny"

# Display: everything is drawn on a small "logical" canvas and scaled up
# with nearest-neighbour so every logical pixel becomes a chunky 2x2 block.
SCREEN_SIZE = (800, 480)
SCALE = 2
LOGICAL_SIZE = (SCREEN_SIZE[0] // SCALE, SCREEN_SIZE[1] // SCALE)
FPS = 30

# DHT22 on GPIO4 (physical pin 7)
DHT_PIN = "D4"
SENSOR_INTERVAL = 3.0        # seconds between reads (DHT22 needs >= 2s)
SENSOR_STALE_AFTER = 30.0    # treat readings older than this as missing

AUTOSAVE_INTERVAL = 30.0

# Local LLM: Ollama on this Pi only (never a remote host)
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_KEEP_ALIVE = "2h"     # keep the model loaded so answers start quickly
CHAT_MAX_TOKENS = 100        # ~3 short sentences
CHAT_HISTORY = 6             # past messages the model sees
CHAT_TIMEOUT = 90            # seconds

# Defaults for parent-adjustable settings, stored in the save file.
DEFAULT_SETTINGS = {
    "parent_pin": "1234",
    "temp_unit": "F",          # "F" or "C"
    "bedtime_enabled": True,
    "bedtime": "19:30",
    "wake_time": "07:00",
    "daily_chat_limit": 30,    # messages per day
}
